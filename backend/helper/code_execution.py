import subprocess
import tempfile
import os
from typing import Optional
from dataclasses import dataclass
import json
from enum import Enum
import logging
from helper_functions import use_claude
import re
class ExecutionStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"

@dataclass
class ExecutionResult:
    status: ExecutionStatus
    output: str
    error: Optional[str] = None
    execution_time: float = 0.0

class CodeExecutor:
    def __init__(self, timeout_seconds: int = 5, max_output_size: int = 1024 * 1024):
        self.timeout = timeout_seconds
        self.max_output_size = max_output_size
        self.logger = logging.getLogger(__name__)

    def _create_temp_file(self, code: str) -> str:
        """Creates a temporary file with the provided code."""
        temp = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        temp.write(code)
        temp.close()
        return temp.name

    def _clean_up(self, filepath: str):
        """Safely removes the temporary file."""
        try:
            os.unlink(filepath)
        except Exception as e:
            self.logger.error(f"Error cleaning up temporary file: {e}")

    def execute_code(self, code: str) -> ExecutionResult:
        """
        Executes the provided Python code in a subprocess with safety constraints.
        """
        temp_file = self._create_temp_file(code)
        
        try:
            # Run the code in a subprocess with timeout
            process = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            # Check output size
            if len(process.stdout) > self.max_output_size:
                return ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    output="Output exceeded maximum allowed size",
                    error="Output too large"
                )

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=process.stdout,
                error=process.stderr if process.stderr else None,
                execution_time=process.returncode
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                output="",
                error=f"Execution timed out after {self.timeout} seconds"
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                output="",
                error=str(e)
            )
        finally:
            self._clean_up(temp_file)


def generate_and_execute(task):
    # Mock LLM client for demonstration
    
    # Initialize the system
    executor = CodeExecutor(timeout_seconds=5)
   
    
    prompt = f"""
    You are an expert python programmer. You are tasked with writing python code to complete the following task:
    {task}

    Please write the code in a way that is clean, readable, and efficient.
    Please write the code in a way that is easy to understand, and easy to modify if needed.

    Output your final python code within the code block tags, as follows:
    <code>
    {"""Your python code here"""}
    </code>
    """
    # Example prompt
    code_generation_result = use_claude(prompt)
    print(code_generation_result);
    # Extract code between <code> tags using regex
    code_match = re.search(r'<code>(.*?)</code>', code_generation_result, re.DOTALL)
    if not code_match:
        return ExecutionResult(
            status=ExecutionStatus.ERROR,
            output="",
            error="No code block found in response"
        )
    generated_code = code_match.group(1)
    result = executor.execute_code(generated_code)
    print(result.output);
    return result.output;

if __name__ == "__main__":
    example_usage()