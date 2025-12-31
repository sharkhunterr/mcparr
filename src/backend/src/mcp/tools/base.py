"""Base classes for MCP tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    description: str
    type: str  # "string", "number", "boolean", "array", "object"
    required: bool = True
    enum: Optional[List[str]] = None
    default: Any = None


@dataclass
class ToolDefinition:
    """Complete definition of an MCP tool."""

    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    category: str = "general"
    is_mutation: bool = False  # True if the tool modifies data
    requires_service: Optional[str] = None  # Service type required

    def to_mcp_schema(self) -> dict:
        """Convert to MCP-compatible JSON schema."""
        properties = {}
        required = []

        for param in self.parameters:
            prop: Dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class BaseTool(ABC):
    """Base class for MCP tool implementations."""

    def __init__(self, service_config: Optional[dict] = None):
        """Initialize tool with optional service configuration."""
        self.service_config = service_config or {}

    @property
    @abstractmethod
    def definitions(self) -> List[ToolDefinition]:
        """Return list of tool definitions provided by this class."""
        pass

    @abstractmethod
    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool with given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Dict with 'success' bool and 'result' or 'error' key
        """
        pass

    def get_tool_names(self) -> List[str]:
        """Get list of tool names provided by this class."""
        return [d.name for d in self.definitions]

    def get_tool_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get definition for a specific tool."""
        for definition in self.definitions:
            if definition.name == name:
                return definition
        return None


class ToolRegistry:
    """Registry for MCP tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._definitions: Dict[str, ToolDefinition] = {}

    def register(self, tool_class: Type[BaseTool], service_config: Optional[dict] = None) -> None:
        """Register a tool class with the registry."""
        tool_instance = tool_class(service_config)
        for definition in tool_instance.definitions:
            self._tools[definition.name] = tool_instance
            self._definitions[definition.name] = definition

    @property
    def tools(self) -> Dict[str, ToolDefinition]:
        """Get all registered tool definitions."""
        return self._definitions

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get tool instance by name."""
        return self._tools.get(name)

    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name."""
        return self._definitions.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tool definitions."""
        return list(self._definitions.values())

    def list_tools_mcp_schema(self) -> List[dict]:
        """List all tools in MCP schema format."""
        return [d.to_mcp_schema() for d in self._definitions.values()]

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool by name with arguments."""
        tool = self.get_tool(tool_name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        try:
            result = await tool.execute(tool_name, arguments)
            return result
        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
