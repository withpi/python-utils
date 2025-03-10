from IPython.display import HTML, display
from withpi.types import Scorer


def display_scorer(scorer: Scorer):
    """display_scorer pretty-prints a scoring system in Colab using HTML"""
    html_content = "<div style='font-family: Arial, sans-serif;'>"
    html_content += f"<h2 style='color: #202124; border-bottom: 2px solid #4285F4; padding-bottom: 8px; margin-bottom: 10px;'>Scorer: {scorer.name}</h2>"
    description = scorer.description
    if description is not None:
        description = description.replace("\n", "<br>")
    html_content += f"<p style='margin-top: 0; margin-bottom: 20px; color: #5F6368;'>{description}</p>"

    if scorer.dimensions is None:
        html_content += """
        <div style='background-color: #FFF3E0; border-left: 4px solid #FF9800; padding: 10px;'>
            <p style='margin: 0; color: #E65100;'><strong>Note:</strong> No scoring dimensions available for this scorer.</p>
        </div>
        """
    else:
        for dimension in scorer.dimensions:
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
