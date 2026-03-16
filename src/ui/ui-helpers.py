"""Format extraction results for Gradio display."""


def format_results_table(results: list[dict] | None) -> list[list[str]] | None:
    """Convert extraction results to table rows for Gradio Dataframe."""
    if not results:
        return None

    rows = []
    for r in results:
        value = r.get("value", "")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        elif value is None:
            value = "(not found)"

        confidence = r.get("confidence")
        conf_str = f"{confidence:.1%}" if confidence is not None else "-"

        rows.append([
            r.get("label_name", ""),
            r.get("data_type", ""),
            str(value),
            conf_str,
        ])

    return rows


def format_confidence(confidence: float | None) -> str:
    """Format confidence score for display."""
    if confidence is None:
        return "N/A"
    return f"{confidence:.1%}"


def format_cost(cost: dict | None) -> str:
    """Format cost info for display."""
    if not cost:
        return "N/A (local)"

    parts = []
    if cost.get("input_tokens"):
        parts.append(f"Input: {cost['input_tokens']} tokens")
    if cost.get("output_tokens"):
        parts.append(f"Output: {cost['output_tokens']} tokens")
    if cost.get("estimated_cost_usd"):
        parts.append(f"Cost: ${cost['estimated_cost_usd']:.6f}")

    return " | ".join(parts) if parts else "N/A"
