"""Unit tests for schema versioning."""

import importlib
import pytest

_semver = importlib.import_module("src.schemas.schema-versioning")

parse_semver = _semver.parse_semver
format_semver = _semver.format_semver
compare_versions = _semver.compare_versions
is_backward_compatible = _semver.is_backward_compatible
compute_next_version = _semver.compute_next_version


class TestSemverParsing:
    """Test semantic version parsing."""

    @pytest.mark.unit
    def test_parse_valid_semver(self):
        """Parsing valid semver returns tuple."""
        major, minor, patch = parse_semver("1.2.3")
        assert major == 1
        assert minor == 2
        assert patch == 3

    @pytest.mark.unit
    def test_parse_semver_zeros(self):
        """Parsing semver with zeros works."""
        major, minor, patch = parse_semver("0.0.0")
        assert major == 0
        assert minor == 0
        assert patch == 0

    @pytest.mark.unit
    def test_parse_semver_large_numbers(self):
        """Parsing semver with large numbers works."""
        major, minor, patch = parse_semver("10.20.999")
        assert major == 10
        assert minor == 20
        assert patch == 999

    @pytest.mark.unit
    def test_parse_invalid_format_raises_valueerror(self):
        """Invalid semver format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid semver format"):
            parse_semver("1.2")

    @pytest.mark.unit
    def test_parse_non_numeric_raises_valueerror(self):
        """Non-numeric parts raise ValueError."""
        with pytest.raises(ValueError, match="Invalid semver format"):
            parse_semver("1.a.3")

    @pytest.mark.unit
    def test_parse_negative_raises_valueerror(self):
        """Negative parts raise ValueError."""
        with pytest.raises(ValueError, match="Invalid semver format"):
            parse_semver("1.-2.3")


class TestSemverFormatting:
    """Test semantic version formatting."""

    @pytest.mark.unit
    def test_format_semver(self):
        """Formatting semver components."""
        result = format_semver(2, 3, 4)
        assert result == "2.3.4"

    @pytest.mark.unit
    def test_format_semver_zeros(self):
        """Formatting semver with zeros."""
        result = format_semver(0, 0, 0)
        assert result == "0.0.0"


class TestSemverComparison:
    """Test semantic version comparison."""

    @pytest.mark.unit
    def test_compare_major_version(self):
        """Comparing major versions."""
        assert compare_versions("2.0.0", "1.0.0") == 1
        assert compare_versions("1.0.0", "2.0.0") == -1
        assert compare_versions("1.0.0", "1.0.0") == 0

    @pytest.mark.unit
    def test_compare_minor_version(self):
        """Comparing minor versions."""
        assert compare_versions("1.2.0", "1.1.0") == 1
        assert compare_versions("1.1.0", "1.2.0") == -1

    @pytest.mark.unit
    def test_compare_patch_version(self):
        """Comparing patch versions."""
        assert compare_versions("1.0.3", "1.0.2") == 1
        assert compare_versions("1.0.2", "1.0.3") == -1

    @pytest.mark.unit
    def test_compare_equal_versions(self):
        """Comparing equal versions returns 0."""
        assert compare_versions("1.2.3", "1.2.3") == 0


class TestBackwardCompatibility:
    """Test backward compatibility checking."""

    @pytest.mark.unit
    def test_no_changes_compatible(self):
        """Identical fields are compatible."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        assert is_backward_compatible(old, new) is True

    @pytest.mark.unit
    def test_adding_field_compatible(self):
        """Adding new field is compatible."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "optional once"},
        ]
        assert is_backward_compatible(old, new) is True

    @pytest.mark.unit
    def test_removing_field_incompatible(self):
        """Removing field is not compatible."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        assert is_backward_compatible(old, new) is False

    @pytest.mark.unit
    def test_changing_type_incompatible(self):
        """Changing field type is not compatible."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "number", "occurrence": "required once"},
        ]
        assert is_backward_compatible(old, new) is False

    @pytest.mark.unit
    def test_changing_occurrence_incompatible(self):
        """Changing field occurrence is not compatible."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "optional once"},
        ]
        assert is_backward_compatible(old, new) is False


class TestVersionBumping:
    """Test version bump computation."""

    @pytest.mark.unit
    def test_bump_major_on_field_removal(self):
        """Removing field bumps major version."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        result = compute_next_version(old, new, "1.0.0")
        assert result == "2.0.0"

    @pytest.mark.unit
    def test_bump_major_on_type_change(self):
        """Changing field type bumps major version."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "number", "occurrence": "required once"},
        ]
        result = compute_next_version(old, new, "1.0.0")
        assert result == "2.0.0"

    @pytest.mark.unit
    def test_bump_major_on_occurrence_change(self):
        """Changing field occurrence bumps major version."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "optional once"},
        ]
        result = compute_next_version(old, new, "1.0.0")
        assert result == "2.0.0"

    @pytest.mark.unit
    def test_bump_minor_on_field_addition(self):
        """Adding field bumps minor version."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "optional once"},
        ]
        result = compute_next_version(old, new, "1.0.0")
        assert result == "1.1.0"

    @pytest.mark.unit
    def test_bump_patch_on_prompt_change(self):
        """Changing prompt only bumps patch version."""
        old = [
            {
                "label_name": "a",
                "data_type": "text",
                "occurrence": "required once",
                "prompt_for_label": "Old prompt",
            },
        ]
        new = [
            {
                "label_name": "a",
                "data_type": "text",
                "occurrence": "required once",
                "prompt_for_label": "New prompt",
            },
        ]
        result = compute_next_version(old, new, "1.0.0")
        assert result == "1.0.1"

    @pytest.mark.unit
    def test_no_change_same_version(self):
        """No field changes returns same version."""
        old = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
        ]
        result = compute_next_version(old, new, "1.0.0")
        assert result == "1.0.0"

    @pytest.mark.unit
    def test_major_bump_resets_minor_patch(self):
        """Major bump resets minor and patch."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [{"label_name": "b", "data_type": "text", "occurrence": "required once"}]
        result = compute_next_version(old, new, "1.5.7")
        assert result == "2.0.0"

    @pytest.mark.unit
    def test_minor_bump_resets_patch(self):
        """Minor bump resets patch."""
        old = [{"label_name": "a", "data_type": "text", "occurrence": "required once"}]
        new = [
            {"label_name": "a", "data_type": "text", "occurrence": "required once"},
            {"label_name": "b", "data_type": "text", "occurrence": "optional once"},
        ]
        result = compute_next_version(old, new, "1.5.7")
        assert result == "1.6.0"
