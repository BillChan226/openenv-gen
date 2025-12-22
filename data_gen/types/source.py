import abc

class DataSource(abc.ABC):
    @abc.abstractmethod
    def generate_content(self, query: str, save_path: str) -> str:
        pass

class WebScraperSource(DataSource):
    def generate_content(self, query: str, save_path: str) -> str:
        pass

class DiffusionSource(DataSource):
    def generate_content(self, prompt: str, save_path: str) -> str:
        pass