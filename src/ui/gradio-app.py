"""Gradio web UI for Amanuo OCR system."""

import importlib
import json
import time

import gradio as gr
import httpx

_ui_helpers = importlib.import_module("src.ui.ui-helpers")

# Internal API base URL
_API_BASE = "http://localhost:8000"


def _sync_post(path: str, **kwargs) -> httpx.Response:
    """Synchronous HTTP POST to internal API."""
    with httpx.Client(timeout=30.0) as client:
        return client.post(f"{_API_BASE}{path}", **kwargs)


def _sync_get(path: str) -> httpx.Response:
    """Synchronous HTTP GET to internal API."""
    with httpx.Client(timeout=30.0) as client:
        return client.get(f"{_API_BASE}{path}")


def submit_extraction(image_path, mode, provider, schema_json):
    """Submit extraction job and poll for results."""
    if not image_path:
        return "Error: No image uploaded", None, "", ""

    if not schema_json or not schema_json.strip():
        return "Error: Schema is required", None, "", ""

    # Validate schema JSON
    try:
        fields = json.loads(schema_json)
        if not isinstance(fields, list):
            return "Error: Schema must be a JSON array", None, "", ""
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON - {e}", None, "", ""

    # Submit job
    try:
        with open(image_path, "rb") as f:
            resp = _sync_post(
                "/extract",
                files={"file": ("document.png", f)},
                data={
                    "mode": mode,
                    "cloud_provider": provider,
                    "schema_fields": schema_json,
                },
            )

        if resp.status_code != 202:
            return f"Error: {resp.text}", None, "", ""

        job_id = resp.json()["job_id"]
    except Exception as e:
        return f"Error submitting job: {e}", None, "", ""

    # Poll for results
    for _ in range(60):  # Max 2 minutes
        time.sleep(2)
        try:
            resp = _sync_get(f"/jobs/{job_id}")
            job = resp.json()

            if job["status"] == "completed":
                table = _ui_helpers.format_results_table(job.get("result", []))
                confidence = _ui_helpers.format_confidence(job.get("confidence"))
                cost = _ui_helpers.format_cost(job.get("cost"))
                return f"Completed (Job: {job_id})", table, confidence, cost

            if job["status"] == "failed":
                return f"Failed: {job.get('error', 'Unknown error')}", None, "", ""

        except Exception as e:
            return f"Error polling job: {e}", None, "", ""

    return "Timeout: Job did not complete in 2 minutes", None, "", ""


def load_schemas_list():
    """Load saved schemas for dropdown."""
    try:
        resp = _sync_get("/schemas")
        schemas = resp.json()
        return {s["name"]: json.dumps(s["fields"], indent=2) for s in schemas}
    except Exception:
        return {}


def save_schema_handler(name, schema_json):
    """Save a new schema."""
    if not name or not schema_json:
        return "Error: Name and schema are required"
    try:
        fields = json.loads(schema_json)
        resp = _sync_post("/schemas", json={"name": name, "fields": fields})
        if resp.status_code == 201:
            return f"Schema '{name}' saved successfully"
        return f"Error: {resp.text}"
    except Exception as e:
        return f"Error: {e}"


def on_schema_select(schema_name, schemas_map):
    """Load schema fields when dropdown selection changes."""
    if schema_name and schema_name in schemas_map:
        return schemas_map[schema_name]
    return ""


def create_ui() -> gr.Blocks:
    """Create the Gradio UI for Amanuo OCR."""
    schemas_map = gr.State({})

    with gr.Blocks(title="Amanuo OCR") as demo:
        gr.Markdown("# Amanuo OCR System\nAdaptive hybrid document extraction")

        with gr.Tab("Extract"):
            with gr.Row():
                with gr.Column(scale=1):
                    image_input = gr.Image(type="filepath", label="Document Image")
                    with gr.Row():
                        mode = gr.Radio(
                            ["local_only", "cloud", "auto"],
                            value="auto", label="Processing Mode",
                        )
                        provider = gr.Dropdown(
                            ["gemini", "mistral"],
                            value="gemini", label="Cloud Provider",
                        )

                    schema_dropdown = gr.Dropdown(
                        label="Load Saved Schema", choices=[], interactive=True,
                    )
                    schema_json = gr.Code(
                        language="json", label="Schema (JSON array)",
                        value='[\n  {\n    "label_name": "example",\n    "data_type": "plain text",\n    "occurrence": "required once"\n  }\n]',
                    )
                    submit_btn = gr.Button("Extract", variant="primary", size="lg")

                with gr.Column(scale=1):
                    status_text = gr.Textbox(label="Status", interactive=False)
                    results_table = gr.Dataframe(
                        label="Extraction Results",
                        headers=["Field", "Type", "Value", "Confidence"],
                    )
                    confidence_text = gr.Textbox(label="Confidence Score", interactive=False)
                    cost_text = gr.Textbox(label="Cost", interactive=False)

            submit_btn.click(
                fn=submit_extraction,
                inputs=[image_input, mode, provider, schema_json],
                outputs=[status_text, results_table, confidence_text, cost_text],
            )

            # Load schemas on tab view
            demo.load(
                fn=lambda: list(load_schemas_list().keys()),
                outputs=[schema_dropdown],
            )

        with gr.Tab("Schemas"):
            with gr.Row():
                schema_name_input = gr.Textbox(label="Schema Name", placeholder="e.g., vehicle-license-vn")
                schema_editor = gr.Code(language="json", label="Schema Definition")

            with gr.Row():
                save_btn = gr.Button("Save Schema", variant="primary")
                save_status = gr.Textbox(label="Status", interactive=False)

            save_btn.click(
                fn=save_schema_handler,
                inputs=[schema_name_input, schema_editor],
                outputs=[save_status],
            )

    return demo
