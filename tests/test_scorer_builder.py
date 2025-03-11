import io

import pytest
from withpi.types import Scorer, ScorerDimension, ScorerSubDimension

from withpi_utils import (
    PiSubDimension,
    PythonSubDimension,
    ScorerBuilder,
    DimensionBuilder,
)


@pytest.fixture
def scorer_builder(scorer):
    return ScorerBuilder.from_scorer(scorer)


@pytest.fixture
def scorer():
    return Scorer(
        name="Test",
        description="Test",
        dimensions=[
            ScorerDimension(
                description="unused",
                label="FirstLabel",
                parameters=[],
                weight=1.0,
                sub_dimensions=[
                    ScorerSubDimension(
                        description="Is it good?",
                        label="Pi Scorer",
                        scoring_type="PI_SCORER",
                        parameters=[],
                        weight=1.0,
                    ),
                    ScorerSubDimension(
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


def test_add_dimension(scorer_builder):
    scorer_builder.add_dimension("test")
    assert [g.label for g in scorer_builder.dimensions] == ["FirstLabel", "test"]


def test_add_dimension_builder(scorer_builder):
    scorer_builder.add_dimension(DimensionBuilder(label="test"))
    assert [g.label for g in scorer_builder.dimensions] == ["FirstLabel", "test"]


def test_remove_dimension(scorer_builder):
    scorer_builder.remove_dimension(scorer_builder.dimensions[0])
    assert len(scorer_builder.dimensions) == 0


def test_print_scorer(scorer_builder):
    buf = io.StringIO()
    scorer_builder.print_scorer(buf)
    assert buf.getvalue() == "FirstLabel\n\tPi Scorer\n\tPython Scorer\n"


def test_add_pi_sub_dimension(scorer_builder):
    dimension = scorer_builder.dimensions[0]
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


def test_add_python_sub_dimension(scorer_builder):
    dimension = scorer_builder.dimensions[0]
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


def test_remove_sub_dimension(scorer_builder):
    dimension = scorer_builder.dimensions[0]
    dimension.remove_sub_dimension(dimension.sub_dimensions[0])
    assert [s.label for s in dimension.sub_dimensions] == ["Python Scorer"]


def test_build_scorer(scorer_builder, scorer):
    built_scorer = scorer_builder.build()
    assert built_scorer.model_dump_json(indent=2) == scorer.model_dump_json(indent=2)


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
