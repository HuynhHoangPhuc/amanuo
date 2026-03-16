"""Semantic versioning utilities for schema version management."""


def parse_semver(version_str: str) -> tuple[int, int, int]:
    """Parse 'MAJOR.MINOR.PATCH' string. Raises ValueError on invalid format."""
    parts = version_str.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semver format: '{version_str}'. Expected 'MAJOR.MINOR.PATCH'.")
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        raise ValueError(f"Invalid semver format: '{version_str}'. Each part must be an integer.")
    if major < 0 or minor < 0 or patch < 0:
        raise ValueError(f"Invalid semver format: '{version_str}'. Parts must be non-negative.")
    return major, minor, patch


def format_semver(major: int, minor: int, patch: int) -> str:
    """Format semver components to string."""
    return f"{major}.{minor}.{patch}"


def compare_versions(v1: str, v2: str) -> int:
    """Compare two semver strings. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
    t1 = parse_semver(v1)
    t2 = parse_semver(v2)
    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    return 0


def is_backward_compatible(old_fields: list, new_fields: list) -> bool:
    """Check if new fields are backward compatible with old fields.

    Compatible = no fields removed, no type/occurrence changes on existing fields.
    Adding new fields is allowed.
    """
    old_map = {f["label_name"]: f for f in old_fields}
    new_map = {f["label_name"]: f for f in new_fields}

    # Any old field removed → breaking
    for name in old_map:
        if name not in new_map:
            return False
        old_f = old_map[name]
        new_f = new_map[name]
        if old_f["data_type"] != new_f["data_type"] or old_f["occurrence"] != new_f["occurrence"]:
            return False

    return True


def compute_next_version(old_fields: list, new_fields: list, current_version: str) -> str:
    """Determine version bump based on field diff.

    Rules:
    - Remove field or change data_type/occurrence → major bump
    - Add new field → minor bump
    - Change only prompt_for_label → patch bump
    - No changes → same version (no bump)
    """
    old_names = {f["label_name"] for f in old_fields}
    new_names = {f["label_name"] for f in new_fields}

    removed = old_names - new_names
    added = new_names - old_names

    # Check type/occurrence changes and prompt changes on existing fields
    type_changed = False
    prompt_changed = False
    for name in old_names & new_names:
        old_f = next(f for f in old_fields if f["label_name"] == name)
        new_f = next(f for f in new_fields if f["label_name"] == name)
        if old_f["data_type"] != new_f["data_type"] or old_f["occurrence"] != new_f["occurrence"]:
            type_changed = True
        if old_f.get("prompt_for_label") != new_f.get("prompt_for_label"):
            prompt_changed = True

    major, minor, patch = parse_semver(current_version)

    if removed or type_changed:
        return format_semver(major + 1, 0, 0)  # breaking change
    elif added:
        return format_semver(major, minor + 1, 0)  # backward-compatible addition
    elif prompt_changed:
        return format_semver(major, minor, patch + 1)  # metadata change
    else:
        return current_version  # no change
