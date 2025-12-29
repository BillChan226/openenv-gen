"""
Data Engine

LLM-powered data engine for intelligent dataset discovery and loading.

Uses LLM to:
1. Infer domain from project instruction
2. Generate search queries for HuggingFace
3. Evaluate dataset quality and relevance
4. Map dataset fields to database schema

This provides smarter, more adaptive behavior compared to rule-based matching.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from jinja2 import Environment, FileSystemLoader

# Setup paths
_TOOLS_DIR = Path(__file__).parent.resolve()
_LLM_GEN_DIR = _TOOLS_DIR.parent
_AGENTS_DIR = _LLM_GEN_DIR.parent.parent
_ENV_GEN_DIR = _AGENTS_DIR.parent.parent

for _path in [str(_LLM_GEN_DIR), str(_AGENTS_DIR), str(_ENV_GEN_DIR)]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from utils.llm import LLM, Message

logger = logging.getLogger(__name__)


@dataclass
class DomainInferenceResult:
    """Result of LLM domain inference."""
    domain: str
    confidence: float
    keywords: List[str]
    entities: List[str]
    search_queries: List[str]
    reasoning: str


@dataclass
class FieldMappingResult:
    """Result of LLM field mapping."""
    mappings: List[Dict[str, Any]]  # [{"source": ..., "target": ..., "transform": ...}]
    unmapped_target: List[str]
    unmapped_source: List[str]
    confidence: float
    notes: str


@dataclass
class DatasetEvaluationResult:
    """Result of LLM dataset evaluation."""
    score: int  # 0-100
    recommendation: str  # highly_recommended, recommended, acceptable, not_recommended, unsuitable
    strengths: List[str]
    weaknesses: List[str]
    field_coverage: Dict[str, List[str]]
    reasoning: str


class DataEngine:
    """
    LLM-powered data engine for intelligent dataset discovery and loading.

    Uses LLM to:
    1. Infer domain from natural language instruction
    2. Generate optimized search queries
    3. Evaluate datasets for quality and relevance
    4. Create field mappings between datasets and database schema
    """

    def __init__(self, llm: LLM):
        """
        Initialize Data Engine.

        Args:
            llm: LLM client for inference
        """
        self.llm = llm

        # Setup Jinja2 for prompts
        prompt_dir = Path(__file__).parent.parent / "prompts"
        self.jinja = Environment(
            loader=FileSystemLoader(str(prompt_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self._logger = logging.getLogger("data_engine")

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Remove markdown code blocks if present
        text = response.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        return json.loads(text.strip())

    async def infer_domain(
        self,
        instruction: str,
        entities: Optional[Dict[str, Any]] = None
    ) -> DomainInferenceResult:
        """
        Infer domain from project instruction using LLM.

        Args:
            instruction: Natural language project description
            entities: Optional entity definitions from spec

        Returns:
            DomainInferenceResult with domain, keywords, entities, queries
        """
        self._logger.info(f"Inferring domain from instruction: {instruction[:100]}...")

        # Render prompt
        prompt = self.jinja.get_template("data_engine/domain_inference.j2").render(
            instruction=instruction,
            entities=entities
        )

        # Call LLM
        messages = [Message.user(prompt)]
        response = await self.llm.complete(messages)

        # Parse response
        try:
            data = self._parse_json_response(response.content)
            result = DomainInferenceResult(
                domain=data.get("domain", "other"),
                confidence=data.get("confidence", 0.0),
                keywords=data.get("keywords", []),
                entities=data.get("entities", []),
                search_queries=data.get("search_queries", []),
                reasoning=data.get("reasoning", "")
            )
            self._logger.info(f"Inferred domain: {result.domain} (confidence: {result.confidence})")
            return result

        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse domain inference response: {e}")
            # Fallback to rule-based inference
            return DomainInferenceResult(
                domain="other",
                confidence=0.0,
                keywords=[],
                entities=[],
                search_queries=[f"{instruction[:50]} dataset"],
                reasoning="LLM response parsing failed, using fallback"
            )

    async def evaluate_dataset(
        self,
        requirement: str,
        dataset_id: str,
        description: str,
        fields: List[str],
        sample: Dict[str, Any],
        downloads: int
    ) -> DatasetEvaluationResult:
        """
        Evaluate a dataset's suitability for the requirement using LLM.

        Args:
            requirement: Natural language requirement description
            dataset_id: HuggingFace dataset ID
            description: Dataset description
            fields: List of field names
            sample: Sample record from dataset
            downloads: Download count

        Returns:
            DatasetEvaluationResult with score and analysis
        """
        self._logger.info(f"Evaluating dataset: {dataset_id}")

        # Format sample for prompt (limit size)
        sample_str = json.dumps(sample, indent=2)
        if len(sample_str) > 1000:
            sample_str = sample_str[:1000] + "\n... (truncated)"

        # Render prompt
        prompt = self.jinja.get_template("data_engine/dataset_evaluation.j2").render(
            requirement=requirement,
            dataset_id=dataset_id,
            description=description[:500] if description else "No description",
            fields=", ".join(fields),
            sample=sample_str,
            downloads=downloads
        )

        # Call LLM
        messages = [Message.user(prompt)]
        response = await self.llm.complete(messages)

        # Parse response
        try:
            data = self._parse_json_response(response.content)
            result = DatasetEvaluationResult(
                score=data.get("score", 0),
                recommendation=data.get("recommendation", "unsuitable"),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                field_coverage=data.get("field_coverage", {}),
                reasoning=data.get("reasoning", "")
            )
            self._logger.info(f"Dataset {dataset_id} score: {result.score} ({result.recommendation})")
            return result

        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse dataset evaluation response: {e}")
            return DatasetEvaluationResult(
                score=0,
                recommendation="unsuitable",
                strengths=[],
                weaknesses=["Failed to evaluate"],
                field_coverage={},
                reasoning="LLM response parsing failed"
            )

    async def generate_field_mapping(
        self,
        target_schema: Dict[str, str],
        dataset_fields: Dict[str, Any]
    ) -> FieldMappingResult:
        """
        Generate field mappings from dataset to database schema using LLM.

        Args:
            target_schema: Database schema {column: type}
            dataset_fields: Dataset fields with sample values

        Returns:
            FieldMappingResult with mappings and analysis
        """
        self._logger.info("Generating field mappings with LLM")

        # Format schemas for prompt
        target_str = "\n".join([f"- {col} ({dtype})" for col, dtype in target_schema.items()])

        dataset_str = ""
        for field, info in dataset_fields.items():
            if isinstance(info, dict):
                sample = info.get("sample", "N/A")
                dtype = info.get("type", "unknown")
                dataset_str += f"- {field}: {dtype}\n  Sample: {str(sample)[:100]}\n"
            else:
                dataset_str += f"- {field}: {str(info)[:100]}\n"

        # Render prompt
        prompt = self.jinja.get_template("data_engine/field_mapping.j2").render(
            target_schema=target_str,
            dataset_fields=dataset_str
        )

        # Call LLM
        messages = [Message.user(prompt)]
        response = await self.llm.complete(messages)

        # Parse response
        try:
            data = self._parse_json_response(response.content)
            result = FieldMappingResult(
                mappings=data.get("mappings", []),
                unmapped_target=data.get("unmapped_target", []),
                unmapped_source=data.get("unmapped_source", []),
                confidence=data.get("confidence", 0.0),
                notes=data.get("notes", "")
            )
            self._logger.info(f"Generated {len(result.mappings)} field mappings (confidence: {result.confidence})")
            return result

        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse field mapping response: {e}")
            return FieldMappingResult(
                mappings=[],
                unmapped_target=list(target_schema.keys()),
                unmapped_source=list(dataset_fields.keys()),
                confidence=0.0,
                notes="LLM response parsing failed"
            )


def create_data_engine(llm: LLM) -> DataEngine:
    """Factory function to create data engine."""
    return DataEngine(llm)
