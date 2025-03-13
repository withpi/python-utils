import json
from collections import defaultdict

import httpx
import markdown
import numpy as np
import pandas as pd
from IPython.display import HTML, display
from matplotlib.colors import LinearSegmentedColormap
from withpi.types import ScoringSpec


def load_scoring_spec_from_web(url: str) -> ScoringSpec:
    """load_scoring_spec_from_web pulls a ScoringSpec JSON blob locally with validation."""
    resp = httpx.get(url)
    return ScoringSpec.model_validate_json(resp.content)


def display_scoring_spec(scoring_spec: ScoringSpec):
    """display_scoring_spec pretty-prints a scoring system in Colab using HTML"""
    html_content = "<div style='font-family: Arial, sans-serif;'>"
    html_content += f"<h2 style='color: #202124; border-bottom: 2px solid #4285F4; padding-bottom: 8px; margin-bottom: 10px;'>ScoringSpec: {scoring_spec.name}</h2>"
    description = scoring_spec.description
    if description is not None:
        description = description.replace("\n", "<br>")
    html_content += f"<p style='margin-top: 0; margin-bottom: 20px; color: #5F6368;'>{description}</p>"

    if scoring_spec.dimensions is None:
        html_content += """
        <div style='background-color: #FFF3E0; border-left: 4px solid #FF9800; padding: 10px;'>
            <p style='margin: 0; color: #E65100;'><strong>Note:</strong> No scoring dimensions available for this scoring spec.</p>
        </div>
        """
    else:
        for dimension in scoring_spec.dimensions:
            # Main dimension as a header
            html_content += f"<h3 style='margin-bottom: 5px; color: #4285F4;'>{dimension.label}</h3>"
            html_content += "<ul style='margin-top: 0; padding-left: 20px;'>"

            for sub_dimension in dimension.sub_dimensions:
                # Sub-dimensions as list items with the scoring type in bold
                html_content += f"<li><strong>{sub_dimension.scoring_type}:</strong> {sub_dimension.description}"

                # Check if python_code exists and display it in a code block
                if (
                    sub_dimension.scoring_type == "PYTHON_CODE"
                    and sub_dimension.python_code
                ):
                    # Create a formatted code block with syntax highlighting
                    html_content += f"""
                    <div style='margin: 10px 0 10px 20px;'>
                        <pre style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto;'>
    <code style='font-family: Monaco, Consolas, "Courier New", monospace; font-size: 13px;'>{sub_dimension.python_code}</code></pre>
                    </div>
                    """

                html_content += "</li>"

            html_content += "</ul>"

        html_content += "</div>"

    # Display the HTML in the notebook
    display(HTML(html_content))


def score_to_color(score):
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


def print_scores(pi_scores):
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
    score_html += "<tr></tr>" + "\n"
    score_html += (
        f"<tr><td>Total score</td><td></td><td style='color: {score_to_color(pi_scores.total_score)}'><b>{round(pi_scores.total_score, 3)}</b></td></tr>"
        + "\n"
    )
    score_html += "</table>"
    return score_html


def pretty_print_responses(
    response1,
    response2=None,
    header=None,
    left_label="Base",
    right_label="Test",
    scores_left=None,
    scores_right=None,
    debug_left=None,
    debug_right=None,
):
    md1 = markdown.markdown(response1)

    # Check if a second response is provided
    is_single_response = response2 is None

    md2 = None
    if not is_single_response:
        md2 = markdown.markdown(response2)

    if scores_left:
        scores_left = print_scores(scores_left)
    if scores_right:
        scores_right = print_scores(scores_right)

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
    if scores_left or scores_right:
        if is_single_response:
            html += f"""
            <div style="display: flex; gap: 20px;">
                <div style="width: 80%; padding: 10px; border: 1px solid #ddd; background-color: #f2f1fe;">
                    {scores_left or ""}
                </div>
            </div>"""
        else:
            html += f"""
            <div style="display: flex; gap: 20px;">
                <div style="width: 40%; padding: 10px; border: 1px solid #ddd; background-color: #f2f1fe;">
                    {scores_left or ""}
                </div>
                <div style="width: 40%; padding: 10px; border: 1px solid #ddd; background-color: #f2f1fe;">
                    {scores_right or ""}
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


def training_stats(
    job_id: str, training_data: dict, is_done: bool, additional_columns: dict[str, str]
):
    """Generate a training progress table dynamically."""
    data_dict = {}
    for header in ["Step", "Epoch", "Learning_Rate", "Training_Loss", "Eval_Loss"]:
        data_dict[header] = []
    for header in additional_columns.keys():
        data_dict[header] = []

    for step, data in training_data.items():
        data_dict["Step"].append(step)
        for header, key in [
            ("Epoch", "epoch"),
            ("Learning_Rate", "learning_rate"),
            ("Training_Loss", "loss"),
            ("Eval_Loss", "eval_loss"),
        ]:
            data_dict[header].append(data.get(key, "X"))
        for header, key in additional_columns.items():
            data_dict[header].append(data.get(key, "X"))

    if not is_done:
        data_dict["Step"].append("...")
        for header in ["Epoch", "Learning_Rate", "Training_Loss", "Eval_Loss"]:
            data_dict[header].append("")
        for header in additional_columns.keys():
            data_dict[header].append("")

    return pd.DataFrame(data_dict)


def stream_training_response(job_id: str, method, additional_columns: dict[str, str]):
    """stream_training_response streams messages from the provided method

    method should be a Pi client object with `retrieve` and `stream_messages`
    endpoints.  This is primarily for convenience."""

    print(f"Training Status for {job_id}")

    training_data = defaultdict(dict)
    stream_output = display(
        training_stats(
            job_id, training_data, is_done=False, additional_columns=additional_columns
        ),
        display_id=True,
    )

    while True:
        response = method.retrieve(job_id=job_id)
        if response.state not in ["QUEUED", "RUNNING"]:
            for line in response.detailed_status:
                try:
                    data_dict = json.loads(line)
                    training_data[data_dict["step"]].update(data_dict)
                except Exception:
                    pass
            stream_output.update(  # type: ignore
                training_stats(
                    job_id,
                    training_data,
                    is_done=True,
                    additional_columns=additional_columns,
                )
            )
            return response

        with method.with_streaming_response.stream_messages(
            job_id=job_id, timeout=None
        ) as response:
            for line in response.iter_lines():
                try:
                    data_dict = json.loads(line)
                    training_data[data_dict["step"]].update(data_dict)
                except Exception:
                    pass
                stream_output.update(  # type: ignore
                    training_stats(
                        job_id,
                        training_data,
                        is_done=False,
                        additional_columns=additional_columns,
                    )
                )
