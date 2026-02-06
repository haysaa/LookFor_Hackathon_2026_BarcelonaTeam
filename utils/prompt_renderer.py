"""
Prompt Template Renderer
Version: 1.0
Developer: Dev B

Renders prompt templates with variables using Jinja2.
"""
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template


class PromptRenderer:
    """
    Renders prompt templates from the prompts/ directory.
    
    Usage:
        renderer = PromptRenderer()
        prompt = renderer.render("triage_agent_v1", {
            "customer_message": "Where is my order #12345?",
            "customer_context": "VIP customer"
        })
    """
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize with prompts directory path."""
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent.parent / "prompts"
        
        self.prompts_dir = prompts_dir
        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            autoescape=False  # Plain text prompts
        )
        self._template_cache: Dict[str, Template] = {}
    
    def get_template(self, template_name: str) -> Template:
        """
        Get a template by name (without .txt extension).
        
        Args:
            template_name: Template name, e.g., "triage_agent_v1"
        
        Returns:
            Jinja2 Template object
        """
        if template_name not in self._template_cache:
            filename = f"{template_name}.txt"
            self._template_cache[template_name] = self.env.get_template(filename)
        return self._template_cache[template_name]
    
    def render(self, template_name: str, variables: Dict[str, Any]) -> str:
        """
        Render a prompt template with given variables.
        
        Args:
            template_name: Template name (e.g., "triage_agent_v1")
            variables: Dict of variables to substitute
        
        Returns:
            Rendered prompt string
        """
        template = self.get_template(template_name)
        return template.render(**variables)
    
    def list_templates(self) -> list[str]:
        """List all available template names."""
        return [
            f.stem for f in self.prompts_dir.glob("*.txt")
            if f.is_file()
        ]


# Convenience function for quick rendering
def render_prompt(template_name: str, variables: Dict[str, Any]) -> str:
    """
    Quick render function without instantiating renderer.
    
    Args:
        template_name: Template name
        variables: Variables to substitute
    
    Returns:
        Rendered prompt
    """
    renderer = PromptRenderer()
    return renderer.render(template_name, variables)
