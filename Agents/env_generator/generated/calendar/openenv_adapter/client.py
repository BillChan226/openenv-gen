import requests
from typing import Any, Dict, Optional


class CalendarEnv:
    """
    CalendarEnv wraps HTTP calls to an environment server for calendar operations.
    """

    def __init__(self, base_url: str) -> None:
        """
        Initialize CalendarEnv with the server's base URL.
        """
        self.base_url = base_url

    @classmethod
    def from_docker_image(cls, image_name: str, port: int = 5000) -> 'CalendarEnv':
        """
        Create a CalendarEnv instance from a Docker image.
        This method assumes the Docker container exposes the environment server on the specified port.
        """
        # This is a placeholder for actual Docker container management
        # In a real scenario, you would start the Docker container here and get its IP address
        base_url = f"http://localhost:{port}"
        return cls(base_url)

    def reset(self) -> Dict[str, Any]:
        """
        Resets the environment to its initial state.
        """
        try:
            response = requests.post(f"{self.base_url}/reset")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise ValueError(f"Failed to reset environment: {str(e)}")

    def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform an action in the environment and return the new state.
        """
        try:
            response = requests.post(f"{self.base_url}/step", json=action)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise ValueError(f"Failed to perform step: {str(e)}")

    def state(self) -> Dict[str, Any]:
        """
        Retrieve the current state of the environment.
        """
        try:
            response = requests.get(f"{self.base_url}/state")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise ValueError(f"Failed to get state: {str(e)}")