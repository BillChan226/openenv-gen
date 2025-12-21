"""
Browser Tools - Headless browser operations for frontend debugging
Inspired by OpenHands browser capabilities
"""
import asyncio
import logging
import base64
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

from utils.tool import BaseTool, ToolResult, ToolCategory

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class BrowserState:
    """Tracks browser session state"""
    browser: Optional[Any] = None
    context: Optional[Any] = None
    page: Optional[Any] = None
    console_logs: List[Dict] = field(default_factory=list)
    network_errors: List[Dict] = field(default_factory=list)
    current_url: str = ""
    

class BrowserManager:
    """Manages browser lifecycle and state"""
    
    _instance: Optional['BrowserManager'] = None
    
    def __init__(self, screenshot_dir: Optional[Path] = None):
        self.state = BrowserState()
        self.screenshot_dir = screenshot_dir or Path("./screenshots")
        self._playwright = None
        self._logger = logging.getLogger(__name__)
    
    @classmethod
    def get_instance(cls, screenshot_dir: Optional[Path] = None) -> 'BrowserManager':
        if cls._instance is None:
            cls._instance = cls(screenshot_dir)
        return cls._instance
    
    async def ensure_browser(self) -> bool:
        """Ensure browser is started"""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        
        if self.state.browser is None:
            try:
                self._playwright = await async_playwright().start()
                self.state.browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                self.state.context = await self.state.browser.new_context(
                    viewport={'width': 1280, 'height': 720}
                )
                self.state.page = await self.state.context.new_page()
                
                # Setup console and network listeners
                self.state.page.on("console", self._on_console)
                self.state.page.on("response", self._on_response)
                self.state.page.on("pageerror", self._on_page_error)
                
                return True
            except Exception as e:
                self._logger.error(f"Failed to start browser: {e}")
                return False
        return True
    
    def _on_console(self, msg):
        """Capture console messages"""
        self.state.console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "location": str(msg.location) if msg.location else None,
        })
    
    def _on_response(self, response):
        """Capture network errors"""
        if response.status >= 400:
            self.state.network_errors.append({
                "url": response.url,
                "status": response.status,
                "method": response.request.method,
            })
    
    def _on_page_error(self, error):
        """Capture page errors"""
        self.state.console_logs.append({
            "type": "error",
            "text": str(error),
            "location": "page",
        })
    
    async def close(self):
        """Close browser"""
        if self.state.page:
            await self.state.page.close()
        if self.state.context:
            await self.state.context.close()
        if self.state.browser:
            await self.state.browser.close()
        if self._playwright:
            await self._playwright.stop()
        
        self.state = BrowserState()
        BrowserManager._instance = None


class BrowserNavigateTool(BaseTool):
    """Navigate to a URL and capture page state"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_navigate", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_navigate",
                "description": "Navigate browser to a URL and capture console errors, network errors, and page content. Use this to debug frontend issues.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to (e.g., http://localhost:3000)"
                        },
                        "wait_for": {
                            "type": "string",
                            "enum": ["load", "domcontentloaded", "networkidle"],
                            "description": "Wait condition (default: networkidle)"
                        }
                    },
                    "required": ["url"]
                }
            }
        }
    
    async def execute(self, url: str, wait_for: str = "networkidle", **kwargs) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult.fail("Playwright not installed. Run: pip install playwright && playwright install chromium")
        
        if not await self.browser.ensure_browser():
            return ToolResult.fail("Failed to start browser")
        
        try:
            # Clear previous logs
            self.browser.state.console_logs.clear()
            self.browser.state.network_errors.clear()
            
            # Navigate
            response = await self.browser.state.page.goto(
                url, 
                wait_until=wait_for,
                timeout=30000
            )
            
            self.browser.state.current_url = url
            
            # Wait a bit for any async errors
            await asyncio.sleep(1)
            
            # Get page info
            title = await self.browser.state.page.title()
            content = await self.browser.state.page.content()
            
            # Filter console errors (ignore browser extension errors)
            console_errors = [
                log for log in self.browser.state.console_logs 
                if log["type"] == "error" and not self._is_extension_error(log["text"])
            ]
            
            # Filter network errors for our domain
            our_network_errors = [
                err for err in self.browser.state.network_errors
                if "localhost" in err["url"]
            ]
            
            result = {
                "url": url,
                "title": title,
                "status": response.status if response else None,
                "console_errors": console_errors[:10],  # Limit
                "network_errors": our_network_errors[:10],
                "content_preview": content[:500] + "..." if len(content) > 500 else content,
                "has_errors": len(console_errors) > 0 or len(our_network_errors) > 0,
            }
            
            return ToolResult.ok(result)
            
        except Exception as e:
            return ToolResult.fail(f"Navigation failed: {str(e)}")
    
    def _is_extension_error(self, text: str) -> bool:
        patterns = ["chrome-extension://", "moz-extension://", "extensions::", "background.js"]
        return any(p in text for p in patterns)


class BrowserScreenshotTool(BaseTool):
    """Take a screenshot of the current page"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_screenshot", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_screenshot",
                "description": "Take a screenshot of the current browser page. Returns base64 encoded image.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "full_page": {
                            "type": "boolean",
                            "description": "Capture full page or just viewport (default: false)"
                        },
                        "save_path": {
                            "type": "string",
                            "description": "Optional path to save screenshot"
                        }
                    },
                    "required": []
                }
            }
        }
    
    async def execute(self, full_page: bool = False, save_path: Optional[str] = None, **kwargs) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult.fail("Playwright not installed")
        
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            screenshot_bytes = await self.browser.state.page.screenshot(full_page=full_page)
            
            if save_path:
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(screenshot_bytes)
            
            # Return base64 for inline viewing
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
            
            return ToolResult.ok({
                "saved_to": save_path,
                "size_bytes": len(screenshot_bytes),
                "base64_preview": screenshot_b64[:100] + "..." if len(screenshot_b64) > 100 else screenshot_b64,
            })
            
        except Exception as e:
            return ToolResult.fail(f"Screenshot failed: {str(e)}")


class BrowserGetConsoleTool(BaseTool):
    """Get console logs from current page"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_console", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_console",
                "description": "Get JavaScript console logs from the current page. Use this to see frontend errors.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter_type": {
                            "type": "string",
                            "enum": ["all", "error", "warning", "log"],
                            "description": "Filter by message type (default: all)"
                        }
                    },
                    "required": []
                }
            }
        }
    
    async def execute(self, filter_type: str = "all", **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        logs = self.browser.state.console_logs
        
        if filter_type != "all":
            logs = [log for log in logs if log["type"] == filter_type]
        
        # Filter out extension errors
        logs = [
            log for log in logs 
            if not any(p in log.get("text", "") for p in ["chrome-extension://", "moz-extension://"])
        ]
        
        return ToolResult.ok({
            "url": self.browser.state.current_url,
            "total_logs": len(logs),
            "logs": logs[:20],  # Limit to 20
        })


class BrowserClickTool(BaseTool):
    """Click an element on the page"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_click", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_click",
                "description": "Click an element on the page using a CSS selector or text content.",
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
                        }
                    },
                    "required": []
                }
            }
        }
    
    async def execute(self, selector: Optional[str] = None, text: Optional[str] = None, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            if selector:
                await self.browser.state.page.click(selector, timeout=5000)
                return ToolResult.ok(f"Clicked element: {selector}")
            elif text:
                await self.browser.state.page.click(f"text={text}", timeout=5000)
                return ToolResult.ok(f"Clicked element with text: {text}")
            else:
                return ToolResult.fail("Provide either selector or text")
                
        except Exception as e:
            return ToolResult.fail(f"Click failed: {str(e)}")


class BrowserFillTool(BaseTool):
    """Fill an input field"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_fill", category=ToolCategory.RUNTIME, **kwargs)
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


class BrowserGetElementsTool(BaseTool):
    """Get elements matching a selector"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_elements", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_elements",
                "description": "Find elements on the page matching a selector. Returns element info.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector to find elements"
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
            elements = await self.browser.state.page.query_selector_all(selector)
            
            element_info = []
            for i, el in enumerate(elements[:10]):  # Limit to 10
                tag = await el.evaluate("el => el.tagName")
                text = await el.inner_text() if await el.is_visible() else ""
                attrs = await el.evaluate("el => Array.from(el.attributes).map(a => ({name: a.name, value: a.value}))")
                
                element_info.append({
                    "index": i,
                    "tag": tag,
                    "text": text[:100] if text else "",
                    "attributes": attrs[:5],  # Limit attributes
                })
            
            return ToolResult.ok({
                "selector": selector,
                "count": len(elements),
                "elements": element_info,
            })
            
        except Exception as e:
            return ToolResult.fail(f"Query failed: {str(e)}")


class BrowserEvaluateTool(BaseTool):
    """Execute JavaScript in the page context"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_eval", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_eval",
                "description": "Execute JavaScript code in the browser page context. Use to inspect state or debug.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "JavaScript code to execute"
                        }
                    },
                    "required": ["script"]
                }
            }
        }
    
    async def execute(self, script: str, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            result = await self.browser.state.page.evaluate(script)
            return ToolResult.ok({
                "script": script[:100] + "..." if len(script) > 100 else script,
                "result": str(result)[:500] if result else None,
            })
        except Exception as e:
            return ToolResult.fail(f"Eval failed: {str(e)}")


class BrowserCloseTool(BaseTool):
    """Close the browser"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_close", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_close",
                "description": "Close the browser session.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        try:
            await self.browser.close()
            return ToolResult.ok("Browser closed")
        except Exception as e:
            return ToolResult.fail(f"Close failed: {str(e)}")


class BrowserWaitTool(BaseTool):
    """Wait for an element to appear or a condition to be met"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_wait", category=ToolCategory.RUNTIME, **kwargs)
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


class BrowserScrollTool(BaseTool):
    """Scroll the page"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_scroll", category=ToolCategory.RUNTIME, **kwargs)
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
                # Scroll element into view
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
            else:  # down
                await self.browser.state.page.evaluate(f"window.scrollBy(0, {pixels})")
                return ToolResult.ok(f"Scrolled down {pixels}px")
        except Exception as e:
            return ToolResult.fail(f"Scroll failed: {str(e)}")


class BrowserHoverTool(BaseTool):
    """Hover over an element"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_hover", category=ToolCategory.RUNTIME, **kwargs)
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


class BrowserSelectTool(BaseTool):
    """Select an option from a dropdown"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_select", category=ToolCategory.RUNTIME, **kwargs)
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


class BrowserGetAttributeTool(BaseTool):
    """Get an attribute from an element"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_get_attribute", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_get_attribute",
                "description": "Get the value of an attribute from an element. Use to check src, href, disabled, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for the element"
                        },
                        "attribute": {
                            "type": "string",
                            "description": "Attribute name to get (e.g., 'href', 'src', 'disabled')"
                        }
                    },
                    "required": ["selector", "attribute"]
                }
            }
        }
    
    async def execute(self, selector: str, attribute: str, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            value = await self.browser.state.page.get_attribute(selector, attribute, timeout=5000)
            return ToolResult.ok({
                "selector": selector,
                "attribute": attribute,
                "value": value
            })
        except Exception as e:
            return ToolResult.fail(f"Get attribute failed: {str(e)}")


class BrowserGetTextTool(BaseTool):
    """Get text content from an element"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_get_text", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_get_text",
                "description": "Get text content from an element. Use to verify displayed content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for the element"
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
            text = await self.browser.state.page.inner_text(selector, timeout=5000)
            return ToolResult.ok({
                "selector": selector,
                "text": text
            })
        except Exception as e:
            return ToolResult.fail(f"Get text failed: {str(e)}")


class BrowserCheckVisibleTool(BaseTool):
    """Check if an element is visible"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_is_visible", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_is_visible",
                "description": "Check if an element is visible on the page. Use for verifying UI state.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for the element"
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
            is_visible = await self.browser.state.page.is_visible(selector, timeout=5000)
            return ToolResult.ok({
                "selector": selector,
                "is_visible": is_visible
            })
        except Exception as e:
            return ToolResult.fail(f"Visibility check failed: {str(e)}")


class BrowserPressKeyTool(BaseTool):
    """Press a keyboard key"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_press_key", category=ToolCategory.RUNTIME, **kwargs)
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


class BrowserGetNetworkErrorsTool(BaseTool):
    """Get all network errors captured during page load"""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_network_errors", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_network_errors",
                "description": "Get all network errors (4xx, 5xx responses) captured since page navigation. Use to debug API issues.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        errors = [
            err for err in self.browser.state.network_errors
            if "localhost" in err.get("url", "")
        ]
        
        return ToolResult.ok({
            "url": self.browser.state.current_url,
            "total_errors": len(errors),
            "errors": errors[:20],
        })


class BrowserCheckAccessibilityTool(BaseTool):
    """Check page accessibility - find elements without proper labels, alt text, etc."""
    
    def __init__(self, browser_manager: BrowserManager, **kwargs):
        super().__init__(name="browser_check_a11y", category=ToolCategory.RUNTIME, **kwargs)
        self.browser = browser_manager
    
    @property
    def tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "browser_check_a11y",
                "description": "Check basic accessibility issues: images without alt, buttons without labels, form inputs without labels.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        if not self.browser.state.page:
            return ToolResult.fail("No page open. Use browser_navigate first.")
        
        try:
            issues = await self.browser.state.page.evaluate("""
                () => {
                    const issues = [];
                    
                    // Images without alt
                    document.querySelectorAll('img').forEach((img, i) => {
                        if (!img.alt && !img.getAttribute('aria-label')) {
                            issues.push({type: 'img-no-alt', selector: `img:nth-of-type(${i+1})`, src: img.src});
                        }
                    });
                    
                    // Buttons without accessible text
                    document.querySelectorAll('button').forEach((btn, i) => {
                        const text = btn.textContent?.trim();
                        const ariaLabel = btn.getAttribute('aria-label');
                        const title = btn.getAttribute('title');
                        if (!text && !ariaLabel && !title) {
                            issues.push({type: 'button-no-label', selector: `button:nth-of-type(${i+1})`});
                        }
                    });
                    
                    // Form inputs without labels
                    document.querySelectorAll('input, select, textarea').forEach((input, i) => {
                        const id = input.id;
                        const ariaLabel = input.getAttribute('aria-label');
                        const placeholder = input.placeholder;
                        const hasLabel = id && document.querySelector(`label[for="${id}"]`);
                        
                        if (!hasLabel && !ariaLabel && !placeholder) {
                            issues.push({type: 'input-no-label', selector: `${input.tagName.toLowerCase()}:nth-of-type(${i+1})`});
                        }
                    });
                    
                    // Links without text
                    document.querySelectorAll('a').forEach((link, i) => {
                        const text = link.textContent?.trim();
                        const ariaLabel = link.getAttribute('aria-label');
                        if (!text && !ariaLabel) {
                            issues.push({type: 'link-no-text', selector: `a:nth-of-type(${i+1})`, href: link.href});
                        }
                    });
                    
                    return issues;
                }
            """)
            
            return ToolResult.ok({
                "url": self.browser.state.current_url,
                "total_issues": len(issues),
                "issues": issues[:20],
            })
        except Exception as e:
            return ToolResult.fail(f"Accessibility check failed: {str(e)}")


def create_browser_tools(screenshot_dir: Optional[Path] = None) -> List[BaseTool]:
    """Create all browser tools with shared browser manager"""
    if not PLAYWRIGHT_AVAILABLE:
        logging.warning("Playwright not installed. Browser tools will not be available.")
        return []
    
    browser_manager = BrowserManager.get_instance(screenshot_dir)
    
    return [
        # Core navigation and inspection
        BrowserNavigateTool(browser_manager),
        BrowserScreenshotTool(browser_manager),
        BrowserGetConsoleTool(browser_manager),
        BrowserGetNetworkErrorsTool(browser_manager),
        
        # Interaction
        BrowserClickTool(browser_manager),
        BrowserFillTool(browser_manager),
        BrowserSelectTool(browser_manager),
        BrowserHoverTool(browser_manager),
        BrowserPressKeyTool(browser_manager),
        
        # Waiting and scrolling
        BrowserWaitTool(browser_manager),
        BrowserScrollTool(browser_manager),
        
        # Element inspection
        BrowserGetElementsTool(browser_manager),
        BrowserGetTextTool(browser_manager),
        BrowserGetAttributeTool(browser_manager),
        BrowserCheckVisibleTool(browser_manager),
        
        # Advanced
        BrowserEvaluateTool(browser_manager),
        BrowserCheckAccessibilityTool(browser_manager),
        
        # Lifecycle
        BrowserCloseTool(browser_manager),
    ]

