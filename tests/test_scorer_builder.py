import io

import pytest
from withpi.types import ScoringSpec, ScoringDimension, ScoringSubDimension

from withpi_utils import (
    PiSubDimension,
    PythonSubDimension,
    ScoringSpecBuilder,
    DimensionBuilder,
)


@pytest.fixture
def scoring_spec_builder(scoring_spec):
    return ScoringSpecBuilder.from_scoring_spec(scoring_spec)


@pytest.fixture
def scoring_spec():
    return ScoringSpec(
        name="Test",
        description="Test",
        dimensions=[
            ScoringDimension(
                description="unused",
                label="FirstLabel",
                parameters=[],
                weight=1.0,
                sub_dimensions=[
                    ScoringSubDimension(
                        description="Is it good?",
                        label="Pi Scorer",
                        scoring_type="PI_SCORER",
                        parameters=[],
                        weight=1.0,
                    ),
                    ScoringSubDimension(
                        description="Python Code",
                        python_code="score = lambda response_text, input_text, **kwargs: { 'score': 1.0, 'explanation': 'good' }",
                        label="Python Scorer",
                        scoring_type="PYTHON_CODE",
                        parameters=[],
                        weight=1.0,
                    ),
                ],
            )
        ],
    )


def test_add_dimension(scoring_spec_builder):
    scoring_spec_builder.add_dimension("test")
    assert [g.label for g in scoring_spec_builder.dimensions] == ["FirstLabel", "test"]


def test_add_dimension_builder(scoring_spec_builder):
    scoring_spec_builder.add_dimension(DimensionBuilder(label="test"))
    assert [g.label for g in scoring_spec_builder.dimensions] == ["FirstLabel", "test"]


def test_remove_dimension(scoring_spec_builder):
    scoring_spec_builder.remove_dimension(scoring_spec_builder.dimensions[0])
    assert len(scoring_spec_builder.dimensions) == 0


def test_print_scoring_spec(scoring_spec_builder):
    buf = io.StringIO()
    scoring_spec_builder.print_scoring_spec(buf)
    assert buf.getvalue() == "FirstLabel\n\tPi Scorer\n\tPython Scorer\n"


def test_add_pi_sub_dimension(scoring_spec_builder):
    dimension = scoring_spec_builder.dimensions[0]
    dimension.add_subdimension(
        PiSubDimension(
            label="test",
            question="Is it still good?",
        )
    )
    assert [s.label for s in dimension.sub_dimensions] == [
        "Pi Scorer",
        "Python Scorer",
        "test",
    ]


def test_add_python_sub_dimension(scoring_spec_builder):
    dimension = scoring_spec_builder.dimensions[0]
    dimension.add_subdimension(
        PythonSubDimension(
            label="test",
            python_code="score = lambda response_text, input_text, **kwargs: { 'score': 1.0, 'explanation': 'good' }",
        )
    )
    assert [s.label for s in dimension.sub_dimensions] == [
        "Pi Scorer",
        "Python Scorer",
        "test",
    ]


def test_remove_sub_dimension(scoring_spec_builder):
    dimension = scoring_spec_builder.dimensions[0]
    dimension.remove_sub_dimension(dimension.sub_dimensions[0])
    assert [s.label for s in dimension.sub_dimensions] == ["Python Scorer"]


def test_build_scoring_spec(scoring_spec_builder, scoring_spec):
    built_scoring_spec = scoring_spec_builder.build()
    assert built_scoring_spec.model_dump_json(indent=2) == scoring_spec.model_dump_json(
        indent=2
    )


def test_python_validator_not_python():
    with pytest.raises(SyntaxError):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="junk(",
        )


def test_python_validator_no_score():
    with pytest.raises(ValueError, match=r"did not define a score\(\) method"):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="print('hello world')",
        )


def test_python_validator_not_a_function():
    with pytest.raises(TypeError, match=r"is not a callable object"):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="score = 10",
        )


def test_python_validator_wrong_arguments():
    with pytest.raises(ValueError, match=r"does not accept a response_text parameter"):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="score = lambda x: x",
        )


def test_python_validator_missing_input_text():
    with pytest.raises(ValueError, match=r"does not accept an input_text parameter"):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="score = lambda response_text: response_text",
        )


def test_python_validator_kwargs_faked():
    with pytest.raises(ValueError, match=r"does not accept a \*\*kwargs parameter"):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="def score(response_text, input_text, kwargs):...",
        )


def test_python_validator_no_dict_return():
    with pytest.raises(ValueError, match=r"did not return a dictionary"):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="""def score(response_text, input_text, **kwargs):
        return 1.0""",
        )


def test_python_validator_bad_score():
    with pytest.raises(
        ValueError,
        match=r"did not return a dictionary with a 'score' key of float type",
    ):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="""def score(response_text, input_text, **kwargs):
        return { 'score': 'bad' }""",
        )


def test_python_validator_bad_score_range():
    with pytest.raises(
        ValueError,
        match=r"returned a score outside the range \[0, 1\]",
    ):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="""def score(response_text, input_text, **kwargs):
        return { 'score': 2.0 }""",
        )


def test_python_validator_no_explanation():
    with pytest.raises(
        ValueError,
        match=r"with an 'explanation' key of str type",
    ):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="""def score(response_text, input_text, **kwargs):
            return { 'score': 1.0 }""",
        )


def test_python_validator_prints_to_stdout():
    with pytest.raises(
        ValueError,
        match=r"printed to stdout, which is not allowed",
    ):
        PythonSubDimension(
            label="Invalid code",
            weight=1.0,
            scaling_parameters=[],
            python_code="""def score(response_text, input_text, **kwargs):
            print('hello world')
            return { 'score': 1.0, 'explanation': 'good' }""",
        )


def test_python_validator_valid_code():
    PythonSubDimension(
        label="Invalid code",
        weight=1.0,
        scaling_parameters=[],
        python_code="""def score(response_text, input_text, **kwargs):
        return { 'score': 1.0, 'explanation': 'good' }""",
    )
