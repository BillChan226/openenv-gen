"""
Image Search Tools - Search and download images from the web

Enables agents to find reference images, icons, and UI components online.
"""

import asyncio
import logging
import re
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tool import BaseTool, ToolResult, create_tool_param, ToolCategory
from workspace import Workspace


class SearchImageTool(BaseTool):
    """Search for images online using various sources."""
    
    NAME = "search_image"
    
    DESCRIPTION = """Search for images online to find design references, icons, or UI components.

Returns a list of image URLs that can be downloaded using download_image.

Examples:
    search_image "atlassian logo"
    search_image "material design button"
    search_image "dashboard UI mockup"
    search_image "notification bell icon svg"

Sources searched:
- Unsplash (free stock photos)
- Iconify (icons and SVGs)
- UI patterns and components

Note: Respect copyright and licensing when using downloaded images.
"""
    
    def __init__(self, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace or Workspace(Path.cwd())
        self._logger = logging.getLogger(__name__)
    
    @property
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for images"
                    },
                    "image_type": {
                        "type": "string",
                        "enum": ["photo", "icon", "ui", "any"],
                        "description": "Type of image to search for (default: any)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)"
                    }
                },
                "required": ["query"]
            }
        )
    
    async def execute(self, query: str, image_type: str = "any", limit: int = 10) -> ToolResult:
        """Search for images"""
        try:
            import aiohttp
        except ImportError:
            return ToolResult(
                success=False,
                error_message="aiohttp not installed. Run: pip install aiohttp"
            )
        
        results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Search based on image type
                if image_type in ["icon", "any"]:
                    icon_results = await self._search_iconify(session, query, limit)
                    results.extend(icon_results)
                
                if image_type in ["photo", "any"]:
                    photo_results = await self._search_unsplash(session, query, limit)
                    results.extend(photo_results)
                
                if image_type in ["ui", "any"]:
                    ui_results = await self._search_ui_patterns(session, query, limit)
                    results.extend(ui_results)
            
            # Deduplicate and limit
            seen_urls = set()
            unique_results = []
            for r in results:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    unique_results.append(r)
                    if len(unique_results) >= limit:
                        break
            
            if not unique_results:
                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "results": [],
                        "count": 0,
                        "message": f"No images found for '{query}'. Try different keywords."
                    }
                )
            
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": unique_results,
                    "count": len(unique_results),
                    "message": f"Found {len(unique_results)} images for '{query}'"
                }
            )
            
        except Exception as e:
            self._logger.error(f"Image search failed: {e}")
            return ToolResult(success=False, error_message=f"Search failed: {e}")
    
    async def _search_iconify(self, session, query: str, limit: int) -> List[Dict]:
        """Search Iconify API for icons"""
        results = []
        try:
            # Iconify search API
            encoded_query = urllib.parse.quote(query)
            url = f"https://api.iconify.design/search?query={encoded_query}&limit={limit}"
            
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    icons = data.get("icons", [])
                    
                    for icon in icons[:limit]:
                        # icon format: "prefix:name"
                        parts = icon.split(":")
                        if len(parts) == 2:
                            prefix, name = parts
                            svg_url = f"https://api.iconify.design/{prefix}/{name}.svg"
                            results.append({
                                "url": svg_url,
                                "title": f"{prefix}:{name}",
                                "source": "iconify",
                                "type": "icon",
                                "format": "svg"
                            })
        except Exception as e:
            self._logger.debug(f"Iconify search failed: {e}")
        
        return results
    
    async def _search_unsplash(self, session, query: str, limit: int) -> List[Dict]:
        """Search Unsplash for photos (using their public source.unsplash.com)"""
        results = []
        try:
            # source.unsplash.com provides direct image URLs
            # We'll generate URLs based on search terms
            encoded_query = urllib.parse.quote(query)
            
            # Generate multiple image URLs with different sizes
            sizes = ["800x600", "1200x800", "400x300"]
            for i, size in enumerate(sizes[:limit]):
                url = f"https://source.unsplash.com/{size}/?{encoded_query}"
                results.append({
                    "url": url,
                    "title": f"Unsplash: {query} ({size})",
                    "source": "unsplash",
                    "type": "photo",
                    "format": "jpg",
                    "license": "Unsplash License (free)"
                })
        except Exception as e:
            self._logger.debug(f"Unsplash search failed: {e}")
        
        return results
    
    async def _search_ui_patterns(self, session, query: str, limit: int) -> List[Dict]:
        """Search for UI patterns and components"""
        results = []
        
        # Provide curated UI resource links based on common queries
        ui_resources = {
            "button": [
                {"url": "https://api.iconify.design/mdi/button-cursor.svg", "title": "Button Icon", "format": "svg"},
            ],
            "navbar": [
                {"url": "https://api.iconify.design/mdi/menu.svg", "title": "Menu Icon", "format": "svg"},
            ],
            "dashboard": [
                {"url": "https://api.iconify.design/mdi/view-dashboard.svg", "title": "Dashboard Icon", "format": "svg"},
            ],
            "notification": [
                {"url": "https://api.iconify.design/mdi/bell.svg", "title": "Notification Bell", "format": "svg"},
            ],
            "search": [
                {"url": "https://api.iconify.design/mdi/magnify.svg", "title": "Search Icon", "format": "svg"},
            ],
            "settings": [
                {"url": "https://api.iconify.design/mdi/cog.svg", "title": "Settings Icon", "format": "svg"},
            ],
            "user": [
                {"url": "https://api.iconify.design/mdi/account.svg", "title": "User Icon", "format": "svg"},
            ],
            "avatar": [
                {"url": "https://api.iconify.design/mdi/account-circle.svg", "title": "Avatar Icon", "format": "svg"},
            ],
        }
        
        # Check if query matches any UI patterns
        query_lower = query.lower()
        for keyword, resources in ui_resources.items():
            if keyword in query_lower:
                for res in resources:
                    results.append({
                        **res,
                        "source": "ui_patterns",
                        "type": "ui"
                    })
        
        return results[:limit]


class DownloadImageTool(BaseTool):
    """Download an image from URL to the workspace."""
    
    NAME = "download_image"
    
    DESCRIPTION = """Download an image from a URL to your workspace.

Use this after search_image to download images you want to use.

Examples:
    download_image "https://example.com/image.png" "design/reference.png"
    download_image "https://api.iconify.design/mdi/home.svg" "assets/icons/home.svg"
    download_image "https://source.unsplash.com/800x600/?nature" "images/background.jpg"

The image will be saved to the specified path in your workspace.
"""
    
    def __init__(self, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace or Workspace(Path.cwd())
        self._logger = logging.getLogger(__name__)
    
    @property
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the image to download"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination path in workspace (e.g., 'images/icon.svg')"
                    }
                },
                "required": ["url", "destination"]
            }
        )
    
    async def execute(self, url: str, destination: str) -> ToolResult:
        """Download image from URL"""
        try:
            import aiohttp
        except ImportError:
            return ToolResult(
                success=False,
                error_message="aiohttp not installed. Run: pip install aiohttp"
            )
        
        # Resolve destination path
        try:
            dest_path = self.workspace.resolve(destination)
        except Exception as e:
            return ToolResult(success=False, error_message=f"Invalid destination: {e}")
        
        # Create parent directory
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30, allow_redirects=True) as resp:
                    if resp.status != 200:
                        return ToolResult(
                            success=False,
                            error_message=f"Download failed: HTTP {resp.status}"
                        )
                    
                    content_type = resp.headers.get("Content-Type", "")
                    
                    # Validate it's an image
                    if not any(t in content_type.lower() for t in ["image", "svg", "octet-stream"]):
                        self._logger.warning(f"Content-Type may not be image: {content_type}")
                    
                    # Read content
                    content = await resp.read()
                    
                    # Check file size (max 50MB)
                    if len(content) > 50 * 1024 * 1024:
                        return ToolResult(
                            success=False,
                            error_message=f"Image too large: {len(content) / 1024 / 1024:.1f}MB. Maximum: 50MB"
                        )
                    
                    # Write to file
                    dest_path.write_bytes(content)
                    
                    size = len(content)
                    size_display = f"{size / 1024:.1f}KB" if size < 1024*1024 else f"{size / 1024 / 1024:.1f}MB"
                    
                    return ToolResult(
                        success=True,
                        data={
                            "url": url,
                            "destination": str(dest_path.relative_to(self.workspace.root)),
                            "absolute_path": str(dest_path),
                            "size": size_display,
                            "content_type": content_type,
                            "message": f"Downloaded to {dest_path.relative_to(self.workspace.root)} ({size_display})"
                        }
                    )
                    
        except asyncio.TimeoutError:
            return ToolResult(success=False, error_message="Download timed out (30s)")
        except Exception as e:
            self._logger.error(f"Download failed: {e}")
            return ToolResult(success=False, error_message=f"Download failed: {e}")


class GoogleImageSearchTool(BaseTool):
    """Search for images using Google Custom Search API.
    
    This provides more comprehensive web image search results including
    UI screenshots, webpage designs, and real-world application references.
    """
    
    NAME = "google_image_search"
    
    DESCRIPTION = """Search for images using Google Custom Search API.

This is the most powerful image search - finds real website screenshots, 
UI designs, and application references from across the web.

Examples:
    google_image_search "jira board screenshot"
    google_image_search "atlassian confluence page design"
    google_image_search "slack message interface"
    google_image_search "github pull request UI"
    google_image_search "notion dashboard design"

Best for:
- Finding real-world UI/UX references
- Website and app screenshots
- Design system examples
- Competitor analysis

Requires GOOGLE_API_KEY and GOOGLE_CX environment variables.
"""
    
    def __init__(self, workspace: Workspace = None, api_key: str = None, cx: str = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace or Workspace(Path.cwd())
        self._logger = logging.getLogger(__name__)
        
        # API credentials from params or environment
        import os
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.cx = cx or os.environ.get("GOOGLE_CX", "")  # Custom Search Engine ID
    
    @property
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for images (be specific, e.g., 'jira board screenshot')"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 10, max: 10)"
                    },
                    "size": {
                        "type": "string",
                        "enum": ["large", "medium", "small", "any"],
                        "description": "Preferred image size (default: any)"
                    },
                    "file_type": {
                        "type": "string",
                        "enum": ["png", "jpg", "gif", "any"],
                        "description": "Preferred file type (default: any)"
                    }
                },
                "required": ["query"]
            }
        )
    
    async def execute(
        self, 
        query: str, 
        num_results: int = 10, 
        size: str = "any",
        file_type: str = "any"
    ) -> ToolResult:
        """Search for images using Google Custom Search API"""
        
        if not self.api_key or not self.cx:
            return ToolResult(
                success=False,
                error_message="Google API credentials not configured. Set GOOGLE_API_KEY and GOOGLE_CX environment variables."
            )
        
        try:
            import aiohttp
        except ImportError:
            return ToolResult(
                success=False,
                error_message="aiohttp not installed. Run: pip install aiohttp"
            )
        
        # Build API URL
        base_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "searchType": "image",
            "num": min(num_results, 10),  # Max 10 per request
        }
        
        # Add size filter
        if size != "any":
            size_map = {"large": "huge", "medium": "medium", "small": "icon"}
            params["imgSize"] = size_map.get(size, "")
        
        # Add file type filter
        if file_type != "any":
            params["fileType"] = file_type
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{base_url}?{urllib.parse.urlencode(params)}"
                
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 403:
                        return ToolResult(
                            success=False,
                            error_message="Google API access denied. Check your API key and quota."
                        )
                    elif resp.status == 400:
                        return ToolResult(
                            success=False,
                            error_message="Invalid request. Check your Custom Search Engine ID (cx)."
                        )
                    elif resp.status != 200:
                        return ToolResult(
                            success=False,
                            error_message=f"Google API error: HTTP {resp.status}"
                        )
                    
                    data = await resp.json()
                    
                    items = data.get("items", [])
                    if not items:
                        return ToolResult(
                            success=True,
                            data={
                                "query": query,
                                "results": [],
                                "count": 0,
                                "message": f"No images found for '{query}'. Try different keywords."
                            }
                        )
                    
                    results = []
                    for item in items:
                        image = item.get("image", {})
                        results.append({
                            "url": item.get("link", ""),
                            "title": item.get("title", ""),
                            "context_url": image.get("contextLink", ""),  # The webpage containing this image
                            "thumbnail": image.get("thumbnailLink", ""),
                            "width": image.get("width", 0),
                            "height": image.get("height", 0),
                            "size_bytes": image.get("byteSize", 0),
                            "mime_type": item.get("mime", ""),
                            "source": "google",
                        })
                    
                    return ToolResult(
                        success=True,
                        data={
                            "query": query,
                            "results": results,
                            "count": len(results),
                            "message": f"Found {len(results)} images for '{query}'"
                        }
                    )
                    
        except asyncio.TimeoutError:
            return ToolResult(success=False, error_message="Search timed out (15s)")
        except Exception as e:
            self._logger.error(f"Google image search failed: {e}")
            return ToolResult(success=False, error_message=f"Search failed: {e}")


class WebScreenshotTool(BaseTool):
    """Take a screenshot of a webpage for reference.
    
    Uses Playwright to capture live webpage screenshots that can be used
    as design references.
    """
    
    NAME = "web_screenshot"
    
    DESCRIPTION = """Take a screenshot of a live webpage for design reference.

Examples:
    web_screenshot "https://www.atlassian.com/software/jira"
    web_screenshot "https://github.com" "screenshots/github_home.png"
    web_screenshot "https://slack.com" "design/slack_ref.png" full_page=true

This captures the current state of a webpage, which is useful for:
- Getting up-to-date design references
- Capturing specific pages that aren't in screenshot library
- Creating comparison references

Requires Playwright to be installed.
"""
    
    def __init__(self, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace or Workspace(Path.cwd())
        self._logger = logging.getLogger(__name__)
    
    @property
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the webpage to screenshot"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination path (default: screenshots/<domain>.png)"
                    },
                    "full_page": {
                        "type": "boolean",
                        "description": "Capture full page or just viewport (default: false)"
                    },
                    "width": {
                        "type": "integer",
                        "description": "Viewport width (default: 1280)"
                    },
                    "height": {
                        "type": "integer",
                        "description": "Viewport height (default: 800)"
                    }
                },
                "required": ["url"]
            }
        )
    
    async def execute(
        self, 
        url: str, 
        destination: str = None,
        full_page: bool = False,
        width: int = 1280,
        height: int = 800
    ) -> ToolResult:
        """Take screenshot of a webpage"""
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return ToolResult(
                success=False,
                error_message="Playwright not installed. Run: pip install playwright && playwright install"
            )
        
        # Determine destination path
        if destination:
            dest_path = self.workspace.resolve(destination)
        else:
            # Extract domain for default filename
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")
            dest_path = self.workspace.root / "screenshots" / f"{domain}.png"
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": width, "height": height}
                )
                page = await context.new_page()
                
                # Navigate and wait for content
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Take screenshot
                await page.screenshot(
                    path=str(dest_path),
                    full_page=full_page
                )
                
                await browser.close()
                
                file_size = dest_path.stat().st_size
                size_display = f"{file_size / 1024:.1f}KB" if file_size < 1024*1024 else f"{file_size / 1024 / 1024:.1f}MB"
                
                return ToolResult(
                    success=True,
                    data={
                        "url": url,
                        "destination": str(dest_path.relative_to(self.workspace.root)),
                        "absolute_path": str(dest_path),
                        "size": size_display,
                        "dimensions": f"{width}x{height}" if not full_page else "full page",
                        "message": f"Screenshot saved: {dest_path.relative_to(self.workspace.root)} ({size_display})"
                    }
                )
                
        except Exception as e:
            self._logger.error(f"Screenshot failed: {e}")
            return ToolResult(success=False, error_message=f"Screenshot failed: {e}")


def create_image_search_tools(workspace: Workspace = None, google_api_key: str = None, google_cx: str = None) -> List[BaseTool]:
    """Create all image search tools"""
    return [
        SearchImageTool(workspace=workspace),
        DownloadImageTool(workspace=workspace),
        GoogleImageSearchTool(workspace=workspace, api_key=google_api_key, cx=google_cx),
        WebScreenshotTool(workspace=workspace),
    ]

