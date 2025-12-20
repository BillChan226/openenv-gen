"""
Vision Tools - Screenshot analysis and design extraction for web generation
Enables agent to build web pages based on reference images/screenshots
"""
import base64
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from utils.tool import BaseTool, ToolResult, ToolCategory, create_tool_param


@dataclass
class DesignAnalysis:
    """Extracted design information from a screenshot"""
    # Layout
    layout_type: str = ""  # grid, flex, sidebar, dashboard, etc.
    sections: List[Dict] = field(default_factory=list)  # [{name, position, description}]
    
    # Colors
    primary_color: str = ""
    secondary_color: str = ""
    background_color: str = ""
    text_color: str = ""
    accent_colors: List[str] = field(default_factory=list)
    
    # Typography
    heading_font: str = ""
    body_font: str = ""
    font_sizes: Dict[str, str] = field(default_factory=dict)
    
    # Components identified
    components: List[Dict] = field(default_factory=list)  # [{type, description, position}]
    
    # Overall style
    style_description: str = ""
    design_system: str = ""  # material, fluent, atlassian, custom, etc.
    
    # Raw LLM analysis
    raw_analysis: str = ""


def encode_image_to_base64(image_path: str) -> Optional[str]:
    """Encode image file to base64 string"""
    path = Path(image_path)
    if not path.exists():
        return None
    
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def get_image_mime_type(image_path: str) -> str:
    """Get MIME type from file extension"""
    ext = Path(image_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mime_map.get(ext, "image/png")


class AnalyzeScreenshotTool(BaseTool):
    """Analyze a screenshot to extract design information for web generation"""
    
    NAME = "analyze_screenshot"
    
    DESCRIPTION = """Analyze a screenshot/mockup image to extract design information.
Returns detailed analysis including:
- Layout structure (grid, flex, sections)
- Color palette (primary, secondary, background, accent)
- Typography (fonts, sizes)
- UI components identified (buttons, cards, navigation, etc.)
- Overall style and design system

Use this when you have a reference image to build a web page from.
"""
    
    def __init__(self, llm_client=None):
        super().__init__(name=self.NAME, category=ToolCategory.CODE)
        self._llm = llm_client
        self._logger = logging.getLogger(__name__)
    
    def set_llm(self, llm_client):
        """Set the LLM client (must support vision)"""
        self._llm = llm_client
    
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
                    "image_path": {
                        "type": "string",
                        "description": "Path to the screenshot/mockup image"
                    },
                    "focus_area": {
                        "type": "string",
                        "description": "Optional: specific area to focus on (e.g., 'header', 'sidebar', 'main content')"
                    }
                },
                "required": ["image_path"]
            }
        )
    
    async def execute(self, image_path: str, focus_area: str = None) -> ToolResult:
        if not self._llm:
            return ToolResult(
                success=False,
                error_message="LLM client not configured. Cannot analyze image."
            )
        
        # Encode image
        image_base64 = encode_image_to_base64(image_path)
        if not image_base64:
            return ToolResult(
                success=False,
                error_message=f"Could not read image: {image_path}"
            )
        
        mime_type = get_image_mime_type(image_path)
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(focus_area)
        
        try:
            # Call vision LLM
            response = await self._call_vision_llm(image_base64, mime_type, prompt)
            
            # Parse response into DesignAnalysis
            analysis = self._parse_analysis(response)
            
            return ToolResult(
                success=True,
                data={
                    "image_path": image_path,
                    "analysis": {
                        "layout_type": analysis.layout_type,
                        "sections": analysis.sections,
                        "colors": {
                            "primary": analysis.primary_color,
                            "secondary": analysis.secondary_color,
                            "background": analysis.background_color,
                            "text": analysis.text_color,
                            "accents": analysis.accent_colors,
                        },
                        "typography": {
                            "heading_font": analysis.heading_font,
                            "body_font": analysis.body_font,
                            "sizes": analysis.font_sizes,
                        },
                        "components": analysis.components,
                        "style_description": analysis.style_description,
                        "design_system": analysis.design_system,
                    },
                    "raw_analysis": analysis.raw_analysis,
                }
            )
        except Exception as e:
            self._logger.error(f"Screenshot analysis failed: {e}")
            return ToolResult(
                success=False,
                error_message=f"Analysis failed: {str(e)}"
            )
    
    def _build_analysis_prompt(self, focus_area: str = None) -> str:
        focus_instruction = ""
        if focus_area:
            focus_instruction = f"\nFocus especially on the {focus_area} area."
        
        return f"""Analyze this web page screenshot/mockup and extract detailed design information.
{focus_instruction}

Please provide a comprehensive analysis in the following JSON format:
{{
    "layout_type": "sidebar|dashboard|landing|blog|ecommerce|app|other",
    "sections": [
        {{"name": "header", "position": "top", "description": "Navigation bar with logo and menu"}},
        ...
    ],
    "colors": {{
        "primary": "#hex",
        "secondary": "#hex", 
        "background": "#hex",
        "text": "#hex",
        "accents": ["#hex", ...]
    }},
    "typography": {{
        "heading_font": "font-family suggestion",
        "body_font": "font-family suggestion",
        "sizes": {{"h1": "size", "h2": "size", "body": "size"}}
    }},
    "components": [
        {{"type": "navbar|sidebar|card|button|form|table|modal|...", 
          "description": "detailed description",
          "position": "where in the layout",
          "styling": "notable styling details"}}
    ],
    "style_description": "Overall visual style description",
    "design_system": "material|fluent|atlassian|bootstrap|tailwind|custom"
}}

Be specific about colors (use hex codes), positions, and component details.
This information will be used to recreate the design in code."""
    
    async def _call_vision_llm(self, image_base64: str, mime_type: str, prompt: str) -> str:
        """Call the vision-capable LLM with the image"""
        
        # Build message with image
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}",
                            "detail": "high"  # high detail for better analysis
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
        
        # Call LLM (assuming litellm-compatible interface)
        response = await self._llm.chat_with_response(
            messages=messages,
            temperature=0.3,  # Lower for more consistent analysis
        )
        
        return response.content if hasattr(response, 'content') else str(response)
    
    def _parse_analysis(self, response: str) -> DesignAnalysis:
        """Parse LLM response into DesignAnalysis object"""
        import json
        import re
        
        analysis = DesignAnalysis(raw_analysis=response)
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                
                analysis.layout_type = data.get("layout_type", "")
                analysis.sections = data.get("sections", [])
                
                colors = data.get("colors", {})
                analysis.primary_color = colors.get("primary", "")
                analysis.secondary_color = colors.get("secondary", "")
                analysis.background_color = colors.get("background", "")
                analysis.text_color = colors.get("text", "")
                analysis.accent_colors = colors.get("accents", [])
                
                typography = data.get("typography", {})
                analysis.heading_font = typography.get("heading_font", "")
                analysis.body_font = typography.get("body_font", "")
                analysis.font_sizes = typography.get("sizes", {})
                
                analysis.components = data.get("components", [])
                analysis.style_description = data.get("style_description", "")
                analysis.design_system = data.get("design_system", "")
                
            except json.JSONDecodeError:
                pass
        
        return analysis


class CompareWithScreenshotTool(BaseTool):
    """Compare generated UI with reference screenshot"""
    
    NAME = "compare_with_screenshot"
    
    DESCRIPTION = """Compare a generated web page screenshot with the reference design.
Returns similarity analysis and specific differences to fix.
Use this after generating UI code to verify it matches the reference.
"""
    
    def __init__(self, llm_client=None):
        super().__init__(name=self.NAME, category=ToolCategory.CODE)
        self._llm = llm_client
        self._logger = logging.getLogger(__name__)
    
    def set_llm(self, llm_client):
        self._llm = llm_client
    
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
                    "reference_image": {
                        "type": "string",
                        "description": "Path to the reference screenshot"
                    },
                    "generated_image": {
                        "type": "string",
                        "description": "Path to screenshot of generated UI"
                    }
                },
                "required": ["reference_image", "generated_image"]
            }
        )
    
    async def execute(self, reference_image: str, generated_image: str) -> ToolResult:
        if not self._llm:
            return ToolResult(success=False, error_message="LLM client not configured")
        
        ref_base64 = encode_image_to_base64(reference_image)
        gen_base64 = encode_image_to_base64(generated_image)
        
        if not ref_base64:
            return ToolResult(success=False, error_message=f"Cannot read reference: {reference_image}")
        if not gen_base64:
            return ToolResult(success=False, error_message=f"Cannot read generated: {generated_image}")
        
        ref_mime = get_image_mime_type(reference_image)
        gen_mime = get_image_mime_type(generated_image)
        
        prompt = """Compare these two web page screenshots:
- Image 1: Reference design (what we want)
- Image 2: Generated output (what we have)

Analyze the differences and provide:
1. Overall similarity score (0-100)
2. Layout differences
3. Color differences  
4. Component differences
5. Specific fixes needed

Respond in JSON:
{
    "similarity_score": 0-100,
    "layout_matches": true/false,
    "color_matches": true/false,
    "differences": [
        {"area": "header", "issue": "description", "fix": "how to fix"}
    ],
    "priority_fixes": ["most important fix first", ...]
}"""
        
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Reference design:"},
                        {"type": "image_url", "image_url": {"url": f"data:{ref_mime};base64,{ref_base64}"}},
                        {"type": "text", "text": "Generated output:"},
                        {"type": "image_url", "image_url": {"url": f"data:{gen_mime};base64,{gen_base64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            response = await self._llm.chat_with_response(messages=messages, temperature=0.3)
            content = response.content if hasattr(response, 'content') else str(response)
            
            import json
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return ToolResult(success=True, data=data)
            
            return ToolResult(success=True, data={"raw_comparison": content})
            
        except Exception as e:
            return ToolResult(success=False, error_message=f"Comparison failed: {e}")


class ExtractComponentsTool(BaseTool):
    """Extract specific UI components from a screenshot for targeted generation"""
    
    NAME = "extract_components"
    
    DESCRIPTION = """Extract specific UI components from a screenshot.
Use this to get detailed specs for individual components like:
- Navigation bars
- Cards
- Forms
- Buttons
- Modals
- Tables
- Sidebars
"""
    
    def __init__(self, llm_client=None):
        super().__init__(name=self.NAME, category=ToolCategory.CODE)
        self._llm = llm_client
    
    def set_llm(self, llm_client):
        self._llm = llm_client
    
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
                    "image_path": {
                        "type": "string",
                        "description": "Path to the screenshot"
                    },
                    "component_type": {
                        "type": "string",
                        "description": "Type of component to extract (navbar, card, form, button, etc.)"
                    }
                },
                "required": ["image_path", "component_type"]
            }
        )
    
    async def execute(self, image_path: str, component_type: str) -> ToolResult:
        if not self._llm:
            return ToolResult(success=False, error_message="LLM client not configured")
        
        image_base64 = encode_image_to_base64(image_path)
        if not image_base64:
            return ToolResult(success=False, error_message=f"Cannot read image: {image_path}")
        
        mime_type = get_image_mime_type(image_path)
        
        prompt = f"""Analyze this screenshot and extract detailed specifications for the {component_type} component(s).

For each {component_type} found, provide:
{{
    "components": [
        {{
            "type": "{component_type}",
            "position": "where in the page",
            "dimensions": {{"width": "...", "height": "..."}},
            "colors": {{"background": "#hex", "text": "#hex", "border": "#hex"}},
            "typography": {{"font": "...", "size": "...", "weight": "..."}},
            "spacing": {{"padding": "...", "margin": "..."}},
            "children": ["list of child elements"],
            "interactions": ["hover states", "click behavior"],
            "css_suggestions": "suggested CSS/Tailwind classes",
            "react_structure": "suggested React component structure"
        }}
    ]
}}

Be very specific - this will be used to generate actual code."""
        
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            response = await self._llm.chat_with_response(messages=messages, temperature=0.3)
            content = response.content if hasattr(response, 'content') else str(response)
            
            import json
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return ToolResult(success=True, data=data)
            
            return ToolResult(success=True, data={"raw_extraction": content})
            
        except Exception as e:
            return ToolResult(success=False, error_message=f"Extraction failed: {e}")


def create_vision_tools(llm_client=None) -> List[BaseTool]:
    """Create all vision tools with optional LLM client"""
    tools = [
        AnalyzeScreenshotTool(llm_client),
        CompareWithScreenshotTool(llm_client),
        ExtractComponentsTool(llm_client),
    ]
    return tools

