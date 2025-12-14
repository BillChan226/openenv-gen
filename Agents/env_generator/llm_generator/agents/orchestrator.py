"""
Generator Orchestrator

Coordinates multiple specialized agents to generate a complete environment.

Architecture:
    GeneratorOrchestrator (coordinator)
        ├── BackendAgent (worker)
        ├── FrontendAgent (worker)
        └── OpenEnvAgent (worker)

Each phase:
1. Orchestrator creates task for the phase
2. Specialized agent executes with THINK -> PLAN -> GENERATE -> REFLECT -> FIX
3. Orchestrator verifies output
4. If issues from previous phases detected, can go back and fix

This mimics how I work on complex tasks:
- Break into phases
- Work on each phase iteratively
- Keep checking for cross-phase consistency
"""

import sys
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.base_agent import BaseAgent, AgentRole, AgentCapability
from utils.planning_agent import PlanningAgent
from utils.config import AgentConfig, LLMConfig, LLMProvider
from utils.message import TaskMessage, ResultMessage, create_result_message
from utils.planner import Plan, PlanStep, StepStatus

from .code_agent import CodeGeneratorAgent
from ..context import GenerationContext
from ..events import EventEmitter, EventType, ConsoleListener
from ..checkpoint import CheckpointManager
from ..runtime_verify import RuntimeVerifier, RuntimeVerificationReport

# Import memory for shared context
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.memory import AgentMemory


@dataclass
class PhaseResult:
    """Result of a generation phase"""
    phase: str
    success: bool
    files_generated: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)
    duration: float = 0.0  # seconds


class GeneratorOrchestrator(PlanningAgent):
    """
    Orchestrates the environment generation process.
    
    Phases:
    1. DESIGN - Analyze requirements, define entities
    2. BACKEND - Generate FastAPI backend
    3. FRONTEND - Generate React frontend
    4. OPENENV - Generate OpenEnv adapter
    5. DOCKER - Generate Docker configuration
    
    Key Features:
    - Each phase runs as THINK -> PLAN -> GENERATE -> REFLECT -> FIX
    - Cross-phase consistency checking
    - Can revisit earlier phases if issues found
    """
    
    PHASES = [
        "design",
        "backend",
        "frontend",
        "openenv",
        "docker",
    ]
    
    def __init__(
        self,
        config: AgentConfig,
        output_dir: Path,
        event_emitter: Optional[EventEmitter] = None,
        verbose: bool = False,
        resume: bool = False,
    ):
        super().__init__(config, role=AgentRole.COORDINATOR)
        
        self.output_dir = output_dir
        self.gen_context: Optional[GenerationContext] = None
        self.verbose = verbose
        self.resume = resume
        
        # Event emitter for real-time progress streaming
        self._emitter = event_emitter or EventEmitter()
        if not event_emitter:
            # Add default console listener if no custom emitter provided
            self._emitter.on_all(ConsoleListener(verbose=verbose))
        
        # Checkpoint manager for resume capability
        self._checkpoint: Optional[CheckpointManager] = None
        
        # Phase tracking
        self.phase_results: Dict[str, PhaseResult] = {}
        
        # Sub-agents (created on demand)
        self._agents: Dict[str, CodeGeneratorAgent] = {}
        
        # SHARED MEMORY across all phases
        # This allows agents to remember:
        # - What files were generated and their purposes
        # - What errors were fixed and how
        # - API endpoints, schemas, etc. for cross-phase consistency
        self._shared_memory = AgentMemory(
            short_term_size=100,   # Recent generation context
            long_term_size=500,    # Persistent patterns and fixes
        )
    
    async def on_initialize(self) -> None:
        """Initialize orchestrator"""
        await super().on_initialize()
        
        # Add capabilities
        self.add_capability(AgentCapability(
            name="coordinate",
            description="Coordinate multiple code generation agents",
        ))
        self.add_capability(AgentCapability(
            name="cross_phase_verify",
            description="Verify consistency across generation phases",
        ))
        
        self._logger.info("GeneratorOrchestrator initialized")
    
    # ===== Memory Methods =====
    
    def _remember_file(self, file_path: str, purpose: str, phase: str, code_summary: str) -> None:
        """Store file generation info in shared memory"""
        content = f"Generated {file_path} in {phase} phase. Purpose: {purpose}"
        
        # Extract key info for recall
        metadata = {
            "type": "file_generated",
            "file_path": file_path,
            "phase": phase,
            "purpose": purpose,
        }
        
        # Add to short-term for immediate recall
        self._shared_memory.remember(content, memory_type="short", metadata=metadata, importance=0.7)
        
        # If it's an important file (API, schema, etc.), add to long-term
        if any(keyword in file_path.lower() for keyword in ["models", "schemas", "api", "auth", "main"]):
            self._shared_memory.remember(
                f"KEY FILE: {file_path}\nPurpose: {purpose}\nSummary: {code_summary[:200]}",
                memory_type="long",
                metadata=metadata,
                importance=0.9,
            )
    
    def _remember_fix(self, issue: str, fix: str, file_path: str) -> None:
        """Store fix pattern in long-term memory for learning"""
        content = f"FIX PATTERN: Issue '{issue[:100]}' in {file_path} was fixed by: {fix[:200]}"
        
        metadata = {
            "type": "fix_pattern",
            "file_path": file_path,
            "issue_type": self._classify_issue(issue),
        }
        
        # Store in long-term memory with high importance (we want to learn from fixes)
        self._shared_memory.remember(content, memory_type="long", metadata=metadata, importance=0.85)
    
    def _classify_issue(self, issue: str) -> str:
        """Classify issue type for better recall"""
        issue_lower = issue.lower()
        if "import" in issue_lower:
            return "import_error"
        elif "syntax" in issue_lower:
            return "syntax_error"
        elif "missing" in issue_lower:
            return "missing_file"
        elif "truncat" in issue_lower:
            return "truncation"
        else:
            return "other"
    
    def _recall_relevant_context(self, phase: str, query: str = "") -> str:
        """Recall relevant context from memory for current phase"""
        context_parts = []
        
        # Get working memory context
        working_context = self._shared_memory.get_context_string(max_items=10)
        if working_context:
            context_parts.append(working_context)
        
        # Search for relevant files from previous phases
        if phase == "frontend":
            # Frontend needs to know about backend APIs
            api_memories = self._shared_memory.recall("API endpoint schemas auth", limit=5)
            if api_memories:
                context_parts.append("## Backend API Context")
                for mem in api_memories:
                    context_parts.append(f"- {mem.content[:150]}")
        
        elif phase == "openenv":
            # OpenEnv needs to know about both backend and frontend
            all_memories = self._shared_memory.recall("models schemas API", limit=8)
            if all_memories:
                context_parts.append("## Application Context")
                for mem in all_memories:
                    context_parts.append(f"- {mem.content[:150]}")
        
        # Always include recent fix patterns
        fix_memories = self._shared_memory.long_term.search("FIX PATTERN", limit=3)
        if fix_memories:
            context_parts.append("## Learned Fix Patterns")
            for mem in fix_memories:
                context_parts.append(f"- {mem.content[:100]}")
        
        return "\n".join(context_parts)
    
    async def generate_environment(
        self,
        name: str,
        description: str,
        domain_type: str = "custom",
    ) -> Dict[str, Any]:
        """
        Generate a complete environment.
        
        This is the main entry point. It:
        1. Creates context
        2. Runs each phase iteratively
        3. Verifies cross-phase consistency
        4. Returns result
        """
        start_time = datetime.now()
        
        # Create output directory
        env_dir = self.output_dir / name
        env_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize checkpoint manager
        self._checkpoint = CheckpointManager(env_dir / ".checkpoint.json")
        
        # Check for resume
        resuming = False
        if self.resume and self._checkpoint.load():
            summary = self._checkpoint.get_summary()
            if summary["can_resume"]:
                resuming = True
                self._checkpoint.print_status()
                self._logger.info(f"Resuming generation from checkpoint...")
                
                # Restore context from checkpoint
                self.gen_context = GenerationContext(
                    name=self._checkpoint.checkpoint.name,
                    display_name=self._checkpoint.checkpoint.name.replace("_", " ").title(),
                    description=self._checkpoint.checkpoint.description,
                    domain_type=self._checkpoint.checkpoint.domain_type,
                    output_dir=env_dir,
                )
            else:
                self._logger.info("Previous generation complete, starting fresh")
                self._checkpoint.clear()
        
        if not resuming:
            # Initialize fresh context
            self.gen_context = GenerationContext(
                name=name,
                display_name=name.replace("_", " ").title(),
                description=description,
                domain_type=domain_type,
                output_dir=env_dir,
            )
            
            # Start new checkpoint
            self._checkpoint.start_generation(name, description, domain_type)
        
        # Emit generation start event
        self._emitter.emit(EventType.GENERATION_START, f"{'Resuming' if resuming else 'Starting'} generation: {name}", {
            "name": name,
            "description": description,
            "domain_type": domain_type,
            "output_dir": str(env_dir),
            "resuming": resuming,
        })
        
        self._logger.info(f"Starting environment generation: {name}")
        self._logger.info(f"Output directory: {env_dir}")
        
        # Run each phase
        for phase in self.PHASES:
            # Check if phase already complete (for resume)
            if self._checkpoint and self._checkpoint.is_phase_complete(phase):
                self._logger.info(f"Phase {phase} already complete, skipping...")
                self._emitter.emit(EventType.PHASE_COMPLETE, f"Phase already complete: {phase}", {
                    "phase": phase,
                    "skipped": True,
                })
                self.gen_context.mark_phase_complete(phase)
                continue
            
            # Start phase in checkpoint
            if self._checkpoint:
                self._checkpoint.start_phase(phase)
            
            # Emit phase start event
            self._emitter.emit(EventType.PHASE_START, f"Phase: {phase.upper()}", {
                "phase": phase,
                "phases_total": len(self.PHASES),
                "phases_completed": len(self.gen_context.completed_phases),
            })
            
            self._logger.info(f"\n{'='*50}")
            self._logger.info(f"PHASE: {phase.upper()}")
            self._logger.info(f"{'='*50}")
            
            self.gen_context.current_phase = phase
            
            result = await self._run_phase(phase)
            self.phase_results[phase] = result
            
            # Complete phase in checkpoint
            if self._checkpoint:
                self._checkpoint.complete_phase(phase, result.issues, result.fixes_applied)
            
            # Emit phase complete event
            self._emitter.emit(EventType.PHASE_COMPLETE, f"Phase complete: {phase}", {
                "phase": phase,
                "success": result.success,
                "files_count": len(result.files_generated),
                "issues_count": len(result.issues),
                "fixes_count": len(result.fixes_applied),
            })
            
            if not result.success:
                self._logger.warning(f"Phase {phase} had issues: {result.issues}")
                # Continue anyway - we'll try to fix issues
            
            self.gen_context.mark_phase_complete(phase, result)
        
        # Final cross-phase verification
        self._logger.info("\n" + "="*50)
        self._logger.info("CROSS-PHASE VERIFICATION")
        self._logger.info("="*50)
        
        final_issues = await self._verify_cross_phase()
        
        if final_issues:
            self._logger.info(f"Found {len(final_issues)} cross-phase issues, attempting fixes...")
            await self._fix_cross_phase_issues(final_issues)
        
        # ========== RUNTIME VERIFICATION ==========
        # Actually try to run the generated code!
        self._logger.info("\n" + "="*50)
        self._logger.info("RUNTIME VERIFICATION")
        self._logger.info("="*50)
        
        self._emitter.emit(EventType.PHASE_START, "Runtime verification", {
            "phase": "runtime_verify",
            "description": "Testing if generated code actually runs",
        })
        
        runtime_report = await self._run_runtime_verification()
        
        # If runtime verification failed, try to fix and re-verify
        if not runtime_report.overall_success:
            runtime_report = await self._fix_runtime_issues(runtime_report)
        
        self._emitter.emit(EventType.PHASE_COMPLETE, "Runtime verification complete", {
            "phase": "runtime_verify",
            "success": runtime_report.overall_success,
            "backend_issues": sum(1 for r in runtime_report.backend_results if not r.success),
            "frontend_issues": sum(1 for r in runtime_report.frontend_results if not r.success),
        })
        
        duration = (datetime.now() - start_time).total_seconds()
        
        success = all(r.success for r in self.phase_results.values())
        
        # Complete checkpoint
        if self._checkpoint:
            self._checkpoint.complete_generation(success)
        
        # Emit generation complete event
        self._emitter.emit(
            EventType.GENERATION_COMPLETE if success else EventType.GENERATION_ERROR,
            f"Generation {'complete' if success else 'finished with issues'}",
            {
                "success": success,
                "name": name,
                "total_files": len(self.gen_context.files),
                "duration": duration,
                "phases_completed": len(self.gen_context.completed_phases),
            }
        )
        
        return {
            "success": success,
            "name": name,
            "output_dir": str(env_dir),
            "phases": {
                phase: {
                    "success": result.success,
                    "files": result.files_generated,
                    "issues": result.issues,
                    "fixes": result.fixes_applied,
                }
                for phase, result in self.phase_results.items()
            },
            "total_files": len(self.gen_context.files),
            "duration": duration,
        }
    
    async def _run_phase(self, phase: str) -> PhaseResult:
        """Run a single generation phase"""
        start_time = datetime.now()
        
        # Get or create agent for this phase
        agent = await self._get_phase_agent(phase)
        
        # Define what this phase should generate
        phase_spec = self._get_phase_spec(phase)
        
        # INJECT MEMORY CONTEXT for this phase
        # This allows agents to know about files from previous phases
        memory_context = self._recall_relevant_context(phase)
        if memory_context:
            self._logger.info(f"  Injecting {len(memory_context)} chars of memory context")
            # Store in working memory for agent access
            self._shared_memory.working.set("phase_context", memory_context)
            self._shared_memory.working.set("current_phase", phase)
        
        # Execute phase with INTELLIGENT iterative generation
        result = PhaseResult(phase=phase, success=True)
        files_this_iteration = []
        existing_files = list(self.gen_context.files.keys())
        
        max_iterations = 3
        for iteration in range(max_iterations):
            self._logger.info(f"  Iteration {iteration + 1}/{max_iterations}")
            
            # High-level phase thinking
            self._emitter.emit(EventType.THINK_START, f"Thinking about {phase} phase", {
                "topic": f"Phase: {phase}, Iteration: {iteration + 1}",
                "context": f"Existing files: {len(existing_files)}",
            })
            
            analysis = await agent.think(
                task=phase_spec["description"],
                context=f"Phase: {phase}\nIteration: {iteration + 1}\nExisting files: {existing_files}"
            )
            
            self._emitter.emit(EventType.THINK_RESULT, f"Analysis complete", {
                "result": analysis,
            })
            self._logger.info(f"  Analysis: {str(analysis)[:100]}...")
            
            # ========== DYNAMIC FILE PLANNING ==========
            # LLM decides what files to generate, not hardcoded list!
            self._logger.info(f"  [PLAN] Dynamically planning files for {phase}...")
            
            planned_files = await agent.plan_phase_files(
                phase=phase,
                phase_description=phase_spec["description"],
                env_name=self.gen_context.name,
                env_description=self.gen_context.description,
                existing_files=existing_files,
                reference_files=phase_spec.get("files", []),  # Hints, not requirements
            )
            
            self._logger.info(f"  [PLAN] LLM planned {len(planned_files)} files:")
            for pf in planned_files[:5]:
                self._logger.info(f"    - {pf.get('path', 'unknown')}")
            if len(planned_files) > 5:
                self._logger.info(f"    ... and {len(planned_files) - 5} more")
            
            # Emit file plan event with details
            self._emitter.emit(EventType.FILE_PLAN, f"Planned {len(planned_files)} files", {
                "phase": phase,
                "files": [f.get("path", "unknown") for f in planned_files],
                "details": [
                    {"path": f.get("path", ""), "purpose": f.get("purpose", "")[:100]}
                    for f in planned_files[:10]
                ],
            })
            
            # Save planned files to checkpoint
            if self._checkpoint:
                self._checkpoint.set_phase_planned_files(
                    phase, 
                    [f.get("path", "") for f in planned_files]
                )
            
            # Generate files with PER-FILE intelligence
            for file_spec in planned_files:
                file_path = file_spec["path"]
                
                # Skip if already generated and verified
                if file_path in self.gen_context.files:
                    existing = self.gen_context.files[file_path]
                    if existing.verified and not existing.issues:
                        continue
                
                # Skip if file already complete in checkpoint (for resume)
                # Now validates content - if content is invalid, file is not considered complete
                if self._checkpoint:
                    if self._checkpoint.is_file_complete(file_path, validate_content=True):
                        self._logger.info(f"  [SKIP] File already complete and valid: {file_path}")
                        continue
                    elif self._checkpoint.get_file_status(file_path) == "complete":
                        # File was marked complete but validation failed
                        self._logger.warning(f"  [INVALID] File marked complete but content invalid: {file_path}")
                        self._checkpoint.invalidate_file(file_path)
                        # Continue to regenerate
                
                # Start file in checkpoint
                if self._checkpoint:
                    self._checkpoint.start_file(file_path, phase)
                
                # ========== INTELLIGENT PRE-GENERATION ==========
                # Step 1: Think BEFORE generating this specific file
                self._logger.info(f"  [THINK] Pre-generation analysis for: {file_path}")
                self._emitter.emit(EventType.THINK_START, f"Pre-thinking for {file_path}", {
                    "topic": f"Analyzing how to generate: {file_path}",
                    "purpose": file_spec.get("purpose", ""),
                })
                
                pre_thinking = await agent.think_before_file(
                    file_path=file_path,
                    purpose=file_spec.get("purpose", ""),
                    existing_files=existing_files + files_this_iteration,
                )
                
                self._emitter.emit(EventType.THINK_RESULT, f"Pre-thinking complete", {
                    "result": {
                        "approach": pre_thinking.get("approach", ""),
                        "needs_context": pre_thinking.get("needs_context", []),
                        "needs_grep": pre_thinking.get("needs_grep", []),
                        "considerations": pre_thinking.get("considerations", []),
                    },
                })
                
                # Step 2: Dynamically gather context based on thinking
                if pre_thinking.get("needs_context") or pre_thinking.get("needs_grep"):
                    self._logger.info(f"  [GATHER] Collecting context...")
                    # Emit tool calls for context gathering
                    for ctx_file in pre_thinking.get("needs_context", []):
                        self._emitter.emit(EventType.TOOL_CALL, f"read_file: {ctx_file}", {
                            "tool": "read_file",
                            "target": ctx_file,
                        })
                    for pattern in pre_thinking.get("needs_grep", []):
                        self._emitter.emit(EventType.TOOL_CALL, f"grep: {pattern}", {
                            "tool": "grep",
                            "target": pattern,
                        })
                    dynamic_context = await agent.gather_context_dynamically(pre_thinking)
                else:
                    dynamic_context = ""
                
                # Step 3: Build dependencies (static + dynamic)
                all_dependencies = list(file_spec.get("dependencies", []))
                
                # Add files the agent decided it needs
                for needed_file in pre_thinking.get("needs_context", []):
                    if needed_file not in all_dependencies:
                        all_dependencies.append(needed_file)
                
                # Add recent files from this iteration
                priority_keywords = ["models", "schemas", "auth", "types", "config"]
                relevant_prev = sorted(
                    [f for f in files_this_iteration if f not in all_dependencies],
                    key=lambda f: any(kw in f.lower() for kw in priority_keywords),
                    reverse=True
                )[:5]
                all_dependencies.extend(relevant_prev)
                
                # ========== GENERATION ==========
                self._logger.info(f"  [GENERATE] {file_path}")
                
                # Emit file start event
                self._emitter.emit(EventType.FILE_START, f"Generating: {file_path}", {
                    "path": file_path,
                    "purpose": file_spec.get("purpose", ""),
                    "phase": phase,
                })
                
                # Include agent's approach in instructions
                enhanced_instructions = file_spec.get("instructions", "")
                if pre_thinking.get("approach"):
                    enhanced_instructions += f"\n\nAPPROACH: {pre_thinking['approach']}"
                if pre_thinking.get("considerations"):
                    enhanced_instructions += f"\n\nBE CAREFUL OF:\n" + "\n".join(f"- {c}" for c in pre_thinking["considerations"])
                if dynamic_context:
                    enhanced_instructions += f"\n\nADDITIONAL CONTEXT GATHERED:\n{dynamic_context[:2000]}"
                
                code = await agent.generate_file(
                    file_path=file_path,
                    purpose=file_spec.get("purpose", ""),
                    instructions=enhanced_instructions,
                    dependencies=all_dependencies,
                )
                
                if not code:
                    self._logger.warning(f"  [FAIL] Failed to generate: {file_path}")
                    self._emitter.emit(EventType.FILE_ERROR, f"Failed to generate: {file_path}", {
                        "path": file_path,
                        "error": "No code generated",
                    })
                    continue
                
                # ========== POST-GENERATION REFLECTION ==========
                self._logger.info(f"  [REFLECT] Analyzing generated code...")
                self._emitter.emit(EventType.REFLECT_START, f"Reflecting on: {file_path}", {
                    "path": file_path,
                    "context": f"Lines: {len(code.split(chr(10))) if code else 0}",
                })
                
                reflection = await agent.reflect_on_file(file_path, code)
                
                quality = reflection.get("quality", "good")
                
                # Emit reflection result
                self._emitter.emit(EventType.REFLECT_RESULT, f"Reflection: {quality}", {
                    "path": file_path,
                    "quality": quality,
                    "issues": reflection.get("issues", []),
                    "checks": reflection.get("checks_performed", []),
                })
                
                # ========== FIX/REGENERATE LOOP ==========
                max_fix_attempts = 3
                fix_attempt = 0
                file_valid = (quality == "good")
                
                while not file_valid and fix_attempt < max_fix_attempts:
                    fix_attempt += 1
                    self._logger.warning(f"  [FIX ATTEMPT {fix_attempt}/{max_fix_attempts}] Quality: {quality}")
                    
                    if quality == "regenerate":
                        issues_to_fix = reflection.get("issues", [])
                        
                        # Check if this is a JSON/YAML file with syntax errors - these need regeneration
                        is_data_file = file_path.endswith(('.json', '.yaml', '.yml'))
                        has_syntax_error = any('SYNTAX' in str(issue).upper() for issue in issues_to_fix)
                        
                        if is_data_file and has_syntax_error:
                            # For JSON/YAML with syntax errors, regenerate completely
                            self._logger.info(f"  [REGENERATE] Data file with syntax error - regenerating completely")
                            self._emitter.emit(EventType.FIX_START, f"Regenerating {file_path} completely", {
                                "path": file_path,
                                "issues": issues_to_fix,
                            })
                            
                            # Regenerate the file completely
                            code = await agent.generate_file(
                                file_path=file_path,
                                purpose=file_spec.get("purpose", ""),
                                instructions=enhanced_instructions + "\n\nPREVIOUS ATTEMPT FAILED WITH SYNTAX ERRORS. Generate complete, valid content.",
                                dependencies=all_dependencies,
                            )
                            
                            if code:
                                self._emitter.emit(EventType.FIX_APPLIED, f"Regenerated: {file_path}", {
                                    "path": file_path,
                                    "fix": "Complete regeneration",
                                })
                        elif issues_to_fix:
                            # Try targeted fixes
                            self._emitter.emit(EventType.FIX_START, f"Fixing {len(issues_to_fix)} issues", {
                                "path": file_path,
                                "issues": issues_to_fix,
                            })
                            fixes = await agent.fix_issues([f"{file_path}: {issue}" for issue in issues_to_fix])
                            if fixes:
                                self._logger.info(f"  [FIXED] Applied {len(fixes)} fixes")
                                for fix in fixes:
                                    self._emitter.emit(EventType.FIX_APPLIED, f"Fixed: {fix[:50]}", {
                                        "path": file_path,
                                        "fix": fix,
                                    })
                                # Re-read the fixed content
                                read_result = await agent.call_tool("read_file", path=file_path)
                                if read_result.success:
                                    code = read_result.data
                            else:
                                # No fixes applied, try regeneration
                                self._logger.info(f"  [REGENERATE] No fixes possible, regenerating...")
                                code = await agent.generate_file(
                                    file_path=file_path,
                                    purpose=file_spec.get("purpose", ""),
                                    instructions=enhanced_instructions + f"\n\nPREVIOUS ISSUES: {issues_to_fix}",
                                    dependencies=all_dependencies,
                                )
                        
                        # Re-validate the file
                        if code:
                            self._logger.info(f"  [RE-VALIDATE] Checking fixed content...")
                            reflection = await agent.reflect_on_file(file_path, code)
                            quality = reflection.get("quality", "good")
                            
                            if quality == "good":
                                file_valid = True
                                self._logger.info(f"  [SUCCESS] File is now valid")
                            else:
                                self._logger.warning(f"  [STILL BROKEN] Quality: {quality}, issues: {reflection.get('issues', [])[:2]}")
                        else:
                            self._logger.error(f"  [FAIL] Regeneration produced no code")
                    
                    elif quality == "needs_improvement":
                        # Minor issues - track but consider file valid
                        self._logger.info(f"  [IMPROVE] Minor issues noted: {reflection.get('issues', [])[:2]}")
                        result.issues.extend(reflection.get("issues", []))
                        file_valid = True  # Accept with minor issues
                    
                    else:
                        file_valid = True
                
                # Final status
                if not file_valid:
                    self._logger.error(f"  [FAIL] Could not fix {file_path} after {max_fix_attempts} attempts")
                    self._emitter.emit(EventType.FILE_ERROR, f"Failed to generate valid: {file_path}", {
                        "path": file_path,
                        "error": f"Quality issues persist after {max_fix_attempts} fix attempts",
                        "final_quality": quality,
                        "issues": reflection.get("issues", []),
                    })
                    # Do NOT mark as complete in checkpoint
                    continue  # Skip to next file
                
                # Emit file complete event - ONLY if file is valid
                lines = len(code.split('\n')) if code else 0
                self._emitter.emit(EventType.FILE_COMPLETE, f"Generated: {file_path}", {
                    "path": file_path,
                    "lines": lines,
                    "quality": quality,
                    "phase": phase,
                })
                
                # Track successful generation
                result.files_generated.append(file_path)
                files_this_iteration.append(file_path)
                existing_files.append(file_path)
                
                # Store in memory
                self._remember_file(
                    file_path=file_path,
                    purpose=file_spec.get("purpose", ""),
                    phase=phase,
                    code_summary=code[:500] if code else "",
                )
                
                # Complete file in checkpoint - ONLY if valid
                if self._checkpoint:
                    import hashlib
                    content_hash = hashlib.md5(code.encode()).hexdigest() if code else None
                    self._checkpoint.complete_file(file_path, content_hash)
            
            # ========== END OF ITERATION REFLECTION ==========
            self._logger.info(f"  [PHASE REFLECT] Checking all generated files...")
            phase_issues = await agent.reflect_on_generation(result.files_generated)
            
            if not phase_issues:
                self._logger.info(f"  [COMPLETE] No issues found, phase complete")
                break
            
            self._logger.info(f"  [ISSUES] Found {len(phase_issues)} issues, fixing...")
            result.issues.extend(phase_issues)
            
            fixes = await agent.fix_issues(phase_issues)
            result.fixes_applied.extend(fixes)
            
            if not fixes:
                self._logger.info(f"  [STOP] No fixes applied, stopping iteration")
                break
        
        result.duration = (datetime.now() - start_time).total_seconds()
        result.success = len(result.issues) == 0 or len(result.fixes_applied) > 0
        
        return result
    
    async def _get_phase_agent(self, phase: str) -> CodeGeneratorAgent:
        """Get or create agent for a phase"""
        if phase not in self._agents:
            # Create agent with same config and SHARED MEMORY
            agent = CodeGeneratorAgent(
                config=self._config,
                output_dir=self.gen_context.output_dir,
                gen_context=self.gen_context,
                shared_memory=self._shared_memory,  # Pass shared memory!
            )
            await agent.initialize()
            self._agents[phase] = agent
        
        return self._agents[phase]
    
    def _get_phase_spec(self, phase: str) -> Dict[str, Any]:
        """Get specification for a phase"""
        name = self.gen_context.name
        class_name = self.gen_context.class_name
        
        specs = {
            "design": {
                "description": f"Design the {self.gen_context.display_name} environment structure",
                "files": [
                    {
                        "path": "env_spec.json",
                        "purpose": "Environment specification",
                        "instructions": f"""Create a JSON specification for {self.gen_context.description}.
Include:
- entities: list of data entities with fields and types
- features: list of features/capabilities
- api_endpoints: list of API endpoints

Example format:
{{
  "name": "{name}",
  "entities": [
    {{"name": "User", "fields": [{{"name": "email", "type": "string"}}]}}
  ],
  "features": ["authentication", "crud"],
  "api_endpoints": ["/api/v1/users", "/api/v1/auth"]
}}""",
                    }
                ],
            },
            "backend": {
                "description": f"Generate FastAPI backend for {self.gen_context.display_name}",
                "files": [
                    {
                        "path": f"{name}_api/models.py",
                        "purpose": "SQLAlchemy database models",
                        "instructions": "Create SQLAlchemy models based on entities in env_spec.json. Use ABSOLUTE imports.",
                        "dependencies": ["env_spec.json"],
                    },
                    {
                        "path": f"{name}_api/schemas.py",
                        "purpose": "Pydantic schemas for API",
                        "instructions": "Create Pydantic schemas for request/response. Use ABSOLUTE imports.",
                        "dependencies": [f"{name}_api/models.py"],
                    },
                    {
                        "path": f"{name}_api/database.py",
                        "purpose": "Database configuration",
                        "instructions": "SQLAlchemy database setup with SQLite default.",
                    },
                    {
                        "path": f"{name}_api/main.py",
                        "purpose": "FastAPI application entry point",
                        "instructions": "Create FastAPI app with CORS, include routers. Use ABSOLUTE imports.",
                        "dependencies": [f"{name}_api/database.py", f"{name}_api/models.py"],
                    },
                    {
                        "path": f"{name}_api/routers/auth.py",
                        "purpose": "Authentication endpoints",
                        "instructions": "JWT-based auth with login/register. Use ABSOLUTE imports (from models import ...).",
                        "dependencies": [f"{name}_api/models.py", f"{name}_api/schemas.py"],
                    },
                    {
                        "path": f"{name}_api/requirements.txt",
                        "purpose": "Python dependencies",
                        "instructions": "List all required packages: fastapi, uvicorn, sqlalchemy, python-jose, passlib, etc.",
                    },
                ],
            },
            "frontend": {
                "description": f"Generate React TypeScript frontend for {self.gen_context.display_name}",
                "files": [
                    {
                        "path": f"{name}_ui/package.json",
                        "purpose": "NPM package configuration",
                        "instructions": "React 18, TypeScript, Vite, React Router, Axios",
                    },
                    {
                        "path": f"{name}_ui/src/main.tsx",
                        "purpose": "React entry point",
                        "instructions": "Render App component",
                    },
                    {
                        "path": f"{name}_ui/src/App.tsx",
                        "purpose": "Main App component with routing",
                        "instructions": "BrowserRouter with routes for Login, Register, Dashboard. ONLY import files that exist.",
                    },
                    {
                        "path": f"{name}_ui/src/contexts/AuthContext.tsx",
                        "purpose": "Authentication context",
                        "instructions": "React context for auth state, login/logout/register functions",
                    },
                    {
                        "path": f"{name}_ui/src/services/api.ts",
                        "purpose": "API client",
                        "instructions": "Axios instance with auth interceptor",
                    },
                    {
                        "path": f"{name}_ui/src/pages/Login.tsx",
                        "purpose": "Login page",
                        "instructions": "Login form using AuthContext",
                    },
                    {
                        "path": f"{name}_ui/src/pages/Dashboard.tsx",
                        "purpose": "Dashboard page",
                        "instructions": "Main dashboard after login",
                    },
                ],
            },
            "openenv": {
                "description": f"Generate OpenEnv-compatible adapter for {self.gen_context.display_name}. OpenEnv is a framework for creating isolated execution environments for RL agents.",
                "files": [
                    {
                        "path": "openenv_adapter/models.py",
                        "purpose": "OpenEnv Action, Observation, State dataclasses",
                        "instructions": f"""Create dataclasses for OpenEnv interface:

1. {class_name}Action - Actions the agent can take:
   - action_type: str (e.g., 'login', 'create_event', 'navigate', 'click')
   - parameters: Dict[str, Any] (action-specific parameters)

2. {class_name}Observation - What the agent observes after an action:
   - page_content: str (current page content summary)
   - elements: List[Dict] (interactable UI elements)
   - message: str (feedback message)
   - success: bool

3. {class_name}State - Full environment state:
   - user_logged_in: bool
   - current_page: str
   - session_data: Dict
   - timestamp: datetime

Include to_dict() and from_dict() methods for serialization.""",
                        "dependencies": ["env_spec.json"],
                    },
                    {
                        "path": "openenv_adapter/server/environment.py",
                        "purpose": "OpenEnv Environment class - the core implementation",
                        "instructions": f"""Create {class_name}Environment class that:

1. Inherits from a base Environment pattern
2. Implements these methods:
   - reset() -> Observation: Reset environment to initial state
   - step(action: Action) -> StepResult: Execute action, return (observation, reward, done)
   - state() -> State: Get current environment state
   - close(): Cleanup resources

3. Connects to the backend API ({name}_api) to perform actual operations
4. Maintains browser/session state (can use httpx or requests)
5. Parses responses into Observation format

Example step() implementation pattern:
- Parse action type and parameters
- Call appropriate backend API endpoint
- Capture response and transform to Observation
- Calculate reward (e.g., 1.0 for success, -0.1 for failure)
- Determine if episode is done""",
                        "dependencies": ["openenv_adapter/models.py", f"{name}_api/main.py", f"{name}_api/schemas.py"],
                    },
                    {
                        "path": "openenv_adapter/server/main.py",
                        "purpose": "FastAPI server to expose OpenEnv environment over HTTP",
                        "instructions": f"""Create FastAPI app with these endpoints:

1. POST /reset - Reset environment, return initial observation
2. POST /step - Execute action, return StepResult (observation, reward, done)
3. GET /state - Get current environment state
4. GET /health - Health check endpoint

Use the {class_name}Environment class from environment.py.
Include proper error handling and logging.""",
                        "dependencies": ["openenv_adapter/server/environment.py", "openenv_adapter/models.py"],
                    },
                    {
                        "path": "openenv_adapter/requirements.txt",
                        "purpose": "Python dependencies for OpenEnv adapter",
                        "instructions": "Include: fastapi, uvicorn, httpx, pydantic",
                    },
                ],
            },
            "docker": {
                "description": "Generate Docker configuration",
                "files": [
                    {
                        "path": f"{name}_api/Dockerfile",
                        "purpose": "Backend Dockerfile",
                        "instructions": "Python 3.11, install requirements, run uvicorn",
                    },
                    {
                        "path": f"{name}_ui/Dockerfile",
                        "purpose": "Frontend Dockerfile",
                        "instructions": "Node 20, build React app, serve with nginx",
                    },
                    {
                        "path": "docker-compose.yml",
                        "purpose": "Docker Compose configuration",
                        "instructions": f"Services: {name}_api, {name}_ui, with proper ports and networking",
                    },
                ],
            },
        }
        
        return specs.get(phase, {"description": phase, "files": []})
    
    async def _verify_cross_phase(self) -> List[str]:
        """Verify consistency across phases"""
        issues = []
        
        # Check: Frontend imports match backend endpoints
        api_files = [f for f in self.gen_context.files.keys() if "_api/" in f]
        ui_files = [f for f in self.gen_context.files.keys() if "_ui/" in f]
        
        # Check: Backend routers are included in main.py
        main_file = self.gen_context.get_file(f"{self.gen_context.name}_api/main.py")
        if main_file:
            router_files = [f for f in api_files if "/routers/" in f]
            for router_file in router_files:
                router_name = Path(router_file).stem
                if router_name != "__init__" and f"from routers.{router_name}" not in main_file:
                    issues.append(f"Router {router_name} not imported in main.py")
        
        return issues
    
    async def _fix_cross_phase_issues(self, issues: List[str]) -> List[str]:
        """Fix issues that span multiple phases"""
        fixes = []
        
        for issue in issues:
            if "not imported in main.py" in issue:
                # Add missing router import
                router_name = issue.split()[1]
                main_path = f"{self.gen_context.name}_api/main.py"
                
                agent = await self._get_phase_agent("backend")
                result = await agent.call_tool(
                    "search_replace",
                    path=main_path,
                    old_string="app = FastAPI(",
                    new_string=f"from routers.{router_name} import router as {router_name}_router\n\napp = FastAPI(",
                )
                
                if result.success:
                    fixes.append(f"Added {router_name} router import")
                    # STORE FIX PATTERN IN MEMORY
                    self._remember_fix(
                        issue=issue,
                        fix=f"Add router import for {router_name}",
                        file_path=main_path,
                    )
        
        return fixes
    
    # ========== RUNTIME VERIFICATION ==========
    
    async def _run_runtime_verification(self) -> RuntimeVerificationReport:
        """
        Actually run the generated code to verify it works.
        
        This goes beyond static analysis - we:
        1. Install dependencies
        2. Start the backend server
        3. Test API endpoints
        4. Build the frontend
        """
        self._logger.info("Starting runtime verification...")
        
        verifier = RuntimeVerifier(
            env_dir=self.gen_context.output_dir,
            env_name=self.gen_context.name,
            api_port=8000,
            ui_port=3000,
            timeout=120,
        )
        
        report = await verifier.verify_all()
        
        # Log results
        all_results = (
            report.backend_results +
            report.frontend_results +
            report.docker_results
        )
        
        passed = sum(1 for r in all_results if r.success)
        failed = sum(1 for r in all_results if not r.success)
        
        self._logger.info(f"Runtime verification: {passed} passed, {failed} failed")
        
        for result in all_results:
            status = "✓" if result.success else "✗"
            self._logger.info(f"  {status} {result.name}: {result.message[:100]}")
            
            if not result.success:
                self._emitter.emit(EventType.VERIFICATION_ERROR, f"Runtime error: {result.name}", {
                    "check": result.name,
                    "message": result.message,
                    "details": result.details,
                })
        
        return report
    
    async def _fix_runtime_issues(self, report: RuntimeVerificationReport) -> RuntimeVerificationReport:
        """
        Fix issues found during runtime verification.
        
        This is the key innovation - we feed runtime errors back to the LLM
        to fix and then re-verify.
        """
        max_fix_iterations = 3
        
        for iteration in range(max_fix_iterations):
            self._logger.info(f"\n--- Runtime Fix Iteration {iteration + 1}/{max_fix_iterations} ---")
            
            # Collect all failed checks
            failed_checks = []
            
            for result in report.backend_results:
                if not result.success:
                    failed_checks.append({
                        "type": "backend",
                        "check": result.name,
                        "message": result.message,
                        "details": result.details,
                    })
            
            for result in report.frontend_results:
                if not result.success:
                    failed_checks.append({
                        "type": "frontend",
                        "check": result.name,
                        "message": result.message,
                        "details": result.details,
                    })
            
            if not failed_checks:
                self._logger.info("All runtime checks passed!")
                break
            
            self._logger.info(f"Found {len(failed_checks)} runtime issues to fix...")
            
            # Convert runtime errors to issues the agent can fix
            issues_to_fix = await self._analyze_runtime_errors(failed_checks)
            
            if not issues_to_fix:
                self._logger.warning("Could not analyze runtime errors into fixable issues")
                break
            
            self._emitter.emit(EventType.FIX_START, f"Fixing {len(issues_to_fix)} runtime issues", {
                "issues": issues_to_fix[:5],
                "iteration": iteration + 1,
            })
            
            # Get appropriate agent to fix
            fixes_applied = []
            
            for issue in issues_to_fix:
                phase = issue.get("phase", "backend")
                agent = await self._get_phase_agent(phase)
                
                self._logger.info(f"  Fixing: {issue['description'][:80]}...")
                
                fixes = await agent.fix_issues([issue["description"]])
                if fixes:
                    fixes_applied.extend(fixes)
                    for fix in fixes:
                        self._emitter.emit(EventType.FIX_APPLIED, f"Fixed: {fix[:50]}", {
                            "fix": fix,
                            "issue": issue["description"],
                        })
                        # Remember this fix pattern
                        self._remember_fix(
                            issue=issue["description"],
                            fix=fix,
                            file_path=issue.get("file", "unknown"),
                        )
            
            if not fixes_applied:
                self._logger.warning("No fixes could be applied")
                break
            
            self._logger.info(f"Applied {len(fixes_applied)} fixes, re-verifying...")
            
            # Re-run verification
            report = await self._run_runtime_verification()
            
            if report.overall_success:
                self._logger.info("All runtime checks now pass!")
                break
        
        return report
    
    async def _analyze_runtime_errors(self, failed_checks: List[Dict]) -> List[Dict]:
        """
        Analyze runtime errors and convert them to issues the agent can fix.
        
        This uses LLM to understand the error and suggest which file needs fixing.
        """
        issues = []
        
        for check in failed_checks:
            check_name = check["check"]
            message = check["message"]
            details = check.get("details", {})
            check_type = check["type"]
            
            # Determine phase and likely file based on check type
            if check_type == "backend":
                phase = "backend"
                
                if check_name == "python_syntax":
                    # Syntax errors have specific file info in details
                    errors = details.get("errors", [])
                    for error in errors:
                        # Parse error like "auth.py: invalid syntax (line 10)"
                        parts = error.split(":")
                        if len(parts) >= 2:
                            file_name = parts[0].strip()
                            issues.append({
                                "phase": phase,
                                "file": f"{self.gen_context.name}_api/{file_name}" if not file_name.startswith(self.gen_context.name) else file_name,
                                "description": f"Python syntax error in {file_name}: {':'.join(parts[1:])}",
                            })
                
                elif check_name == "deps_install":
                    # Missing or incompatible dependencies
                    issues.append({
                        "phase": phase,
                        "file": f"{self.gen_context.name}_api/requirements.txt",
                        "description": f"Dependency installation failed: {message}. Check requirements.txt for missing or incorrect packages.",
                    })
                
                elif check_name == "server_start":
                    # Server failed to start - usually import or config error
                    issues.append({
                        "phase": phase,
                        "file": f"{self.gen_context.name}_api/main.py",
                        "description": f"Server failed to start: {message}. Check imports and router configuration in main.py.",
                    })
                    
                    # Also check for import errors in message
                    if "ModuleNotFoundError" in message or "ImportError" in message:
                        # Try to extract the problematic module
                        import re
                        match = re.search(r"No module named '(\w+)'", message)
                        if match:
                            module = match.group(1)
                            issues.append({
                                "phase": phase,
                                "file": f"{self.gen_context.name}_api/routers/auth.py",
                                "description": f"Import error: module '{module}' not found. Use absolute imports: from {self.gen_context.name}_api.module import ...",
                            })
                
                elif check_name == "health_check":
                    # Health check failed
                    issues.append({
                        "phase": phase,
                        "file": f"{self.gen_context.name}_api/main.py",
                        "description": f"Health check endpoint failed: {message}. Ensure /health endpoint exists.",
                    })
                
                elif check_name == "auth_endpoints":
                    # Auth endpoints failed
                    issues.append({
                        "phase": phase,
                        "file": f"{self.gen_context.name}_api/routers/auth.py",
                        "description": f"Auth endpoints failed: {message}. Check /api/auth/register and /api/auth/login routes.",
                    })
            
            elif check_type == "frontend":
                phase = "frontend"
                
                if check_name == "npm_install":
                    issues.append({
                        "phase": phase,
                        "file": f"{self.gen_context.name}_ui/package.json",
                        "description": f"NPM install failed: {message}. Check package.json for invalid dependencies.",
                    })
                
                elif check_name == "typescript_check":
                    # TypeScript errors - parse the output
                    issues.append({
                        "phase": phase,
                        "file": f"{self.gen_context.name}_ui/src/App.tsx",
                        "description": f"TypeScript errors: {message}. Fix type errors in frontend code.",
                    })
        
        return issues
    
    # ===== Memory Persistence =====
    
    def save_memory(self, filepath: str = None) -> None:
        """
        Save learned patterns to file for persistence across sessions.
        
        This allows the generator to learn from past generations and
        apply successful fix patterns to future environments.
        """
        if filepath is None:
            filepath = str(self.output_dir / ".generator_memory.json")
        
        self._shared_memory.save(filepath)
        self._logger.info(f"Saved memory to {filepath}")
    
    def load_memory(self, filepath: str = None) -> bool:
        """
        Load previously learned patterns from file.
        
        Returns True if memory was loaded successfully.
        """
        if filepath is None:
            filepath = str(self.output_dir / ".generator_memory.json")
        
        try:
            if Path(filepath).exists():
                self._shared_memory.load(filepath)
                self._logger.info(f"Loaded memory from {filepath}")
                return True
        except Exception as e:
            self._logger.warning(f"Failed to load memory: {e}")
        
        return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about current memory state"""
        stats = self._shared_memory.stats()
        
        # Count fix patterns
        fix_patterns = self._shared_memory.long_term.search("FIX PATTERN", limit=100)
        stats["fix_patterns_learned"] = len(fix_patterns)
        
        return stats
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process generation task"""
        params = task.task_params
        
        result = await self.generate_environment(
            name=params.get("name", "generated_env"),
            description=params.get("description", "A generated environment"),
            domain_type=params.get("domain_type", "custom"),
        )
        
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=result["success"],
            result_data=result,
        )

