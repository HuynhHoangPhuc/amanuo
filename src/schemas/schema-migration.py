"""Field diff analysis and migration validation for schema versioning."""

from dataclasses import dataclass, field


@dataclass
class FieldDiff:
    """Result of comparing old and new schema fields."""
    added: list[str] = field(default_factory=list)        # field names added
    removed: list[str] = field(default_factory=list)      # field names removed
    type_changed: list[str] = field(default_factory=list) # fields with type/occurrence change
    prompt_changed: list[str] = field(default_factory=list) # fields with only prompt change
    unchanged: list[str] = field(default_factory=list)    # completely unchanged fields


def diff_fields(old_fields: list[dict], new_fields: list[dict]) -> FieldDiff:
    """Compare old and new field lists. Returns FieldDiff."""
    old_map = {f["label_name"]: f for f in old_fields}
    new_map = {f["label_name"]: f for f in new_fields}

    old_names = set(old_map.keys())
    new_names = set(new_map.keys())

    result = FieldDiff(
        added=sorted(new_names - old_names),
        removed=sorted(old_names - new_names),
    )

    for name in sorted(old_names & new_names):
        old_f = old_map[name]
        new_f = new_map[name]

        type_or_occurrence_changed = (
            old_f["data_type"] != new_f["data_type"]
            or old_f["occurrence"] != new_f["occurrence"]
        )
        prompt_changed = old_f.get("prompt_for_label") != new_f.get("prompt_for_label")

        if type_or_occurrence_changed:
            result.type_changed.append(name)
        elif prompt_changed:
            result.prompt_changed.append(name)
        else:
            result.unchanged.append(name)

    return result


def validate_migration(old_fields: list[dict], new_fields: list[dict]) -> list[str]:
    """Validate migration. Returns list of warning messages.

    Warnings for:
    - Removed fields (breaking change)
    - Type changes (breaking change)
    - Required field changed to optional
    """
    diff = diff_fields(old_fields, new_fields)
    warnings: list[str] = []

    for name in diff.removed:
        warnings.append(
            f"Breaking change: field '{name}' removed. Existing documents may lose data."
        )

    old_map = {f["label_name"]: f for f in old_fields}
    new_map = {f["label_name"]: f for f in new_fields}

    for name in diff.type_changed:
        old_f = old_map[name]
        new_f = new_map[name]
        if old_f["data_type"] != new_f["data_type"]:
            warnings.append(
                f"Breaking change: field '{name}' data_type changed from "
                f"'{old_f['data_type']}' to '{new_f['data_type']}'."
            )
        if old_f["occurrence"] != new_f["occurrence"]:
            warnings.append(
                f"Breaking change: field '{name}' occurrence changed from "
                f"'{old_f['occurrence']}' to '{new_f['occurrence']}'."
            )
            # Specifically warn when required → optional
            if "required" in old_f["occurrence"] and "optional" in new_f["occurrence"]:
                warnings.append(
                    f"Warning: field '{name}' changed from required to optional. "
                    "Previously mandatory extractions may now be skipped."
                )

    return warnings
