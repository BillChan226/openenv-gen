import requests
from typing import Any, Dict

# Define types for better readability
State = Dict[str, Any]
Observation = Dict[str, Any]
Action = Dict[str, Any]


class CalendarEnvironment:
    def __init__(self, api_base_url: str) -> None:
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.state = {}  # Initialize the state

    def reset(self) -> Observation:
        """
        Resets the environment to its initial state.
        """
        self.state = {}  # Reset state to initial conditions
        # Ideally, here we would call an API endpoint to reset the environment
        # For simplicity, we're just resetting the local state.
        return self._get_initial_observation()

    def step(self, action: Action) -> Observation:
        """
        Executes an action in the environment and returns the new state.
        """
        action_type = action.get("type")
        if action_type == "login":
            return self._handle_login(action)
        elif action_type == "logout":
            return self._handle_logout(action)
        elif action_type in ["create", "read", "update", "delete"]:
            return self._handle_crud(action)
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    @property
    def state(self) -> State:
        """
        Returns the current state of the environment.
        """
        return self.state

    def _get_initial_observation(self) -> Observation:
        """
        Helper method to return the initial observation after reset.
        """
        # This method would typically involve calling an API to get the initial state
        return self.state

    def _handle_login(self, action: Action) -> Observation:
        """
        Handles user login action.
        """
        response = self.session.post(f"{self.api_base_url}/login", json=action.get("data"))
        if response.status_code == 200:
            self.state["user"] = response.json()
            return {"success": True, "data": self.state["user"]}
        else:
            return {"success": False, "error": response.text}

    def _handle_logout(self, action: Action) -> Observation:
        """
        Handles user logout action.
        """
        response = self.session.post(f"{self.api_base_url}/logout")
        if response.status_code == 200:
            self.state.pop("user", None)
            return {"success": True}
        else:
            return {"success": False, "error": response.text}

    def _handle_crud(self, action: Action) -> Observation:
        """
        Handles CRUD operations for entities.
        """
        entity = action.get("entity")
        method_map = {
            "create": "post",
            "read": "get",
            "update": "put",
            "delete": "delete"
        }
        method = method_map.get(action["type"])
        url = f"{self.api_base_url}/{entity}"

        if action["type"] == "read":
            response = self.session.request(method, url, params=action.get("data"))
        else:
            response = self.session.request(method, url, json=action.get("data"))

        if response.status_code in (200, 201):
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": response.text}