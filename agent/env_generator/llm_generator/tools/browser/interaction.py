"""
Browser Interaction Tools - Click, Fill, Select, Hover, Key Press, Scroll, Wait
"""
from typing import Dict, Any, Optional

from utils.tool import BaseTool, ToolResult, ToolCategory
from ._manager import BrowserManager, PLAYWRIGHT_AVAILABLE


class BrowserClickTool(BaseTool):
    """Click an element on the page"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_click", category=ToolCategory.RUNTIME, **kwargs)
        self.NAME = "browser_click"
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_click",
                "description": "Click an element on the page using stable locators (preferred) or fallback text/selector.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector (e.g., '#login-btn', 'button[type=submit]')"
                        },
                        "text": {
                            "type": "string",
                            "description": "Alternative: click element containing this text"
                        },
                        "testid": {
                            "type": "string",
                            "description": "Preferred: data-testid value (clicks element [data-testid=\"...\"])"
                        },
                        "aria_label": {
                            "type": "string",
                            "description": "Preferred: aria-label value (clicks element matching [aria-label=\"...\"])"
                        },
                        "role": {
                            "type": "string",
                            "description": "Preferred: ARIA role for get_by_role (e.g., 'button', 'link', 'textbox')"
                        },
                        "name": {
                            "type": "string",
                            "description": "Accessible name used with role-based queries (works with role)"
                        }
                    },
                    "required": []
                }
            }
        }
    
    async def execute(
        self,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        testid: Optional[str] = None,
        aria_label: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            # Priority: stable locators first
            if testid:
                await self.browser.state.page.click(f'[data-testid="{testid}"]', timeout=5000)
                return ToolResult.ok(f"Clicked element by testid: {testid}")
            if aria_label:
                await self.browser.state.page.click(f'[aria-label="{aria_label}"]', timeout=5000)
                return ToolResult.ok(f"Clicked element by aria-label: {aria_label}")
            if role:
                role_selector = f'role={role}'
                if name:
                    role_selector += f'[name="{name}"]'
                await self.browser.state.page.click(role_selector, timeout=5000)
                return ToolResult.ok(
                    f"Clicked element by role: {role}" + (f" name={name}" if name else "")
                )
            # Fallbacks
            if selector:
                await self.browser.state.page.click(selector, timeout=5000)
                return ToolResult.ok(f"Clicked element: {selector}")
            elif text:
                await self.browser.state.page.click(f"text={text}", timeout=5000)
                return ToolResult.ok(f"Clicked element with text: {text}")
            else:
                return ToolResult.fail("Provide one of: testid, aria_label, role, selector, or text")
                
        except Exception as e:
            return ToolResult.fail(f"Click failed: {str(e)}")


class BrowserFillTool(BaseTool):
    """Fill an input field"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_fill", category=ToolCategory.RUNTIME, **kwargs)
        self.NAME = "browser_fill"
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_fill",
                "description": "Fill an input field with text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for the input field"
                        },
                        "value": {
                            "type": "string",
                            "description": "Text to fill"
                        }
                    },
                    "required": ["selector", "value"]
                }
            }
        }
    
    async def execute(self, selector: str, value: str, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            await self.browser.state.page.fill(selector, value, timeout=5000)
            return ToolResult.ok(f"Filled {selector} with '{value}'")
        except Exception as e:
            return ToolResult.fail(f"Fill failed: {str(e)}")


class BrowserSelectTool(BaseTool):
    """Select an option from a dropdown"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_select", category=ToolCategory.RUNTIME, **kwargs)
        self.NAME = "browser_select"
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_select",
                "description": "Select an option from a <select> dropdown.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for the <select> element"
                        },
                        "value": {
                            "type": "string",
                            "description": "Option value to select"
                        },
                        "label": {
                            "type": "string",
                            "description": "Alternative: option text to select"
                        }
                    },
                    "required": ["selector"]
                }
            }
        }
    
    async def execute(self, selector: str, value: Optional[str] = None, label: Optional[str] = None, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            if value:
                await self.browser.state.page.select_option(selector, value=value, timeout=5000)
                return ToolResult.ok(f"Selected value '{value}' in {selector}")
            elif label:
                await self.browser.state.page.select_option(selector, label=label, timeout=5000)
                return ToolResult.ok(f"Selected label '{label}' in {selector}")
            else:
                return ToolResult.fail("Provide either value or label")
        except Exception as e:
            return ToolResult.fail(f"Select failed: {str(e)}")


class BrowserHoverTool(BaseTool):
    """Hover over an element"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_hover", category=ToolCategory.RUNTIME, **kwargs)
        self.NAME = "browser_hover"
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_hover",
                "description": "Hover over an element. Use to reveal tooltips, dropdown menus, or hover states.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for the element to hover over"
                        }
                    },
                    "required": ["selector"]
                }
            }
        }
    
    async def execute(self, selector: str, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            await self.browser.state.page.hover(selector, timeout=5000)
            return ToolResult.ok(f"Hovered over: {selector}")
        except Exception as e:
            return ToolResult.fail(f"Hover failed: {str(e)}")


class BrowserPressKeyTool(BaseTool):
    """Press a keyboard key"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_press_key", category=ToolCategory.RUNTIME, **kwargs)
        self.NAME = "browser_press_key"
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_press_key",
                "description": "Press a keyboard key. Use for Enter, Escape, Tab, shortcuts, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Key to press (e.g., 'Enter', 'Escape', 'Tab', 'ArrowDown', 'Control+a')"
                        }
                    },
                    "required": ["key"]
                }
            }
        }
    
    async def execute(self, key: str, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            await self.browser.state.page.keyboard.press(key)
            return ToolResult.ok(f"Pressed key: {key}")
        except Exception as e:
            return ToolResult.fail(f"Key press failed: {str(e)}")


class BrowserScrollTool(BaseTool):
    """Scroll the page"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_scroll", category=ToolCategory.RUNTIME, **kwargs)
        self.NAME = "browser_scroll"
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_scroll",
                "description": "Scroll the page. Use to navigate long pages or reveal lazy-loaded content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["up", "down", "top", "bottom"],
                            "description": "Scroll direction or position"
                        },
                        "pixels": {
                            "type": "integer",
                            "description": "Pixels to scroll (for up/down). Default: 500"
                        },
                        "selector": {
                            "type": "string",
                            "description": "Optional: scroll to this element"
                        }
                    },
                    "required": []
                }
            }
        }
    
    async def execute(self, direction: str = "down", pixels: int = 500, selector: Optional[str] = None, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            if selector:
                await self.browser.state.page.locator(selector).scroll_into_view_if_needed()
                return ToolResult.ok(f"Scrolled to element: {selector}")
            elif direction == "top":
                await self.browser.state.page.evaluate("window.scrollTo(0, 0)")
                return ToolResult.ok("Scrolled to top")
            elif direction == "bottom":
                await self.browser.state.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                return ToolResult.ok("Scrolled to bottom")
            elif direction == "up":
                await self.browser.state.page.evaluate(f"window.scrollBy(0, -{pixels})")
                return ToolResult.ok(f"Scrolled up {pixels}px")
            else:
                await self.browser.state.page.evaluate(f"window.scrollBy(0, {pixels})")
                return ToolResult.ok(f"Scrolled down {pixels}px")
        except Exception as e:
            return ToolResult.fail(f"Scroll failed: {str(e)}")


class BrowserWaitTool(BaseTool):
    """Wait for an element to appear or a condition to be met"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_wait", category=ToolCategory.RUNTIME, **kwargs)
        self.NAME = "browser_wait"
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_wait",
                "description": "Wait for an element to appear, become visible, or for a timeout. Use for waiting after page navigation or AJAX calls.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector to wait for"
                        },
                        "state": {
                            "type": "string",
                            "enum": ["attached", "visible", "hidden", "detached"],
                            "description": "Element state to wait for (default: visible)"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in milliseconds (default: 10000)"
                        }
                    },
                    "required": ["selector"]
                }
            }
        }
    
    async def execute(self, selector: str, state: str = "visible", timeout: int = 10000, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            await self.browser.state.page.wait_for_selector(
                selector, 
                state=state,
                timeout=timeout
            )
            return ToolResult.ok(f"Element '{selector}' is now {state}")
        except Exception as e:
            return ToolResult.fail(f"Wait failed: {str(e)}")

