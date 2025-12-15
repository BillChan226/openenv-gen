"""HTTP Client for the {{ENV_NAME}} environment.

Provides a client interface for interacting with the environment server.
"""

from typing import Any, Dict

from openenv_core.client_types import StepResult
from openenv_core.http_env_client import HTTPEnvClient

from .models import WebAction, WebObservation, WebState


class WebEnvClient(HTTPEnvClient[WebAction, WebObservation]):
    """HTTP client for the generated web environment.

    Usage:
        # From Docker image
        client = WebEnvClient.from_docker_image("{{ENV_NAME}}:latest")

        # From running server
        client = WebEnvClient(base_url="http://localhost:8000")

        # Interact with environment
        result = client.reset()
        result = client.step(WebAction(action_str="click('login-btn')"))
        client.close()
    """

    def _step_payload(self, action: WebAction) -> Dict[str, Any]:
        """Convert action to JSON payload for the server."""
        return {
            "action_str": action.to_action_str(),
            "action_type": action.action_type,
            "selector": action.selector,
            "value": action.value,
            "metadata": action.metadata,
        }

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[WebObservation]:
        """Parse server response into StepResult."""
        obs_data = payload.get("observation", {})

        observation = WebObservation(
            text=obs_data.get("text", ""),
            url=obs_data.get("url", ""),
            screenshot=obs_data.get("screenshot"),
            goal=obs_data.get("goal", ""),
            html=obs_data.get("html", ""),
            axtree_txt=obs_data.get("axtree_txt", ""),
            error=obs_data.get("error", ""),
            last_action_error=obs_data.get("last_action_error", False),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> WebState:
        """Parse server state response."""
        return WebState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_id=payload.get("task_id"),
            task_name=payload.get("task_name", ""),
            goal=payload.get("goal", ""),
            current_url=payload.get("current_url", ""),
            max_steps=payload.get("max_steps"),
            cum_reward=payload.get("cum_reward", 0.0),
            db_state=payload.get("db_state", {}),
        )
