"""
OpenEnv Code Snippets

Patterns for OpenEnv-compatible environment adapters.
"""

OPENENV_SNIPPETS = {
    "environment_class": '''
from openenv import Environment, Action, Observation, State, StepResult
from dataclasses import dataclass
from typing import Optional, Any, Dict
import requests


@dataclass
class AppState(State):
    """Application-specific state"""
    user_id: Optional[str] = None
    is_authenticated: bool = False
    current_page: str = "login"
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


@dataclass  
class AppAction(Action):
    """Application-specific action"""
    action_type: str  # "login", "navigate", "create", "update", "delete"
    target: Optional[str] = None  # Page or resource ID
    params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class AppObservation(Observation):
    """Observation after taking an action"""
    success: bool
    message: str
    current_page: str
    visible_elements: list
    data: Optional[Dict[str, Any]] = None


class MyEnvironment(Environment):
    """OpenEnv-compatible environment for my application"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self._state = AppState()
        self._token: Optional[str] = None
    
    def reset(self) -> AppObservation:
        """Reset environment to initial state"""
        self._state = AppState()
        self._token = None
        
        return AppObservation(
            success=True,
            message="Environment reset",
            current_page="login",
            visible_elements=["email_input", "password_input", "login_button", "register_link"],
        )
    
    def step(self, action: AppAction) -> StepResult:
        """Execute an action and return result"""
        try:
            if action.action_type == "login":
                obs = self._handle_login(action.params)
            elif action.action_type == "register":
                obs = self._handle_register(action.params)
            elif action.action_type == "navigate":
                obs = self._handle_navigate(action.target)
            elif action.action_type == "create":
                obs = self._handle_create(action.target, action.params)
            elif action.action_type == "update":
                obs = self._handle_update(action.target, action.params)
            elif action.action_type == "delete":
                obs = self._handle_delete(action.target)
            else:
                obs = AppObservation(
                    success=False,
                    message=f"Unknown action: {action.action_type}",
                    current_page=self._state.current_page,
                    visible_elements=[],
                )
            
            # Calculate reward
            reward = 1.0 if obs.success else -0.1
            done = False  # Customize based on task completion
            
            return StepResult(observation=obs, reward=reward, done=done)
            
        except Exception as e:
            return StepResult(
                observation=AppObservation(
                    success=False,
                    message=str(e),
                    current_page=self._state.current_page,
                    visible_elements=[],
                ),
                reward=-1.0,
                done=False,
            )
    
    def state(self) -> AppState:
        """Get current state"""
        return self._state
    
    def _api_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make API request"""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        
        url = f"{self.api_url}{endpoint}"
        response = requests.request(method, url, json=data, headers=headers)
        response.raise_for_status()
        
        return response.json() if response.content else {}
    
    def _handle_login(self, params: dict) -> AppObservation:
        """Handle login action"""
        result = self._api_request("POST", "/api/auth/login", {
            "email": params.get("email"),
            "password": params.get("password"),
        })
        
        self._token = result.get("access_token")
        self._state.is_authenticated = True
        self._state.user_id = result.get("user", {}).get("id")
        self._state.current_page = "dashboard"
        
        return AppObservation(
            success=True,
            message="Login successful",
            current_page="dashboard",
            visible_elements=["nav_menu", "dashboard_content", "logout_button"],
            data=result.get("user"),
        )
    
    def _handle_register(self, params: dict) -> AppObservation:
        """Handle registration action"""
        self._api_request("POST", "/api/auth/register", {
            "email": params.get("email"),
            "password": params.get("password"),
            "name": params.get("name"),
        })
        
        return AppObservation(
            success=True,
            message="Registration successful",
            current_page="login",
            visible_elements=["email_input", "password_input", "login_button"],
        )
    
    def _handle_navigate(self, target: str) -> AppObservation:
        """Handle navigation"""
        if not self._state.is_authenticated and target != "login":
            return AppObservation(
                success=False,
                message="Must be authenticated",
                current_page="login",
                visible_elements=["email_input", "password_input", "login_button"],
            )
        
        self._state.current_page = target
        visible = self._get_page_elements(target)
        
        return AppObservation(
            success=True,
            message=f"Navigated to {target}",
            current_page=target,
            visible_elements=visible,
        )
    
    def _handle_create(self, resource: str, params: dict) -> AppObservation:
        """Handle create action"""
        result = self._api_request("POST", f"/api/{resource}", params)
        
        return AppObservation(
            success=True,
            message=f"Created {resource}",
            current_page=self._state.current_page,
            visible_elements=self._get_page_elements(self._state.current_page),
            data=result,
        )
    
    def _handle_update(self, resource_id: str, params: dict) -> AppObservation:
        """Handle update action"""
        resource_type, item_id = resource_id.split("/", 1)
        result = self._api_request("PATCH", f"/api/{resource_type}/{item_id}", params)
        
        return AppObservation(
            success=True,
            message=f"Updated {resource_type}",
            current_page=self._state.current_page,
            visible_elements=self._get_page_elements(self._state.current_page),
            data=result,
        )
    
    def _handle_delete(self, resource_id: str) -> AppObservation:
        """Handle delete action"""
        resource_type, item_id = resource_id.split("/", 1)
        self._api_request("DELETE", f"/api/{resource_type}/{item_id}")
        
        return AppObservation(
            success=True,
            message=f"Deleted {resource_type}",
            current_page=self._state.current_page,
            visible_elements=self._get_page_elements(self._state.current_page),
        )
    
    def _get_page_elements(self, page: str) -> list:
        """Get visible elements for a page"""
        elements = {
            "login": ["email_input", "password_input", "login_button", "register_link"],
            "register": ["email_input", "password_input", "name_input", "register_button"],
            "dashboard": ["nav_menu", "dashboard_content", "items_link", "logout_button"],
            "items": ["nav_menu", "items_list", "create_button", "search_input"],
        }
        return elements.get(page, ["nav_menu", "content"])
''',

    "openenv_models": '''
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class Action:
    """Base action class"""
    pass


@dataclass
class Observation:
    """Base observation class"""
    pass


@dataclass  
class State:
    """Base state class"""
    pass


@dataclass
class StepResult:
    """Result of a step in the environment"""
    observation: Observation
    reward: float
    done: bool
    info: Optional[Dict[str, Any]] = None
''',
}

