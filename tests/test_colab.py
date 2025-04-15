from pathlib import Path

from withpi_utils.colab import load_scoring_spec, dump_scoring_spec
from withpi.types import Question

DATADIR = Path(__file__).resolve().parent / "data"


def test_dump_scoring_spec():
    path = DATADIR / "scoring_spec.json"
    scoring_spec = [
        Question(question="Is it good?"),
        Question(
            question="Python Code",
            python_code="score = lambda response_text, input_text, **kwargs: { 'score': 1.0, 'explanation': 'good' }",
            scoring_type="PYTHON_CODE",
        ),
    ]
    dump = dump_scoring_spec(scoring_spec)
    assert dump == path.read_text()


def test_load_scoring_spec():
    path = DATADIR / "scoring_spec.json"
    scoring_spec = load_scoring_spec(path.read_bytes())
    assert scoring_spec == [
        Question(
            question="Is it good?",
        ),
        Question(
            question="Python Code",
            python_code="score = lambda response_text, input_text, **kwargs: { 'score': 1.0, 'explanation': 'good' }",
            scoring_type="PYTHON_CODE",
        ),
    ]
