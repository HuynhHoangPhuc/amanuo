"""Conflict detection and resolution logic for approval engine."""

import json
from collections import defaultdict


def detect_conflicts(assignments: list) -> dict:
    """Detect field-level conflicts across completed assignments.

    Compares corrected field values across assignments in the same round.
    Returns dict of {field_label: [distinct_values]} for conflicting fields.
    """
    field_values: dict[str, set] = defaultdict(set)

    for assignment in assignments:
        if assignment.status not in ("approved", "corrected"):
            continue
        if not assignment.corrected_result:
            continue

        corrected = json.loads(assignment.corrected_result)
        for field in corrected:
            label = field.get("label_name", field.get("label", ""))
            value = str(field.get("value", ""))
            field_values[label].add(value)

    # Conflict = same field has 2+ different values
    return {
        label: sorted(vals)
        for label, vals in field_values.items()
        if len(vals) > 1
    }


def build_conflict_summary(conflicts: dict) -> list[dict]:
    """Format conflicts for API response / audit log."""
    return [
        {"field": label, "values": values}
        for label, values in conflicts.items()
    ]
