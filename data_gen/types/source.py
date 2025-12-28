import abc

class DataSource(abc.ABC):
    @abc.abstractmethod
    def generate_content(self, query: str, save_path: str) -> str:
        pass