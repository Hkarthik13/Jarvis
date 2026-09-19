from abc import ABC, abstractmethod
from typing import Any, Dict, List
from backend.utils.logger import logger

class BaseTool(ABC):
    """
    Abstract Base Class for all JARVIS tools.
    Every tool must define its name, description, schema, validation, and execution.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool (must match Groq function calling syntax)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of the tool to help the LLM decide when to call it."""
        pass

    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """Groq/OpenAI compatible JSON schema describing tool inputs."""
        pass

    @abstractmethod
    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and sanitizes tool arguments.
        Raises ValueError if arguments are invalid or dangerous.
        """
        pass

    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> Any:
        """
        Executes the tool's core logic with validated arguments.
        """
        pass


class ToolRegistry:
    """
    Central registry for managing, validating, and executing JARVIS tools.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a tool with the registry."""
        if tool.name in self._tools:
            logger.warning(f"Overwriting already registered tool: {tool.name}")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: '{tool.name}'")

    def get_tool(self, name: str) -> BaseTool:
        """Retrieves a tool by name."""
        return self._tools.get(name)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns the list of tool schemas for LLM injection."""
        return [tool.schema for tool in self._tools.values()]

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """
        Orchestrates tool execution: lookup, validation, execution, and logging.
        Returns a string representation of the result or error.
        """
        tool = self.get_tool(name)
        if not tool:
            err_msg = f"Error: Tool '{name}' is not registered."
            logger.error(err_msg)
            return err_msg
            
        logger.info(f"Registry: Executing tool '{name}' with arguments: {args}")
        try:
            # 1. Validate
            validated_args = tool.validate_args(args)
            logger.debug(f"Registry: Validation successful for '{name}' parameters.")
            
            # 2. Execute
            result = tool.execute(validated_args)
            logger.info(f"Registry: Tool '{name}' executed successfully.")
            return str(result)
            
        except ValueError as ve:
            validation_err = f"Validation Error in tool '{name}': {str(ve)}"
            logger.warning(validation_err)
            return validation_err
        except Exception as e:
            execution_err = f"Execution Error in tool '{name}': {str(e)}"
            logger.error(execution_err)
            return execution_err

# Global singleton registry instance
registry = ToolRegistry()
