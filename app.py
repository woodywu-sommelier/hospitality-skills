"""Did your AI invent a wine? A Gradio page around the vendored wine-fact-guard."""
import base64
import os
from pathlib import Path

# Before Gradio is imported: no telemetry, and no run history in the visitor's browser.
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["GRADIO_RUN_HISTORY"] = "False"

import gradio as gr  # noqa: E402

from checker import EXAMPLES, MAX_CHARS, run  # noqa: E402

HERE = Path(__file__).resolve().parent
LOGO = base64.b64encode((HERE / "assets" / "icon.png").read_bytes()).decode()

PAPER, OXBLOOD, INK = "#F4EFE6", "#6E2532", "#1F1A17"

HEAD = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:opsz,wght@6..96,500;6..96,700&family=EB+Garamond:ital,wght@0,400;0,600;1,400&display=swap">
<meta name="description" content="Paste a chatbot's answer about a wine and see what it may have invented.">
"""

# The same palette in light and dark mode: this is a printed page.
CSS = f"""
:root, .dark {{
  --body-background-fill: {PAPER};
  --background-fill-primary: {PAPER};
  --background-fill-secondary: #EDE6DA;
  --block-background-fill: #FBF8F2;
  --block-border-color: #D9CFBF;
  --border-color-primary: #D9CFBF;
  --input-background-fill: #FFFDF9;
  --input-border-color-focus: {OXBLOOD};
  --body-text-color: {INK};
  --body-text-color-subdued: #5A4E46;
  --block-label-text-color: #5A4E46;
  --block-title-text-color: {INK};
  --block-info-text-color: #5A4E46;
  --color-accent: {OXBLOOD};
  --color-accent-soft: #F1E3E5;
  --link-text-color: {OXBLOOD};
  --link-text-color-hover: #4A1822;
  --button-primary-background-fill: {OXBLOOD};
  --button-primary-background-fill-hover: #561C27;
  --button-primary-text-color: #FFFDF9;
  --button-secondary-background-fill: #FBF8F2;
  --button-secondary-text-color: {INK};
  --loader-color: {OXBLOOD};
  --font: "EB Garamond", Georgia, "Times New Roman", serif;
}}
body, .gradio-container {{ background: {PAPER} !important; color: {INK}; }}
.gradio-container {{ max-width: 760px !important; margin: 0 auto !important; font-size: 18px; }}
.wfg-masthead {{ text-align: center; padding: 8px 4px 0; }}
.wfg-masthead img {{ width: 64px; height: 64px; border-radius: 50%; }}
.wfg-masthead h1 {{
  font-family: "Bodoni Moda", "Playfair Display", Georgia, serif; font-weight: 700;
  font-size: clamp(2rem, 7vw, 3rem); line-height: 1.1; margin: 8px 0 12px; color: {INK};
}}
.wfg-masthead p {{ font-size: 1.1rem; line-height: 1.5; margin: 0 auto 6px; max-width: 34em; }}
.wfg-rule {{ border: 0; border-top: 1px solid {OXBLOOD}; width: 80px; margin: 14px auto; }}
.wfg-private {{ font-style: italic; color: #5A4E46; }}
.wfg-results h3, .wfg-count {{
  font-family: "Bodoni Moda", Georgia, serif; font-size: 1.5rem; margin: 4px 0 12px;
}}
.wfg-card {{
  background: #FFFDF9; border: 1px solid #D9CFBF; border-left: 4px solid {OXBLOOD};
  border-radius: 6px; padding: 14px 16px; margin: 0 0 14px;
}}
.wfg-type {{ font-weight: 600; font-size: 1.1rem; display: flex; flex-wrap: wrap;
  gap: 8px; align-items: baseline; justify-content: space-between; }}
.wfg-sev {{ font-size: .85rem; font-weight: 400; color: {OXBLOOD}; letter-spacing: .02em; }}
.wfg-phrase {{ margin: 10px 0; padding: 6px 12px; border-left: 2px solid #D9CFBF;
  font-style: italic; overflow-wrap: anywhere; }}
.wfg-reason {{ margin: 6px 0; line-height: 1.5; }}
.wfg-sources {{ font-size: .95rem; color: #5A4E46; }}
.wfg-sources ul, .wfg-handled ul {{ margin: 4px 0 0 18px; padding: 0; }}
.wfg-sources a {{ overflow-wrap: anywhere; }}
.wfg-handled {{ background: #EEF1E8; border-radius: 6px; padding: 10px 14px; margin: 0 0 14px; }}
.wfg-notice {{ background: #F1E3E5; border-radius: 6px; padding: 8px 12px; }}
.wfg-disclaimer {{ font-style: italic; color: #5A4E46; border-top: 1px solid #D9CFBF;
  padding-top: 10px; margin-top: 6px; }}
.wfg-footer {{ text-align: center; font-size: 1rem; line-height: 1.7; padding: 8px 0 20px; }}
.wfg-footer p {{ margin: 2px 0; }}
"""

MASTHEAD = f"""
<div class="wfg-masthead">
  <img src="data:image/png;base64,{LOGO}" alt="Woody Wu bear logo">
  <h1>Did your AI invent a wine?</h1>
  <p>Paste a chatbot's answer about a wine. This checks it against a sourced list of wines that
  were never made, and flags invented scores and tasting claims. Built by sommelier Woody Wu.</p>
  <hr class="wfg-rule">
  <p class="wfg-private">Nothing you paste is stored.</p>
</div>
"""

FOOTER = """
<div class="wfg-footer">
  <hr class="wfg-rule">
  <p>Want this checked by a sommelier for your AI product?
     <a href="https://woodywusommelier.com/consulting/ai-teams/" target="_blank" rel="noopener">woodywusommelier.com/consulting/ai-teams/</a></p>
  <p>Full benchmark: <a href="https://woodywusommelier.com/constance-test/" target="_blank" rel="noopener">woodywusommelier.com/constance-test/</a></p>
  <p>Code: <a href="https://github.com/woodywu-sommelier/hospitality-skills" target="_blank" rel="noopener">github.com/woodywu-sommelier/hospitality-skills</a></p>
</div>
"""

with gr.Blocks(title="Did your AI invent a wine?", analytics_enabled=False) as demo:
    gr.HTML(MASTHEAD)
    answer = gr.Textbox(label="Paste the AI's answer", lines=10, max_lines=30,
                        placeholder="Paste the chatbot's answer here.")
    question = gr.Textbox(label="What did you ask it? (optional)", lines=2, max_lines=6,
                          info="Adding the question also catches answers that play along with a "
                               "wine that was never made.")
    result = gr.HTML(render=False)
    gr.Examples(
        examples=[[answer_text, question_text] for _, answer_text, question_text in EXAMPLES],
        example_labels=[label for label, _, _ in EXAMPLES],
        inputs=[answer, question], outputs=result, fn=run,
        cache_examples=False, run_on_click=True, label="Try an example (written for this page)",
    )
    check_button = gr.Button("Check the answer", variant="primary")
    gr.Markdown(f"Up to {MAX_CHARS:,} characters are checked.", elem_classes="wfg-private")
    result.render()
    gr.HTML(FOOTER)
    check_button.click(run, inputs=[answer, question], outputs=result, show_progress="minimal")

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Base(), css=CSS, head=HEAD, footer_links=[],
                run_history=False, enable_monitoring=False, mcp_server=False)
