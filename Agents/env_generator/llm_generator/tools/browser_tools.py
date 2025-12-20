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


def create_browser_tools(screenshot_dir: Optional[Path] = None) -> List[BaseTool]:
    """Create all browser tools with shared browser manager"""
    if not PLAYWRIGHT_AVAILABLE:
        logging.warning("Playwright not installed. Browser tools will not be available.")
        return []
    
    browser_manager = BrowserManager.get_instance(screenshot_dir)
    
    return [
        BrowserNavigateTool(browser_manager),
        BrowserScreenshotTool(browser_manager),
        BrowserGetConsoleTool(browser_manager),
        BrowserClickTool(browser_manager),
        BrowserFillTool(browser_manager),
        BrowserGetElementsTool(browser_manager),
        BrowserEvaluateTool(browser_manager),
        BrowserCloseTool(browser_manager),
    ]

