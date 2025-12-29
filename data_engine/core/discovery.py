"""
HuggingFace Dataset Discovery Module

Searches HuggingFace Hub for datasets matching requirements inferred from
user instructions and entity specifications.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from huggingface_hub import HfApi, DatasetInfo

logger = logging.getLogger(__name__)


@dataclass
class DataRequirements:
    """Requirements for dataset discovery."""
    domain: str  # e.g., "e-commerce", "social-media", "news"
    entities: Dict[str, List[str]]  # entity_name -> required_fields
    search_queries: List[str] = field(default_factory=list)
    min_records: int = 1000
    max_records: Optional[int] = None
    required_fields: List[str] = field(default_factory=list)
    preferred_fields: List[str] = field(default_factory=list)


@dataclass
class DatasetCandidate:
    """A candidate dataset from HuggingFace."""
    dataset_id: str
    description: str
    downloads: int
    likes: int
    tags: List[str]
    size_category: Optional[str]  # e.g., "1K<n<10K", "10K<n<100K"
    columns: List[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def url(self) -> str:
        return f"https://huggingface.co/datasets/{self.dataset_id}"


class DatasetDiscovery:
    """Discovers relevant datasets on HuggingFace Hub."""

    # Domain keywords for inferring domain from instructions
    DOMAIN_KEYWORDS = {
        "e-commerce": [
            "product", "shopping", "store", "catalog", "cart", "checkout",
            "ebay", "amazon", "shop", "buy", "sell", "price", "inventory",
            "e-commerce", "ecommerce", "marketplace", "retail"
        ],
        "social-media": [
            "post", "feed", "social", "twitter", "reddit", "comment",
            "like", "share", "follow", "user", "profile", "timeline"
        ],
        "news": [
            "article", "news", "blog", "headline", "journalist", "publish",
            "media", "press", "story", "reporter"
        ],
        "real-estate": [
            "property", "house", "apartment", "listing", "rent", "real estate",
            "home", "housing", "realtor", "mortgage"
        ],
        "restaurant": [
            "restaurant", "food", "menu", "order", "delivery", "cuisine",
            "dining", "recipe", "meal", "dish"
        ],
        "travel": [
            "hotel", "flight", "booking", "travel", "trip", "destination",
            "vacation", "tourism", "reservation"
        ],
    }

    # Search queries for each domain
    DOMAIN_SEARCH_QUERIES = {
        "e-commerce": [
            "amazon products",
            "e-commerce products dataset",
            "retail products",
            "shopping dataset",
            "product catalog",
        ],
        "social-media": [
            "twitter dataset",
            "reddit posts",
            "social media dataset",
            "user comments",
        ],
        "news": [
            "news articles dataset",
            "news headlines",
            "journalism dataset",
        ],
        "real-estate": [
            "real estate listings",
            "housing dataset",
            "property listings",
        ],
        "restaurant": [
            "restaurant dataset",
            "food reviews",
            "menu dataset",
            "yelp dataset",
        ],
        "travel": [
            "hotel reviews",
            "travel dataset",
            "booking dataset",
        ],
    }

    # Entity to field mappings for common domains
    ENTITY_FIELD_MAPPINGS = {
        "e-commerce": {
            "Product": ["name", "title", "price", "description", "image", "category", "rating"],
            "Category": ["name", "slug", "parent"],
            "User": ["email", "name", "username"],
            "Order": ["total", "status", "items"],
            "Review": ["rating", "text", "comment", "author"],
        },
        "social-media": {
            "Post": ["content", "text", "body", "author", "timestamp", "created"],
            "User": ["username", "name", "avatar", "bio"],
            "Comment": ["text", "content", "author"],
        },
        "news": {
            "Article": ["title", "headline", "content", "body", "author", "date"],
            "Author": ["name", "bio"],
            "Category": ["name", "slug"],
        },
    }

    # Known good datasets for domains (curated recommendations)
    RECOMMENDED_DATASETS = {
        "e-commerce": [
            "milistu/AMAZON-Products-2023",
            "McAuley-Lab/Amazon-Reviews-2023",
            "spacemanidol/product-search-corpus",
        ],
        "social-media": [
            "sentiment140",
            "tweet_eval",
        ],
        "news": [
            "cnn_dailymail",
            "multi_news",
        ],
    }

    def __init__(self):
        self.api = HfApi()

    def infer_domain(self, instruction: str) -> str:
        """Infer the domain from a natural language instruction."""
        instruction_lower = instruction.lower()

        domain_scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in instruction_lower)
            if score > 0:
                domain_scores[domain] = score

        if not domain_scores:
            logger.warning(f"Could not infer domain from instruction: {instruction}")
            return "general"

        best_domain = max(domain_scores, key=domain_scores.get)
        logger.info(f"Inferred domain '{best_domain}' from instruction (score: {domain_scores[best_domain]})")
        return best_domain

    def infer_requirements(
        self,
        instruction: str,
        entities: Optional[Dict[str, Any]] = None
    ) -> DataRequirements:
        """
        Infer dataset requirements from instruction and entity spec.

        Args:
            instruction: Natural language description (e.g., "e-commerce website like eBay")
            entities: Entity definitions from spec.project.json

        Returns:
            DataRequirements object with inferred requirements
        """
        domain = self.infer_domain(instruction)

        # Build required fields from entities
        entity_fields = {}
        required_fields = []

        if entities:
            domain_mappings = self.ENTITY_FIELD_MAPPINGS.get(domain, {})
            for entity_name, entity_def in entities.items():
                # Get expected fields for this entity type
                expected = domain_mappings.get(entity_name, [])

                # Also extract fields from entity definition if available
                if isinstance(entity_def, dict):
                    defined_fields = list(entity_def.get("fields", {}).keys())
                    entity_fields[entity_name] = defined_fields or expected
                else:
                    entity_fields[entity_name] = expected

                required_fields.extend(entity_fields.get(entity_name, []))

        # Get search queries for domain
        search_queries = self.DOMAIN_SEARCH_QUERIES.get(domain, [f"{domain} dataset"])

        # Determine scale from instruction
        min_records = 1000
        if any(word in instruction.lower() for word in ["large", "big", "production", "real"]):
            min_records = 10000
        elif any(word in instruction.lower() for word in ["demo", "small", "sample"]):
            min_records = 100

        return DataRequirements(
            domain=domain,
            entities=entity_fields,
            search_queries=search_queries,
            min_records=min_records,
            required_fields=list(set(required_fields)),
        )

    def search(
        self,
        requirements: DataRequirements,
        limit: int = 20
    ) -> List[DatasetCandidate]:
        """
        Search HuggingFace Hub for datasets matching requirements.

        Args:
            requirements: DataRequirements object
            limit: Maximum number of candidates to return

        Returns:
            List of DatasetCandidate objects, sorted by score
        """
        candidates = []
        seen_ids = set()

        # First, check recommended datasets for this domain
        recommended = self.RECOMMENDED_DATASETS.get(requirements.domain, [])
        for dataset_id in recommended:
            try:
                info = self.api.dataset_info(dataset_id)
                candidate = self._info_to_candidate(info)
                candidate.score = 100  # Boost recommended datasets
                candidates.append(candidate)
                seen_ids.add(dataset_id)
                logger.info(f"Found recommended dataset: {dataset_id}")
            except Exception as e:
                logger.debug(f"Could not fetch recommended dataset {dataset_id}: {e}")

        # Search using queries
        for query in requirements.search_queries[:3]:  # Limit queries to avoid rate limits
            try:
                results = self.api.list_datasets(
                    search=query,
                    sort="downloads",
                    direction=-1,
                    limit=limit,
                )

                for info in results:
                    if info.id in seen_ids:
                        continue
                    seen_ids.add(info.id)

                    candidate = self._info_to_candidate(info)
                    candidates.append(candidate)

            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")

        # Score and rank candidates
        scored_candidates = []
        for candidate in candidates:
            if candidate.score == 0:  # Don't re-score recommended
                candidate.score = self._score_candidate(candidate, requirements)
            scored_candidates.append(candidate)

        # Sort by score descending
        scored_candidates.sort(key=lambda c: c.score, reverse=True)

        return scored_candidates[:limit]

    def _info_to_candidate(self, info: DatasetInfo) -> DatasetCandidate:
        """Convert HuggingFace DatasetInfo to DatasetCandidate."""
        return DatasetCandidate(
            dataset_id=info.id,
            description=getattr(info, 'description', '') or "",
            downloads=getattr(info, 'downloads', 0) or 0,
            likes=getattr(info, 'likes', 0) or 0,
            tags=list(info.tags) if hasattr(info, 'tags') and info.tags else [],
            size_category=getattr(info, 'size_category', None),
            columns=[],  # Will be populated when dataset is loaded
        )

    def _score_candidate(
        self,
        candidate: DatasetCandidate,
        requirements: DataRequirements
    ) -> float:
        """Score a candidate dataset based on requirements."""
        score = 0.0

        # Popularity score (log scale)
        if candidate.downloads > 0:
            import math
            score += min(30, math.log10(candidate.downloads) * 10)

        # Likes bonus
        score += min(10, candidate.likes)

        # Description relevance
        desc_lower = candidate.description.lower()
        for field in requirements.required_fields:
            if field.lower() in desc_lower:
                score += 5

        # Domain keyword match
        domain_keywords = self.DOMAIN_KEYWORDS.get(requirements.domain, [])
        for kw in domain_keywords:
            if kw in desc_lower:
                score += 3

        # Tag relevance
        for tag in candidate.tags:
            tag_lower = tag.lower()
            if requirements.domain in tag_lower:
                score += 10
            for kw in domain_keywords[:5]:
                if kw in tag_lower:
                    score += 2

        # Size category bonus
        if candidate.size_category:
            size_scores = {
                "n<1K": -10,
                "1K<n<10K": 5,
                "10K<n<100K": 15,
                "100K<n<1M": 20,
                "n>1M": 10,  # Too large might be slower
            }
            score += size_scores.get(candidate.size_category, 0)

        return score

    def get_dataset_schema(self, dataset_id: str) -> Dict[str, Any]:
        """
        Get the schema (column names and types) of a dataset.

        Args:
            dataset_id: HuggingFace dataset ID

        Returns:
            Dictionary with column information
        """
        try:
            from datasets import load_dataset

            # Load just a small sample to inspect schema
            ds = load_dataset(dataset_id, split="train", streaming=True)
            sample = next(iter(ds))

            schema = {}
            for key, value in sample.items():
                schema[key] = {
                    "type": type(value).__name__,
                    "sample": str(value)[:100] if value else None
                }

            return schema

        except Exception as e:
            logger.error(f"Failed to get schema for {dataset_id}: {e}")
            return {}

    def discover(
        self,
        instruction: str,
        entities: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[DatasetCandidate]:
        """
        High-level discovery: infer requirements and search.

        Args:
            instruction: Natural language description
            entities: Entity definitions
            limit: Max candidates to return

        Returns:
            List of ranked DatasetCandidate objects
        """
        requirements = self.infer_requirements(instruction, entities)
        logger.info(f"Inferred requirements: domain={requirements.domain}, "
                   f"min_records={requirements.min_records}")

        candidates = self.search(requirements, limit=limit)

        if candidates:
            logger.info(f"Found {len(candidates)} candidate datasets. "
                       f"Top: {candidates[0].dataset_id} (score: {candidates[0].score:.1f})")
        else:
            logger.warning("No candidate datasets found")

        return candidates
