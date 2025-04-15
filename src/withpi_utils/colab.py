import httpx
import json
import markdown
import numpy as np
from IPython.display import HTML, display
from matplotlib.colors import LinearSegmentedColormap
from withpi.types import Question, ScoringSystemMetrics


def load_scoring_spec_from_web(url: str) -> list[Question]:
    """load_scoring_spec_from_web pulls a scoring spec from a URL."""
    resp = httpx.get(url)
    return load_scoring_spec(resp.content)


def load_scoring_spec(
    scoring_spec: str | bytes | bytearray | list[dict],
) -> list[Question]:
    if not isinstance(scoring_spec, dict):
        parsed = json.loads(scoring_spec)  # type: ignore
    else:
        parsed = scoring_spec
    if not isinstance(parsed, list):
        raise ValueError("Expected a list of questions")
    return [Question.model_validate(q) for q in parsed]


def dump_scoring_spec(scoring_spec: list[Question]) -> str:
    """dump_scoring_spec prints a scoring spec in JSON form, returning it to be saved in a file"""
    # Convert the list of Question objects to a list of dictionaries
    scoring_spec_dicts = [question.model_dump() for question in scoring_spec]

    # Convert the list of dictionaries to a JSON string
    return json.dumps(scoring_spec_dicts, indent=2)


def display_scoring_spec(scoring_spec: list[Question]) -> None:
    """display_scoring_spec pretty-prints a scoring system in Colab using HTML"""
    html_content = "<div style='font-family: Arial, sans-serif;'>"
    html_content += "<h2 style='color: #202124; border-bottom: 2px solid #4285F4; padding-bottom: 8px; margin-bottom: 10px;'>Scoring Spec</h2>"

    if len(scoring_spec) == 0:
        html_content += """
        <div style='background-color: #FFF3E0; border-left: 4px solid #FF9800; padding: 10px;'>
            <p style='margin: 0; color: #E65100;'><strong>Note:</strong> No questions available for this scoring spec.</p>
        </div>
        """
    else:
        html_content += "<ul style='margin-top: 0; padding-left: 20px;'>"
        for question in scoring_spec:
            # Sub-dimensions as list items with the scoring type in bold (if not PI SCORER)
            if question.scoring_type is None or question.scoring_type == "PI_SCORER":
                html_content += f"<li>{question.question}"
            else:
                html_content += (
                    f"<li><strong>{question.scoring_type}:</strong> {question.question}"
                )

            # Check if python_code exists and display it in a code block
            if question.scoring_type == "PYTHON_CODE" and question.python_code:
                # Create a formatted code block with syntax highlighting
                html_content += f"""
                <div style='margin: 10px 0 10px 20px;'>
                    <pre style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto;'>
    <code style='font-family: Monaco, Consolas, "Courier New", monospace; font-size: 13px;'>{question.python_code}</code></pre>
                    </div>
                """

            html_content += "</li>"

        html_content += "</ul>"

    html_content += "</div>"

    # Display the HTML in the notebook
    display(HTML(html_content))


def score_to_color(score: float) -> str:
    """Convert a score to a color using a custom colormap."""
    score = np.clip(score, 0, 1)  # Ensure score is within [0, 1]

    # Define the key color points
    colors = [
        (0.0, "#e74c3c"),  # Red
        (0.3, "#e67e22"),  # Orange
        (0.5, "#f1c40f"),  # Yellow
        (0.7, "#2ecc71"),  # Green-ish
        (1.0, "#27ae60"),  # Bright Green
    ]

    # Create a colormap
    cmap = LinearSegmentedColormap.from_list(
        "custom_colormap", [c[1] for c in colors], N=256
    )

    # Normalize score to the colormap range
    rgba = cmap(score)

    # Convert RGBA to HEX
    return "#{:02x}{:02x}{:02x}".format(
        int(rgba[0] * 255), int(rgba[1] * 255), int(rgba[2] * 255)
    )


def print_scores(pi_scores: ScoringSystemMetrics) -> str:
    """Print the scores in a pretty HTML table."""
    score_html = """
  <style>
  table {
    border-collapse: collapse; /* Ensures borders don't double up */
    width: 100%; /* Optional: makes the table full width */
  }

  tr {
    border-bottom: 1px solid #ccc; /* Sets a bottom border for each row */
    border-top: 1px solid #ccc; /* Sets a bottom border for each row */
  }

  th, td {
    font-weight: bold;
    padding: 4px; /* Adds some spacing */
    text-align: left; /* Aligns text to the left */
    border-right: 1px solid #ccc; /* Sets a bottom border for each row */
    border-left: 1px solid #ccc; /* Sets a bottom border for each row */
  }
  img {
    width: 30%;
  }
  </style>
  <table>"""

    if pi_scores.dimension_scores:
        for dimension_name, dimension_scores in pi_scores.dimension_scores.items():
            score_html += (
                f"<tr><td><b>{dimension_name}</b></td><td></td><td style='color: {score_to_color(dimension_scores.total_score)}'>{round(dimension_scores.total_score, 3)}</td></tr>"
                + "\n"
            )
            for (
                subdimension_name,
                subdimension_score,
            ) in dimension_scores.subdimension_scores.items():
                score_html += (
                    f"<tr><td></td><td style='font-weight: normal;'>{subdimension_name}</td><td style='color: {score_to_color(subdimension_score)}'>{round(subdimension_score, 3)}</td></tr>"
                    + "\n"
                )
            score_html += "\n\n"
    else:
        for question_name, question_score in pi_scores.question_scores.items():
            score_html += (
                f"<tr><td><b>{question_name}</b></td><td style='color: {score_to_color(question_score)}'>{round(question_score, 3)}</td><td></td></tr>"
                + "\n"
            )
    score_html += (
        f"<tr><td>Total score</td><td></td><td style='color: {score_to_color(pi_scores.total_score)}'><b>{round(pi_scores.total_score, 3)}</b></td></tr>"
        + "\n"
    )
    score_html += "</table>"
    return score_html


def pretty_print_responses(
    response1: str,
    response2: str | None = None,
    header: str | None = None,
    left_label: str = "Base",
    right_label: str = "Test",
    scores_left: ScoringSystemMetrics | None = None,
    scores_right: ScoringSystemMetrics | None = None,
    debug_left: str | None = None,
    debug_right: str | None = None,
) -> None:
    md1 = markdown.markdown(response1)

    # Check if a second response is provided
    is_single_response = response2 is None

    md2 = None
    if not is_single_response:
        md2 = markdown.markdown(response2)

    if scores_left:
        scores_left_rendered = print_scores(scores_left)
    else:
        scores_left_rendered = None
    if scores_right:
        scores_right_rendered = print_scores(scores_right)
    else:
        scores_right_rendered = None

    if header:
        header = markdown.markdown(header)
        header_padding = "10px" if is_single_response else "30px"
        html = f"""
        <div style="display: flex; gap: 20px;">
            <div style="width: 80%; padding: {header_padding}; border: 1px solid #ddd; background-color: #fff9f5;">
                <h4>{header}</h4>
            </div>
        </div>"""
    else:
        html = ""

    # For single response, only show one column
    if is_single_response:
        html += f"""
        <div style="display: flex; gap: 20px;">
            <div style="width: 80%; padding: 10px; border: 1px solid #ddd; background-color: #f0f0f0; text-align:center;">
                <h4>{left_label}</h4>
            </div>
        </div>
        <div style="display: flex; gap: 20px;">
            <div style="width: 80%; padding: 10px; border: 1px solid #ddd;">
                {md1}
            </div>
        </div>
        """
    else:
        # Original two-column layout
        html += f"""
        <div style="display: flex; gap: 20px;">
            <div style="width: 40%; padding: 10px; border: 1px solid #ddd; background-color: #f0f0f0; text-align:center;">
                <h4>{left_label}</h4>
            </div>
            <div style="width: 40%; padding: 10px; border: 1px solid #ddd; background-color: #f0f0f0; text-align:center;">
                <h4>{right_label}</h4>
            </div>
        </div>
        <div style="display: flex; gap: 20px;">
            <div style="width: 40%; padding: 10px; border: 1px solid #ddd;">
                {md1}
            </div>
            <div style="width: 40%; padding: 10px; border: 1px solid #ddd;">
                {md2}
            </div>
        </div>
        """

    # Handle scores display based on single/dual response
    if scores_left_rendered or scores_right_rendered:
        if is_single_response:
            html += f"""
            <div style="display: flex; gap: 20px;">
                <div style="width: 80%; padding: 10px; border: 1px solid #ddd; background-color: #f2f1fe;">
                    {scores_left_rendered or ""}
                </div>
            </div>"""
        else:
            html += f"""
            <div style="display: flex; gap: 20px;">
                <div style="width: 40%; padding: 10px; border: 1px solid #ddd; background-color: #f2f1fe;">
                    {scores_left_rendered or ""}
                </div>
                <div style="width: 40%; padding: 10px; border: 1px solid #ddd; background-color: #f2f1fe;">
                    {scores_right_rendered or ""}
                </div>
            </div>"""

    # Handle debug display based on single/dual response
    if debug_left or debug_right:
        if is_single_response and debug_left:
            html += f"""
            <div style="display: flex; gap: 20px;">
                <div style="width: 80%; padding: 10px; border: 1px solid #ddd; background-color: #f0f0f0;">
                    {debug_left or ""}
                </div>
            </div>"""
        elif not is_single_response:
            html += f"""
            <div style="display: flex; gap: 20px;">
                <div style="width: 40%; padding: 10px; border: 1px solid #ddd; background-color: #f0f0f0;">
                    {debug_left or ""}
                </div>
                <div style="width: 40%; padding: 10px; border: 1px solid #ddd; background-color: #f0f0f0;">
                    {debug_right or ""}
                </div>
            </div>"""

    display(HTML(html))
