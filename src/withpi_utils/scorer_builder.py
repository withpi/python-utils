"""scoring_spec_builder provides a set of tools for inspecting and modifying ScoringSpec objects"""

import contextlib
import inspect
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from pathlib import Path

from withpi.types import ScoringSpec, ScoringDimension, ScoringSubDimension


class SubdimensionType(Enum):
    PI_SCORER = auto()
    PYTHON_CODE = auto()


@dataclass
class SubDimensionBuilder(ABC):
    """SubDimensionBuilder is a leaf of a ScoringSpec tree.

    Instantiate one of the concrete subclasses and add them to the tree at the Dimension level with
    add_subdimension()."""

    label: str

    @abstractmethod
    def _build(self) -> ScoringSubDimension: ...

    @classmethod
    @abstractmethod
    def _from_sub_dimension(
        cls, sub_dimension: ScoringSubDimension
    ) -> "SubDimensionBuilder":
        if sub_dimension.scoring_type == "PI_SCORER":
            return PiSubDimension._from_sub_dimension(sub_dimension)
        elif sub_dimension.scoring_type == "PYTHON_CODE":
            return PythonSubDimension._from_sub_dimension(sub_dimension)
        raise ValueError(f"Unknown scoring type: {sub_dimension.scoring_type}")


@dataclass
class PiSubDimension(SubDimensionBuilder):
    """PiSubDimension is a SubDimension that uses Pi to answer an objective question."""

    question: str
    weight: float = 1.0
    scaling_parameters: list[float] = field(default_factory=list)

    @classmethod
    def _from_sub_dimension(
        cls, sub_dimension: ScoringSubDimension
    ) -> "PiSubDimension":
        return cls(
            label=sub_dimension.label,
            weight=sub_dimension.weight if sub_dimension.weight else 1.0,
            scaling_parameters=(
                sub_dimension.parameters if sub_dimension.parameters else []
            ),
            question=sub_dimension.description,
        )

    def _build(self) -> ScoringSubDimension:
        return ScoringSubDimension(
            description=self.question,
            label=self.label,
            scoring_type="PI_SCORER",
            weight=self.weight,
            parameters=self.scaling_parameters,
        )


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


@dataclass
class PythonSubDimension(SubDimensionBuilder):
    """PythonSubDimension uses Python to evaluate an aspect of the response.

    Supplied snippets must define a score() function that takes a response_text, an input_text, and **kwargs.
    The function should return a dictionary with a 'score' key (float) and an 'explanation' key (str).
    """

    python_code: str
    weight: float = 1.0
    scaling_parameters: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validate()

    @classmethod
    def from_python_file(
        cls,
        label: str,
        weight: float,
        scaling_parameters: list[float],
        python_file: Path,
    ) -> "PythonSubDimension":
        """Create a PythonSubDimension from a Python file"""
        with open(python_file, "r") as f:
            python_code = f.read()
        return cls(
            label=label,
            weight=weight,
            scaling_parameters=scaling_parameters,
            python_code=python_code,
        )

    @classmethod
    def _from_sub_dimension(
        cls, sub_dimension: ScoringSubDimension
    ) -> "PythonSubDimension":
        return cls(
            label=sub_dimension.label,
            weight=sub_dimension.weight if sub_dimension.weight else 1.0,
            scaling_parameters=(
                sub_dimension.parameters if sub_dimension.parameters else []
            ),
            python_code=sub_dimension.python_code if sub_dimension.python_code else "",
        )

    def _build(self) -> ScoringSubDimension:
        return ScoringSubDimension(
            description="Python Code",
            label=self.label,
            scoring_type="PYTHON_CODE",
            weight=self.weight,
            parameters=self.scaling_parameters,
            python_code=self.python_code,
        )

    def _validate(self) -> None:
        """Validate the Python code, raising on error"""
        parent_conn, child_conn = Pipe()
        process = Process(
            target=_test_python_subprocess, args=[self.python_code, child_conn]
        )
        process.start()
        response = parent_conn.recv()
        process.join()
        if process.exitcode != 0:
            raise response


@dataclass
class DimensionBuilder:
    """DimensionBuilder wraps a Dimension.

    Add this to a ScoringSpecBuilder to add a Dimension to the ScoringSpec."""

    label: str
    weight: float = 1.0
    scaling_parameters: list[float] = field(default_factory=list)
    _sub_dimensions: list[SubDimensionBuilder] = field(default_factory=list, init=False)

    @property
    def sub_dimensions(self) -> list[SubDimensionBuilder]:
        return self._sub_dimensions.copy()

    def add_subdimension(
        self, sub_dimension: SubDimensionBuilder
    ) -> SubDimensionBuilder:
        self._sub_dimensions.append(sub_dimension)
        return sub_dimension

    def remove_sub_dimension(self, sub_dimension: SubDimensionBuilder) -> None:
        self._sub_dimensions.remove(sub_dimension)

    @classmethod
    def _from_dimension(cls, dimension: ScoringDimension) -> "DimensionBuilder":
        self = cls(label=dimension.label)
        self.weight = dimension.weight if dimension.weight else 1.0
        self.scaling_parameters = dimension.parameters if dimension.parameters else []
        self._sub_dimensions = []
        for sub_dimension in dimension.sub_dimensions:
            self._sub_dimensions.append(
                SubDimensionBuilder._from_sub_dimension(sub_dimension)
            )
        return self

    def _build(self) -> ScoringDimension:
        return ScoringDimension(
            description="unused",
            label=self.label,
            weight=self.weight,
            parameters=self.scaling_parameters,
            sub_dimensions=[s._build() for s in self._sub_dimensions],
        )


class ScoringSpecBuilder:
    """ScoringSpecBuilder provides a read-write interface to a ScoringSpec tree.

    Instantiate with the from_x() class methods, depending on what you have,
    call methods to modify the object, and call build() to get a new ScoringSpec object.

    This is a more ergonomic interface for manually manipulating ScoringSpecs at the JSON level,
    with more type checking and convenience methods."""

    name: str
    description: str
    _dimensions: list[DimensionBuilder]

    def build(self) -> ScoringSpec:
        return ScoringSpec(
            description=self.description,
            name=self.name,
            dimensions=[g._build() for g in self._dimensions],
        )

    @property
    def dimensions(self) -> list[DimensionBuilder]:
        return self._dimensions.copy()

    def add_dimension(
        self, label_or_builder: str | DimensionBuilder
    ) -> DimensionBuilder:
        if isinstance(label_or_builder, str):
            label = label_or_builder
            builder = DimensionBuilder(label=label)
        else:
            builder = label_or_builder
        self._dimensions.append(builder)
        return builder

    def remove_dimension(self, dimension: DimensionBuilder) -> None:
        self._dimensions.remove(dimension)

    def print_scoring_spec(self, file=None) -> None:
        """print_scoring_spec pretty-prints the wrapped ScoringSpec."""
        for dimension in self.dimensions:
            print(dimension.label, file=file)
            for sub_dimension in dimension.sub_dimensions:
                print(f"\t{sub_dimension.label}", file=file)

    def __init__(self):
        self._groups = []

    @classmethod
    def from_dict(cls, d: dict) -> "ScoringSpecBuilder":
        return cls.from_scoring_spec(ScoringSpec.model_validate(d))

    @classmethod
    def from_json(cls, json: str | bytes | bytearray) -> "ScoringSpecBuilder":
        """Create a ScoringSystemBuilder from a JSON string"""
        return cls.from_scoring_spec(ScoringSpec.model_validate_json(json))

    @classmethod
    def from_scoring_spec(cls, scoring_spec: ScoringSpec) -> "ScoringSpecBuilder":
        self = cls()
        self.name = scoring_spec.name
        self.description = scoring_spec.description
        self._dimensions = []
        if scoring_spec.dimensions is None:
            return self
        for dimension in scoring_spec.dimensions:
            self._dimensions.append(DimensionBuilder._from_dimension(dimension))

        return self
