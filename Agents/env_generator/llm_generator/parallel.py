"""
Parallel Generation Utilities

Analyzes file dependencies to enable parallel generation of independent files.
"""

import asyncio
from typing import Dict, List, Set, Tuple


def build_dependency_graph(file_specs: List[dict]) -> Dict[str, Set[str]]:
    """
    Build a dependency graph from file specifications.
    
    Args:
        file_specs: List of file specs with "path" and "dependencies"
        
    Returns:
        Dict mapping file path to set of dependencies
    """
    graph = {}
    
    for spec in file_specs:
        path = spec.get("path", "")
        deps = set(spec.get("dependencies", []))
        graph[path] = deps
    
    return graph


def get_generation_order(dependency_graph: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Get files grouped by generation order.
    
    Files with no dependencies come first.
    Then files that only depend on the first group.
    And so on...
    
    Args:
        dependency_graph: Dict mapping file path to dependencies
        
    Returns:
        List of lists, where each inner list can be generated in parallel
    """
    remaining = set(dependency_graph.keys())
    generated = set()
    order = []
    
    while remaining:
        # Find files that can be generated now (all deps satisfied)
        batch = []
        for path in remaining:
            deps = dependency_graph.get(path, set())
            # Only consider deps that are in our graph (ignore external deps)
            internal_deps = deps & set(dependency_graph.keys())
            if internal_deps <= generated:
                batch.append(path)
        
        if not batch:
            # Circular dependency or missing dependencies
            # Just generate remaining files one by one
            batch = list(remaining)[:1]
        
        order.append(batch)
        generated.update(batch)
        remaining -= set(batch)
    
    return order


def analyze_parallelism(file_specs: List[dict]) -> dict:
    """
    Analyze parallelism potential for file generation.
    
    Returns analysis with:
    - dependency_graph: the built graph
    - generation_batches: files grouped for parallel generation
    - max_parallelism: maximum files that can be generated in parallel
    - estimated_speedup: theoretical speedup factor
    """
    if not file_specs:
        return {
            "dependency_graph": {},
            "generation_batches": [],
            "max_parallelism": 0,
            "estimated_speedup": 1.0,
        }
    
    graph = build_dependency_graph(file_specs)
    batches = get_generation_order(graph)
    
    max_parallelism = max(len(batch) for batch in batches) if batches else 0
    total_files = len(file_specs)
    
    # Estimate speedup (assuming each file takes same time)
    # Sequential: total_files iterations
    # Parallel: len(batches) iterations
    estimated_speedup = total_files / len(batches) if batches else 1.0
    
    return {
        "dependency_graph": {k: list(v) for k, v in graph.items()},
        "generation_batches": batches,
        "max_parallelism": max_parallelism,
        "estimated_speedup": round(estimated_speedup, 2),
    }


async def generate_batch_parallel(
    batch: List[str],
    generate_func,
    max_concurrency: int = 3,
) -> Dict[str, Tuple[bool, str]]:
    """
    Generate a batch of files in parallel with limited concurrency.
    
    Args:
        batch: List of file paths to generate
        generate_func: Async function that takes file_path and returns (success, code)
        max_concurrency: Maximum number of concurrent generations
        
    Returns:
        Dict mapping file path to (success, code_or_error)
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    results = {}
    
    async def generate_with_semaphore(path: str):
        async with semaphore:
            try:
                result = await generate_func(path)
                return path, result
            except Exception as e:
                return path, (False, str(e))
    
    tasks = [generate_with_semaphore(path) for path in batch]
    completed = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in completed:
        if isinstance(result, Exception):
            # Task itself raised exception
            continue
        path, (success, data) = result
        results[path] = (success, data)
    
    return results


class ParallelGenerator:
    """
    Manages parallel generation of files.
    
    Usage:
        gen = ParallelGenerator(file_specs, generate_func)
        
        async for batch_result in gen.generate():
            print(f"Completed batch: {batch_result}")
    """
    
    def __init__(
        self,
        file_specs: List[dict],
        generate_func,
        max_concurrency: int = 3,
    ):
        self.file_specs = file_specs
        self.generate_func = generate_func
        self.max_concurrency = max_concurrency
        
        # Build spec lookup
        self.spec_by_path = {s["path"]: s for s in file_specs}
        
        # Analyze parallelism
        self.analysis = analyze_parallelism(file_specs)
        self.batches = self.analysis["generation_batches"]
    
    @property
    def max_parallelism(self) -> int:
        return self.analysis["max_parallelism"]
    
    @property
    def estimated_speedup(self) -> float:
        return self.analysis["estimated_speedup"]
    
    async def generate_all(self) -> Dict[str, Tuple[bool, str]]:
        """Generate all files respecting dependencies"""
        all_results = {}
        
        for batch_num, batch in enumerate(self.batches):
            # Generate this batch in parallel
            batch_results = await generate_batch_parallel(
                batch,
                self._wrap_generate,
                max_concurrency=self.max_concurrency,
            )
            all_results.update(batch_results)
        
        return all_results
    
    async def generate_iter(self):
        """Yield results batch by batch"""
        for batch_num, batch in enumerate(self.batches):
            batch_results = await generate_batch_parallel(
                batch,
                self._wrap_generate,
                max_concurrency=self.max_concurrency,
            )
            yield {
                "batch_num": batch_num + 1,
                "total_batches": len(self.batches),
                "files": batch,
                "results": batch_results,
            }
    
    async def _wrap_generate(self, path: str) -> Tuple[bool, str]:
        """Wrapper that passes full spec to generate function"""
        spec = self.spec_by_path.get(path, {"path": path})
        return await self.generate_func(spec)

