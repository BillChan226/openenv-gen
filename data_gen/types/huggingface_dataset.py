from datasets import load_dataset
import pandas as pd
import os
from typing import Optional, List
from .source import DataSource


class HuggingFaceDatasetSource(DataSource):
    """Downloads and converts HuggingFace datasets to CSV format."""

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the HuggingFace dataset source.

        Args:
            cache_dir: Optional directory to cache downloaded datasets
        """
        self.cache_dir = cache_dir

    def generate_content(self, query: str, save_path: str) -> str:
        """
        Download a HuggingFace dataset and convert it to CSV.

        Args:
            query: HuggingFace dataset ID (e.g., "imdb", "squad", "user/dataset")
                   Can optionally include split info: "dataset_id:split" (e.g., "imdb:train")
                   Can include config: "dataset_id:config:split" (e.g., "glue:cola:train")
            save_path: Path where the CSV file will be saved

        Returns:
            Path to the saved CSV file
        """
        # Parse the query to extract dataset_id, config, and split
        dataset_id, config, split = self._parse_query(query)

        try:
            print(f"Loading dataset '{dataset_id}'...")
            if config:
                print(f"  Config: {config}")
            if split:
                print(f"  Split: {split}")

            # Load the dataset
            if config and split:
                dataset = load_dataset(
                    dataset_id,
                    config,
                    split=split,
                    cache_dir=self.cache_dir
                )
            elif config:
                dataset = load_dataset(
                    dataset_id,
                    config,
                    cache_dir=self.cache_dir
                )
            elif split:
                dataset = load_dataset(
                    dataset_id,
                    split=split,
                    cache_dir=self.cache_dir
                )
            else:
                dataset = load_dataset(
                    dataset_id,
                    cache_dir=self.cache_dir
                )

            # Convert to pandas DataFrame
            if hasattr(dataset, 'to_pandas'):
                # Single split dataset
                df = dataset.to_pandas()
            elif isinstance(dataset, dict):
                # Multiple splits - concatenate all splits
                dfs = []
                for split_name, split_data in dataset.items():
                    split_df = split_data.to_pandas()
                    split_df['split'] = split_name  # Add split column
                    dfs.append(split_df)
                df = pd.concat(dfs, ignore_index=True)
            else:
                raise ValueError(f"Unexpected dataset type: {type(dataset)}")

            # Ensure the directory exists
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)

            # Save to CSV
            df.to_csv(save_path, index=False)

            print(f"Dataset saved with {len(df)} rows and {len(df.columns)} columns")

            return save_path

        except Exception as e:
            raise RuntimeError(f"Failed to load HuggingFace dataset '{query}': {str(e)}")

    def _parse_query(self, query: str) -> tuple:
        """
        Parse the query string to extract dataset_id, config, and split.

        Supported formats:
        - "dataset_id"
        - "dataset_id:split"
        - "dataset_id:config:split"

        Args:
            query: Query string

        Returns:
            Tuple of (dataset_id, config, split)
        """
        parts = query.split(':')

        if len(parts) == 1:
            return parts[0], None, None
        elif len(parts) == 2:
            return parts[0], None, parts[1]
        elif len(parts) == 3:
            return parts[0], parts[1], parts[2]
        else:
            raise ValueError(f"Invalid query format: {query}. Expected 'dataset_id', 'dataset_id:split', or 'dataset_id:config:split'")

    def get_dataset_info(self, dataset_id: str) -> dict:
        """
        Get information about a dataset without downloading it.

        Args:
            dataset_id: HuggingFace dataset ID

        Returns:
            Dictionary with dataset information
        """
        from datasets import get_dataset_infos

        try:
            infos = get_dataset_infos(dataset_id)
            return infos
        except Exception as e:
            raise RuntimeError(f"Failed to get info for dataset '{dataset_id}': {str(e)}")

    def list_available_splits(self, dataset_id: str, config: Optional[str] = None) -> List[str]:
        """
        List available splits for a dataset.

        Args:
            dataset_id: HuggingFace dataset ID
            config: Optional config name

        Returns:
            List of available split names
        """
        try:
            if config:
                dataset_info = load_dataset(dataset_id, config, cache_dir=self.cache_dir)
            else:
                dataset_info = load_dataset(dataset_id, cache_dir=self.cache_dir)

            if isinstance(dataset_info, dict):
                return list(dataset_info.keys())
            else:
                return ['train']  # Default split

        except Exception as e:
            raise RuntimeError(f"Failed to list splits for dataset '{dataset_id}': {str(e)}")
