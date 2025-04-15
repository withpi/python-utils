import pytest
from withpi.types import Question

from withpi_utils import (
    PiQuestionBuilder,
    PythonQuestionBuilder,
)


@pytest.fixture
def scoring_spec():
    return [
        Question(
            question="Is it good?",
        ),
        Question(
            question="Python Code",
            python_code="score = lambda response_text, input_text, **kwargs: { 'score': 1.0, 'explanation': 'good' }",
            scoring_type="PYTHON_CODE",
        ),
    ]


def test_build_pi_question():
    question = PiQuestionBuilder.from_question("Is it good?")
    assert question.question == "Is it good?"


def test_build_python_question():
    question = PythonQuestionBuilder.from_python_string(
        question="Python",
        python_code="score = lambda response_text, input_text, **kwargs: { 'score': 1.0, 'explanation': 'good' }",
    )
    assert question.question == "Python"


def test_python_validator_not_python():
    with pytest.raises(SyntaxError):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="junk(",
        )


def test_python_validator_no_score():
    with pytest.raises(ValueError, match=r"did not define a score\(\) method"):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="print('hello world')",
        )


def test_python_validator_not_a_function():
    with pytest.raises(TypeError, match=r"is not a callable object"):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="score = 10",
        )


def test_python_validator_wrong_arguments():
    with pytest.raises(ValueError, match=r"does not accept a response_text parameter"):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="score = lambda x: x",
        )


def test_python_validator_missing_input_text():
    with pytest.raises(ValueError, match=r"does not accept an input_text parameter"):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="score = lambda response_text: response_text",
        )


def test_python_validator_kwargs_faked():
    with pytest.raises(ValueError, match=r"does not accept a \*\*kwargs parameter"):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="def score(response_text, input_text, kwargs):...",
        )


def test_python_validator_no_dict_return():
    with pytest.raises(ValueError, match=r"did not return a dictionary"):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="""def score(response_text, input_text, **kwargs):
        return 1.0""",
        )


def test_python_validator_bad_score():
    with pytest.raises(
        ValueError,
        match=r"did not return a dictionary with a 'score' key of float type",
    ):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="""def score(response_text, input_text, **kwargs):
        return { 'score': 'bad' }""",
        )


def test_python_validator_bad_score_range():
    with pytest.raises(
        ValueError,
        match=r"returned a score outside the range \[0, 1\]",
    ):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="""def score(response_text, input_text, **kwargs):
        return { 'score': 2.0 }""",
        )


def test_python_validator_no_explanation():
    with pytest.raises(
        ValueError,
        match=r"with an 'explanation' key of str type",
    ):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="""def score(response_text, input_text, **kwargs):
            return { 'score': 1.0 }""",
        )


def test_python_validator_prints_to_stdout():
    with pytest.raises(
        ValueError,
        match=r"printed to stdout, which is not allowed",
    ):
        PythonQuestionBuilder.from_python_string(
            question="Invalid code",
            python_code="""def score(response_text, input_text, **kwargs):
            print('hello world')
            return { 'score': 1.0, 'explanation': 'good' }""",
        )


def test_python_validator_valid_code():
    PythonQuestionBuilder.from_python_string(
        question="OK code",
        python_code="""def score(response_text, input_text, **kwargs):
        return { 'score': 1.0, 'explanation': 'good' }""",
    )
