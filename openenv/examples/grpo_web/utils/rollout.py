from __future__ import annotations

import random
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from .env_pool import EnvironmentPool

# Add openenv root to path for envs imports
_openenv_root = Path(__file__).parent.parent.parent.parent
if str(_openenv_root) not in sys.path:
    sys.path.insert(0, str(_openenv_root))

# Add src to path for openenv imports
_src_path = _openenv_root / "src"
if _src_path.exists() and str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from forge.observability.metrics import Reduce, record_metric

from envs.browsergym_env import BrowserGymAction, BrowserGymEnv
from .prompts import format_web_prompt, parse_web_action


def setup_task_logger(log_dir: str = "web_task_logs") -> Callable[[str], None]:
    """
    Setup detailed task logging to file.

    Args:
        log_dir: Directory for log files

    Returns:
        Logging function that writes to file and console
    """
    Path(log_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"web_tasks_{timestamp}.log"

    def log(message: str):
        """Write message to log file and console."""
        with open(log_file, "a") as f:
            f.write(f"{message}\n")
        print(message)

    log("=" * 80)
    log(f"GRPO Web Training - Task Log Started at {datetime.now()}")
    log("=" * 80)
    log("")

    return log


async def play_web_task(
    task_idx: int,
    task_id: str,
    server_url: str,
    policy,
    tokenizer,
    task_log: Callable[[str], None],
    rollout_count: int = 0,
    max_steps: int = 15,
    benchmark: str = "miniwob",
    task_name: str = "click-test",
    max_text_chars: int = 4000,
) -> List[Dict[str, Any]]:
    """
    Play a single web navigation task and collect episode data.

    Interacts with a BrowserGym environment, generating actions
    using the policy model and collecting step data for training.

    Args:
        task_idx: Index of this task in the rollout batch
        task_id: Unique identifier for this task attempt
        server_url: OpenEnv BrowserGym server URL
        policy: Policy model (Forge Generator) for action selection
        tokenizer: Tokenizer for prompt formatting
        task_log: Logging function
        rollout_count: Current rollout iteration number
        max_steps: Maximum steps allowed per task
        benchmark: BrowserGym benchmark (miniwob, webarena, etc.)
        task_name: Specific task within the benchmark

    Returns:
        List of step result dicts, each containing:
        - task_id: Task identifier
        - step_num: Step number (0-indexed)
        - prompt: Formatted prompt sent to model
        - response: Model's completion object
        - final_reward: Task outcome reward
        - step_count: Total steps taken
        - max_steps: Maximum steps allowed
        - had_error: Whether action caused an error
    """
    # print(f"  [DEBUG] Creating BrowserGymEnv client for {server_url}...")
    env = BrowserGymEnv(base_url=server_url, message_timeout_s=120.0)
    # print(f"  [DEBUG] BrowserGymEnv client created")

    task_log("")
    task_log("=" * 80)
    task_log(f"TASK {task_idx + 1} (Rollout #{rollout_count + 1}) - ID: {task_id}")
    task_log(f"Benchmark: {benchmark}, Task: {task_name}")
    task_log("=" * 80)

    try:
        # Connect to WebSocket
        # print(f"  [DEBUG] Connecting to WebSocket...")
        env.connect()
        # print(f"  [DEBUG] WebSocket connected successfully")

        # Reset environment with specific task
        # print(f"  [DEBUG] Calling env.reset(task_name={task_name})...")
        result = env.reset(task_name=task_name)
        # print(f"  [DEBUG] env.reset() completed")
        obs = result.observation
        done = False
        step_num = 0
        action_history: List[str] = []
        task_steps: List[Dict[str, Any]] = []

        task_log(f"\nGOAL: {obs.goal}")
        task_log(f"Initial URL: {obs.url}")
        # print(f"  [DEBUG] Got observation - Goal: {obs.goal[:50] if obs.goal else 'None'}...")

        while not done and step_num < max_steps:
            # print(f"  [DEBUG] Step {step_num + 1} - formatting prompt...")
            # Format prompt for model
            prompt = format_web_prompt(
                step_num=step_num,
                observation=obs,
                action_history=action_history,
                tokenizer=tokenizer,
                max_text_chars=max_text_chars,
            )
            # print(f"  [DEBUG] Step {step_num + 1} - prompt formatted, length={len(prompt)}")

            # task_log(f"\n--- Step {step_num + 1} ---")
            # task_log(f"URL: {obs.url}")

            # Generate action using policy
            # print(f"  [DEBUG] Step {step_num + 1} - calling policy.generate.route()...")
            responses = await policy.generate.route(prompt)
            # print(f"  [DEBUG] Step {step_num + 1} - policy.generate.route() completed")
            response = responses[0]

            # Log model output (show full output for debugging)
            # task_log(f"Model output: '{response.text}'")

            # Parse action from model output
            action_str = parse_web_action(response.text)
            action_history.append(action_str)

            # Debug: if noop was parsed, show the full response to understand why
            if action_str == "noop()":
                print(f"  [NOOP DEBUG] Task {task_id} Step {step_num + 1}")
                print(f"  [NOOP DEBUG] Response length: {len(response.text)}")
                print(f"  [NOOP DEBUG] Response (last 500 chars): {response.text[-500:]}")

            # Determine action validity with format compliance checks
            # Following verl-agent's approach: stricter validity checking creates more variance
            is_action_valid = True
            response_text = response.text

            # Check 1: noop() means parsing failed or model explicitly chose to do nothing
            if action_str == "noop()":
                is_action_valid = False

            # Check 2: Proper <think>...</think> format (when thinking mode is enabled)
            # This ensures the model is actually reasoning, not just outputting collapsed text
            has_think_open = "<think>" in response_text.lower()
            has_think_close = "</think>" in response_text.lower()
            if not (has_think_open and has_think_close):
                # Missing proper thinking tags - mark as invalid
                is_action_valid = False

            # Check 3: Response too short (collapsed output)
            # A proper response with thinking should be at least ~50 chars
            MIN_RESPONSE_LENGTH = 50
            if len(response_text.strip()) < MIN_RESPONSE_LENGTH:
                is_action_valid = False
            task_steps.append({
                "step_num": step_num,
                "prompt": prompt,
                "response": response,
                "action": action_str,
                "had_error": False,  # Updated after step
                "is_action_valid": is_action_valid,  # For invalid action penalty
            })

            # Execute action in environment
            result = env.step(BrowserGymAction(action_str=action_str))
            obs = result.observation
            done = result.done

            # Check for action errors
            if obs.last_action_error:
                task_steps[-1]["had_error"] = True
                task_steps[-1]["is_action_valid"] = False  # Action that causes error is invalid
                error_msg = obs.error if hasattr(obs, 'error') else "Unknown error"
                task_log(f"Action error: {error_msg}")

            if done:
                task_log("Task completed!")

            step_num += 1

        # Get final task outcome
        final_reward = result.reward if result.reward is not None else 0.0

        # Log outcome
        outcome = "SUCCESS" if final_reward > 0 else "FAILED"
        task_log("")
        task_log(f"{outcome} - Reward: {final_reward}")
        task_log(f"Task length: {len(task_steps)} steps")
        task_log(f"Actions: {' -> '.join(action_history)}")

        # Prepare return data with final reward assigned to all steps
        # traj_uid is shared by all steps in this trajectory (for GRPO advantage computation)
        traj_uid = str(uuid.uuid4())
        all_step_results = []
        for step_data in task_steps:
            all_step_results.append({
                "task_id": task_id,
                "traj_uid": traj_uid,  # All steps in this trajectory share this ID
                "final_reward": final_reward,
                "step_count": len(task_steps),
                "max_steps": max_steps,
                **step_data,
            })

        # Record metrics
        record_metric("task/count_completed", 1, Reduce.SUM)
        record_metric("task/avg_length", len(task_steps), Reduce.MEAN)
        record_metric("task/success_rate", 1.0 if final_reward > 0 else 0.0, Reduce.MEAN)
        record_metric("task/avg_reward", final_reward, Reduce.MEAN)

        # Track valid action ratio for invalid action penalty monitoring
        valid_actions = sum(1 for s in task_steps if s.get("is_action_valid", True))
        valid_action_ratio = valid_actions / len(task_steps) if task_steps else 1.0
        record_metric("task/valid_action_ratio", valid_action_ratio, Reduce.MEAN)

        return all_step_results

    finally:
        env.close()


async def play_web_task_parallel(
    num_tasks: int,
    env_pool: "EnvironmentPool",
    policy,
    tokenizer,
    task_log: Callable[[str], None],
    task_names: List[str],
    rollout_count: int = 0,
    max_steps: int = 15,
    benchmark: str = "miniwob",
) -> List[Dict[str, Any]]:
    """
    Play multiple web tasks in parallel, respecting server capacity.

    Tasks are processed concurrently but the pool limits simultaneous
    connections to the number of available servers. This prevents
    "Server at capacity" errors.

    Args:
        num_tasks: Number of tasks to play
        env_pool: EnvironmentPool instance for managing server connections
        policy: Policy model for action selection
        tokenizer: Tokenizer for prompts
        task_log: Logging function
        task_names: List of task names (one per task, will cycle if shorter than num_tasks)
        rollout_count: Current rollout iteration
        max_steps: Max steps per task
        benchmark: BrowserGym benchmark

    Returns:
        Combined list of step results from all tasks
    """
    import asyncio

    async def run_task_with_pool(task_idx: int) -> List[Dict[str, Any]]:
        """Run a single task, acquiring a server from the pool."""
        task_id = str(uuid.uuid4())[:8]
        task_name = task_names[task_idx % len(task_names)]

        async with env_pool.acquire() as server_url:
            return await play_web_task(
                task_idx=task_idx,
                task_id=task_id,
                server_url=server_url,
                policy=policy,
                tokenizer=tokenizer,
                task_log=task_log,
                rollout_count=rollout_count,
                max_steps=max_steps,
                benchmark=benchmark,
                task_name=task_name,
            )

    # Create all tasks - the pool's semaphore limits concurrency
    tasks = [run_task_with_pool(task_idx) for task_idx in range(num_tasks)]

    # Run all tasks - pool automatically limits to available servers
    results = await asyncio.gather(*tasks)

    # Flatten results
    all_steps = []
    for task_results in results:
        all_steps.extend(task_results)

    return all_steps


async def play_web_task_with_pool(
    task_idx: int,
    env_pool: "EnvironmentPool",
    policy,
    tokenizer,
    task_log: Callable[[str], None],
    rollout_count: int = 0,
    max_steps: int = 15,
    benchmark: str = "miniwob",
    task_name: str = "click-test",
    max_text_chars: int = 4000,
) -> List[Dict[str, Any]]:
    """
    Play a single web task using a server from the pool.

    This is a convenience wrapper that acquires a server from the pool,
    runs the task, and releases the server automatically.

    Args:
        task_idx: Index of this task in the rollout batch
        env_pool: EnvironmentPool instance
        policy: Policy model for action selection
        tokenizer: Tokenizer for prompt formatting
        task_log: Logging function
        rollout_count: Current rollout iteration number
        max_steps: Maximum steps allowed per task
        benchmark: BrowserGym benchmark
        task_name: Specific task within the benchmark
        max_text_chars: Max chars for observation text

    Returns:
        List of step result dicts
    """
    from .env_pool import EnvironmentPool

    task_id = str(uuid.uuid4())[:8]

    async with env_pool.acquire() as server_url:
        return await play_web_task(
            task_idx=task_idx,
            task_id=task_id,
            server_url=server_url,
            policy=policy,
            tokenizer=tokenizer,
            task_log=task_log,
            rollout_count=rollout_count,
            max_steps=max_steps,
            benchmark=benchmark,
            task_name=task_name,
            max_text_chars=max_text_chars,
        )


def show_web_observation(observation) -> None:
    """
    Pretty print a BrowserGym observation for debugging.

    Args:
        observation: BrowserGymObservation object
    """
    print("=" * 60)
    print("Web Page Observation")
    print("=" * 60)
    print(f"Goal: {observation.goal}")
    print(f"URL: {observation.url}")
    print(f"Has screenshot: {observation.screenshot is not None}")
    print(f"Text length: {len(observation.text or '')} chars")
    print(f"AXTree length: {len(observation.axtree_txt or '')} chars")
    print(f"Pruned HTML length: {len(observation.pruned_html or '')} chars")
    print(f"Last action error: {observation.last_action_error}")
    if hasattr(observation, 'error') and observation.error:
        print(f"Error message: {observation.error}")
    print("=" * 60)


def play_random_web_policy(
    server_url: str,
    num_tasks: int = 10,
    max_steps: int = 10,
) -> Dict[str, Any]:
    """
    Benchmark random policy on web navigation tasks.

    Useful for establishing a baseline before training.

    Args:
        server_url: OpenEnv BrowserGym server URL
        num_tasks: Number of tasks to attempt
        max_steps: Maximum steps per task

    Returns:
        dict with statistics including success rate
    """
    env = BrowserGymEnv(base_url=server_url)
    successes = 0
    failures = 0
    total_steps = 0

    # Random actions (safe ones that won't break things)
    random_actions = [
        "noop()",
        "scroll('down')",
        "scroll('up')",
    ]

    for task_num in range(num_tasks):
        result = env.reset()
        done = False
        step_count = 0

        while not done and step_count < max_steps:
            action = random.choice(random_actions)
            result = env.step(BrowserGymAction(action_str=action))
            done = result.done
            step_count += 1

        total_steps += step_count

        if result.reward and result.reward > 0:
            successes += 1
        else:
            failures += 1

    env.close()

    return {
        "successes": successes,
        "failures": failures,
        "success_rate": successes / num_tasks if num_tasks > 0 else 0,
        "avg_steps": total_steps / num_tasks if num_tasks > 0 else 0,
        "total_tasks": num_tasks,
    }


def play_heuristic_web_policy(
    server_url: str,
    num_tasks: int = 10,
    max_steps: int = 15,
) -> Dict[str, Any]:
    """
    Benchmark a simple heuristic policy.

    Heuristic: Try to click the first clickable element matching the goal.

    Args:
        server_url: BrowserGym server URL
        num_tasks: Number of tasks to attempt
        max_steps: Max steps per task

    Returns:
        Statistics dict
    """
    import re

    env = BrowserGymEnv(base_url=server_url)
    successes = 0
    failures = 0

    for _ in range(num_tasks):
        result = env.reset()
        obs = result.observation
        done = False
        step_count = 0

        while not done and step_count < max_steps:
            # Simple heuristic: find BIDs and click the first one
            bid_pattern = re.compile(r'\[(\d+)\]')
            matches = bid_pattern.findall(obs.axtree_txt or "")

            if matches:
                action = f"click('{matches[0]}')"
            else:
                action = "scroll('down')"

            result = env.step(BrowserGymAction(action_str=action))
            obs = result.observation
            done = result.done
            step_count += 1

        if result.reward and result.reward > 0:
            successes += 1
        else:
            failures += 1

    env.close()

    return {
        "successes": successes,
        "failures": failures,
        "success_rate": successes / num_tasks if num_tasks > 0 else 0,
        "total_tasks": num_tasks,
    }
