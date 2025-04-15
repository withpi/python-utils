"""question_builders provides a set of tools for building Questions"""

import contextlib
import inspect
import io
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from pathlib import Path

from withpi.types import Question


def _test_python_subprocess(python_code: str, conn: Connection):
    """Test Python code to catch various signature errors for a PythonSubDimension.
    This should run in a separate process."""
    try:
        exec(python_code)
        # This should have brought a score() method into the environment.
        if "score" not in locals():
            raise ValueError("Python code did not define a score() method!")
        signature = inspect.signature(locals()["score"])
        if "response_text" not in signature.parameters:
            raise ValueError(
                "score() method does not accept a response_text parameter!"
            )
        if "input_text" not in signature.parameters:
            raise ValueError("score() method does not accept an input_text parameter!")
        if (
            "kwargs" not in signature.parameters
            or signature.parameters["kwargs"].kind != inspect.Parameter.VAR_KEYWORD
        ):
            raise ValueError("score() method does not accept a **kwargs parameter!")
        with io.StringIO() as buf, contextlib.redirect_stdout(buf):
            response = locals()["score"]("LLM Response", "LLM Input")
            if buf.getvalue():
                raise ValueError("score() printed to stdout, which is not allowed!")
        if not isinstance(response, dict):
            raise ValueError("score() did not return a dictionary!")
        if "score" not in response or not isinstance(response["score"], float):
            raise ValueError(
                "score() did not return a dictionary with a 'score' key of float type!"
            )
        if response["score"] < 0 or response["score"] > 1:
            raise ValueError("score() returned a score outside the range [0, 1]!")
        if "explanation" not in response or not isinstance(
            response["explanation"], str
        ):
            raise ValueError(
                "score() did not return a dictionary with an 'explanation' key of str type!"
            )
        conn.send(None)
        conn.close()
    except Exception as e:
        conn.send(e)
        conn.close()
        raise e


class PiQuestionBuilder:
    @classmethod
    def from_question(cls, question: str) -> Question:
        """Create a Pi question from a string"""
        return Question(question=question)


class PythonQuestionBuilder:
    @classmethod
    def from_python_file(cls, question: str, python_file: Path) -> Question:
        """Create a Python question from a Python file"""
        with open(python_file, "r") as f:
            python_code = f.read()
        return cls._validate(question, python_code)

    @classmethod
    def from_python_string(cls, question: str, python_code: str) -> Question:
        """Create a Python question from a Python string"""
        return cls._validate(question, python_code)

    @classmethod
    def _validate(cls, question: str, python_code) -> Question:
        """Validate the Python code, raising on error"""
        parent_conn, child_conn = Pipe()
        process = Process(
            target=_test_python_subprocess, args=[python_code, child_conn]
        )
        process.start()
        response = parent_conn.recv()
        process.join()
        if process.exitcode != 0:
            raise response
        return Question(
            question=question, python_code=python_code, scoring_type="PYTHON_CODE"
        )
