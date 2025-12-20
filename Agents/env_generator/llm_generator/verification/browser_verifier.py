"""
Browser Verifier - Tests frontend using headless browser
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Page, Browser, Error as PlaywrightError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    PlaywrightError = Exception


@dataclass
class ConsoleMessage:
    """Browser console message"""
    type: str  # 'error', 'warning', 'log', 'info'
    text: str
    location: Optional[str] = None


@dataclass
class PageTestResult:
    """Result of testing a single page"""
    url: str
    success: bool = False
    load_time_ms: float = 0
    title: Optional[str] = None
    console_errors: List[ConsoleMessage] = field(default_factory=list)
    console_warnings: List[ConsoleMessage] = field(default_factory=list)
    network_errors: List[str] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)
    screenshot_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BrowserVerificationReport:
    """Complete browser verification report"""
    base_url: str
    total_pages: int = 0
    passed: int = 0
    failed: int = 0
    results: List[PageTestResult] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        return (self.passed / self.total_pages * 100) if self.total_pages > 0 else 0
    
    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.total_pages > 0
    
    @property
    def total_console_errors(self) -> int:
        return sum(len(r.console_errors) for r in self.results)
    
    @property
    def total_network_errors(self) -> int:
        return sum(len(r.network_errors) for r in self.results)
    
    def summary(self) -> str:
        lines = [
            f"Browser Verification Report ({self.base_url})",
            f"  Pages Tested: {self.total_pages}, Passed: {self.passed}, Failed: {self.failed}",
            f"  Console Errors: {self.total_console_errors}",
            f"  Network Errors: {self.total_network_errors}",
        ]
        
        for r in self.results:
            status = "✓" if r.success else "✗"
            lines.append(f"\n  {status} {r.url}")
            lines.append(f"    Load time: {r.load_time_ms:.0f}ms")
            
            if r.console_errors:
                lines.append(f"    Console Errors ({len(r.console_errors)}):")
                for err in r.console_errors[:3]:
                    lines.append(f"      - {err.text[:100]}")
                if len(r.console_errors) > 3:
                    lines.append(f"      ... and {len(r.console_errors) - 3} more")
            
            if r.network_errors:
                lines.append(f"    Network Errors ({len(r.network_errors)}):")
                for err in r.network_errors[:3]:
                    lines.append(f"      - {err[:100]}")
            
            if r.missing_elements:
                lines.append(f"    Missing Elements: {r.missing_elements}")
            
            if r.error:
                lines.append(f"    Error: {r.error}")
        
        return "\n".join(lines)


class BrowserVerifier:
    """Verifies frontend using headless browser (Playwright)"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        timeout: int = 30000,  # ms
        logger: Optional[logging.Logger] = None,
        screenshot_dir: Optional[Path] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._logger = logger or logging.getLogger(__name__)
        self.screenshot_dir = screenshot_dir
        
        if not PLAYWRIGHT_AVAILABLE:
            self._logger.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")
    
    async def verify_all(
        self,
        pages: Optional[List[str]] = None,
        check_elements: Optional[Dict[str, List[str]]] = None,
    ) -> BrowserVerificationReport:
        """
        Run browser verification tests.
        
        Args:
            pages: List of page paths to test (default: ["/"])
            check_elements: Dict mapping page path to list of selectors to check
        """
        report = BrowserVerificationReport(base_url=self.base_url)
        
        if not PLAYWRIGHT_AVAILABLE:
            result = PageTestResult(
                url=self.base_url,
                success=False,
                error="Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
            report.results.append(result)
            report.total_pages = 1
            report.failed = 1
            return report
        
        # Default pages to test
        if pages is None:
            pages = ["/", "/login"]
        
        # Default elements to check
        if check_elements is None:
            check_elements = {
                "/": ["body", "#root"],
                "/login": ["body", "#root"],
            }
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                
                for page_path in pages:
                    result = await self._test_page(
                        context,
                        page_path,
                        check_elements.get(page_path, []),
                    )
                    report.results.append(result)
                    report.total_pages += 1
                    
                    if result.success:
                        report.passed += 1
                    else:
                        report.failed += 1
                
                await browser.close()
                
        except Exception as e:
            self._logger.error(f"Browser verification error: {e}")
            result = PageTestResult(
                url=self.base_url,
                success=False,
                error=str(e)
            )
            report.results.append(result)
            report.total_pages += 1
            report.failed += 1
        
        return report
    
    async def _test_page(
        self,
        context,
        page_path: str,
        required_elements: List[str],
    ) -> PageTestResult:
        """Test a single page"""
        url = f"{self.base_url}{page_path}"
        result = PageTestResult(url=url)
        
        page = await context.new_page()
        
        # Collect console messages
        def on_console(msg):
            cm = ConsoleMessage(
                type=msg.type,
                text=msg.text,
                location=f"{msg.location.get('url', '')}:{msg.location.get('lineNumber', '')}" if msg.location else None
            )
            if msg.type == "error":
                result.console_errors.append(cm)
            elif msg.type == "warning":
                result.console_warnings.append(cm)
        
        page.on("console", on_console)
        
        # Collect network errors
        def on_response(response):
            if response.status >= 400:
                result.network_errors.append(
                    f"{response.status} {response.request.method} {response.url}"
                )
        
        page.on("response", on_response)
        
        try:
            import time
            start = time.time()
            
            # Navigate to page
            response = await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            
            result.load_time_ms = (time.time() - start) * 1000
            result.title = await page.title()
            
            # Check response
            if response and response.status >= 400:
                result.error = f"Page returned status {response.status}"
                result.success = False
            else:
                # Check required elements
                for selector in required_elements:
                    try:
                        element = await page.query_selector(selector)
                        if element is None:
                            result.missing_elements.append(selector)
                    except Exception:
                        result.missing_elements.append(selector)
                
                # Determine success:
                # - No critical console errors (filter out extension errors)
                critical_errors = [
                    e for e in result.console_errors
                    if not self._is_extension_error(e.text)
                ]
                
                # - No missing required elements
                # - No network errors for our domain
                our_network_errors = [
                    e for e in result.network_errors
                    if "localhost" in e or self.base_url in e
                ]
                
                result.success = (
                    len(critical_errors) == 0 and
                    len(result.missing_elements) == 0 and
                    len(our_network_errors) == 0
                )
                
                if critical_errors:
                    result.error = f"{len(critical_errors)} console error(s)"
                elif result.missing_elements:
                    result.error = f"Missing elements: {result.missing_elements}"
                elif our_network_errors:
                    result.error = f"{len(our_network_errors)} network error(s)"
            
            # Take screenshot on failure
            if not result.success and self.screenshot_dir:
                try:
                    self.screenshot_dir.mkdir(parents=True, exist_ok=True)
                    screenshot_path = self.screenshot_dir / f"failure_{page_path.replace('/', '_')}.png"
                    await page.screenshot(path=str(screenshot_path))
                    result.screenshot_path = str(screenshot_path)
                except Exception as e:
                    self._logger.warning(f"Failed to take screenshot: {e}")
                    
        except PlaywrightError as e:
            result.error = f"Playwright error: {str(e)}"
            result.success = False
        except Exception as e:
            result.error = f"Error: {str(e)}"
            result.success = False
        finally:
            await page.close()
        
        return result
    
    def _is_extension_error(self, error_text: str) -> bool:
        """Check if error is from a browser extension (should be ignored)"""
        extension_patterns = [
            "chrome-extension://",
            "moz-extension://",
            "extensions::",
            "background.js",
            "content.js",
        ]
        return any(p in error_text for p in extension_patterns)


# Convenience function
async def verify_browser(
    base_url: str = "http://localhost:3000",
    pages: Optional[List[str]] = None,
) -> BrowserVerificationReport:
    """Quick browser verification"""
    verifier = BrowserVerifier(base_url=base_url)
    return await verifier.verify_all(pages=pages)

