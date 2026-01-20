"""
Executor Agent - Executes tasks using available tools.
Implements Tool Use and Exception Handling patterns.
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional

from ..core.tool_registry import ToolRegistry
from ..models import ExecutionResult, Task, TaskStatus
from .base_agent import BaseAgent


class ExecutorAgent(BaseAgent):
    """Agent that executes tasks using available tools."""

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        """
        Initialize the executor agent.

        Args:
            tool_registry: Tool registry instance
        """
        super().__init__(model_name="gpt-4", temperature=0.1)
        self.tool_registry = tool_registry or ToolRegistry()

    def execute_task(self, task: Task) -> ExecutionResult:
        """
        Execute a task using the appropriate tool.

        Args:
            task: Task to execute

        Returns:
            ExecutionResult with outcome details
        """
        self.log(f"Executing task: {task.description}")

        start_time = time.time()
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()

        try:
            # Determine which tool and operation to use
            if not task.tool:
                # Try to infer tool from task description
                task.tool = self._infer_tool(task.description)

            if not task.tool:
                return ExecutionResult(
                    task_id=task.id,
                    success=False,
                    error="No tool specified and could not infer tool from task description",
                    execution_time=time.time() - start_time,
                )

            # Execute the tool operation
            result = self._execute_tool_operation(task)

            execution_time = time.time() - start_time

            if result["success"]:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = result

                return ExecutionResult(
                    task_id=task.id,
                    success=True,
                    output=str(
                        result.get("message", result.get("content", "Task completed"))
                    ),
                    execution_time=execution_time,
                    metadata=result,
                )
            else:
                # Check if we should retry
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    self.log(
                        f"Task failed, retrying ({task.retry_count}/{task.max_retries})"
                    )
                    time.sleep(1)  # Brief delay before retry
                    return self.execute_task(task)

                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                task.error = result.get("error", "Unknown error")

                return ExecutionResult(
                    task_id=task.id,
                    success=False,
                    error=result.get("error", "Task execution failed"),
                    execution_time=execution_time,
                    metadata=result,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()

            self.log(f"Exception during task execution: {str(e)}", "ERROR")

            return ExecutionResult(
                task_id=task.id,
                success=False,
                error=str(e),
                execution_time=execution_time,
            )

    def _infer_tool(self, task_description: str) -> Optional[str]:
        """
        Infer which tool to use from task description.

        Args:
            task_description: Description of the task

        Returns:
            Tool name or None
        """
        description_lower = task_description.lower()

        # Simple keyword-based inference
        if any(
            keyword in description_lower
            for keyword in ["file", "create file", "read file", "write", "directory"]
        ):
            return "file_operations"
        elif any(
            keyword in description_lower
            for keyword in ["git", "commit", "branch", "repository"]
        ):
            return "git_operations"
        elif any(
            keyword in description_lower
            for keyword in ["download", "fetch", "request", "http", "url"]
        ):
            return "web_operations"
        elif any(
            keyword in description_lower
            for keyword in ["run", "execute", "command", "install", "python", "npm"]
        ):
            return "command_executor"

        return None

    def _execute_tool_operation(self, task: Task) -> Dict[str, Any]:
        """
        Execute a tool operation for a task.

        Args:
            task: Task with tool and tool_params

        Returns:
            Result dictionary
        """
        if not task.tool:
            return {"success": False, "error": "No tool specified"}

        # Parse tool and operation from task
        # Format: "tool_name" or "tool_name.operation"
        tool_name = task.tool
        operation = None

        if "." in tool_name:
            tool_name, operation = tool_name.split(".", 1)

        # Get tool params
        params = task.tool_params.copy()

        # If operation is in params, use it
        if "operation" in params:
            operation = params.pop("operation")

        # Default operations for each tool
        if not operation:
            operation = self._get_default_operation(tool_name, task.description)

        if not operation:
            return {
                "success": False,
                "error": f"Could not determine operation for tool '{tool_name}'",
            }

        # Execute using tool registry
        return self.tool_registry.execute_tool(tool_name, operation, **params)

    def _get_default_operation(
        self, tool_name: str, task_description: str
    ) -> Optional[str]:
        """
        Get default operation for a tool based on task description.

        Args:
            tool_name: Name of the tool
            task_description: Description of the task

        Returns:
            Operation name or None
        """
        description_lower = task_description.lower()

        if tool_name == "file_operations":
            if "create" in description_lower or "write" in description_lower:
                return "create_file"
            elif "read" in description_lower:
                return "read_file"
            elif "directory" in description_lower or "folder" in description_lower:
                return "create_directory"
            elif "list" in description_lower:
                return "list_directory"
            elif "delete" in description_lower:
                return "delete_file"

        elif tool_name == "git_operations":
            if "init" in description_lower or "initialize" in description_lower:
                return "initialize_repo"
            elif "branch" in description_lower:
                return "create_branch"
            elif "commit" in description_lower:
                return "commit"
            elif "status" in description_lower:
                return "get_status"

        elif tool_name == "web_operations":
            if "download" in description_lower:
                return "download_file"
            elif "get" in description_lower or "fetch" in description_lower:
                return "get"
            elif "post" in description_lower:
                return "post"

        elif tool_name == "command_executor":
            return "execute_safe"

        return None
