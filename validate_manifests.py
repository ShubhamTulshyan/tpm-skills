#!/usr/bin/env python3
"""
Validation script for TPM-Skills manifest files.

Validates all SK-*/skill.json files against the schema and reports any errors.
Exits with code 0 if all pass, 1 if any fail.
"""

import json
import sys
from pathlib import Path


VALID_FAMILIES = {"strategy", "evaluation", "forward_intelligence", "executive_control"}

FAMILY_LAYERS: dict[str, list[int]] = {
    "strategy": [1],
    "evaluation": [2],
    "forward_intelligence": [3],
    "executive_control": [4],
}

VALID_STATUSES = {"scaffold", "alpha", "beta", "production", "deprecated"}

REQUIRED_FIELDS = {
    "id": str,
    "name": str,
    "family": str,
    "layer": int,
    "description": str,
    "data_requirements": list,
    "has_tool": bool,
    "dependencies": list,
    "status": str,
}


def validate_schema(data: dict, skill_id: str, all_skill_ids: set[str]) -> list[str]:
    """Validate that data matches the skill.json schema.

    Args:
        data: Parsed skill.json content.
        skill_id: The folder name (e.g. SK-01) for context.
        all_skill_ids: Set of all known skill IDs, used to validate dependencies.

    Returns:
        List of error messages. Empty if valid.
    """
    errors: list[str] = []

    # Check required fields exist
    missing_fields = set(REQUIRED_FIELDS.keys()) - set(data.keys())
    if missing_fields:
        errors.append(f"  Missing required fields: {sorted(missing_fields)}")
        return errors  # Can't validate further without required fields

    # Validate field types
    for field, expected_type in REQUIRED_FIELDS.items():
        if not isinstance(data[field], expected_type):
            errors.append(
                f"  '{field}' must be {expected_type.__name__}, "
                f"got {type(data[field]).__name__}"
            )

    # Validate non-empty strings
    for field in ("id", "name", "description"):
        if isinstance(data.get(field), str) and not data[field].strip():
            errors.append(f"  '{field}' must not be empty")

    # Validate family
    if isinstance(data.get("family"), str) and data["family"] not in VALID_FAMILIES:
        errors.append(
            f"  Invalid family '{data['family']}'. "
            f"Valid: {sorted(VALID_FAMILIES)}"
        )

    # Validate layer matches family
    if data.get("family") in FAMILY_LAYERS and isinstance(data.get("layer"), int):
        valid_layers = FAMILY_LAYERS[data["family"]]
        if data["layer"] not in valid_layers:
            errors.append(
                f"  Invalid layer {data['layer']} for family '{data['family']}'. "
                f"Valid: {valid_layers}"
            )

    # Validate status
    if isinstance(data.get("status"), str) and data["status"] not in VALID_STATUSES:
        errors.append(
            f"  Invalid status '{data['status']}'. "
            f"Valid: {sorted(VALID_STATUSES)}"
        )

    # Validate data_requirements contains only strings
    if isinstance(data.get("data_requirements"), list):
        for i, item in enumerate(data["data_requirements"]):
            if not isinstance(item, str):
                errors.append(
                    f"  data_requirements[{i}] must be a string, "
                    f"got {type(item).__name__}"
                )

    # Validate dependencies contain only strings and reference existing skills
    if isinstance(data.get("dependencies"), list):
        for i, dep in enumerate(data["dependencies"]):
            if not isinstance(dep, str):
                errors.append(
                    f"  dependencies[{i}] must be a string, "
                    f"got {type(dep).__name__}"
                )
            elif dep not in all_skill_ids:
                errors.append(
                    f"  dependencies[{i}] references unknown skill '{dep}'"
                )

    return errors


def validate_skill_id_matches_folder(skill_id: str, folder_name: str) -> list[str]:
    """Validate that skill ID matches folder name."""
    if folder_name != skill_id:
        return [f"  Folder name '{folder_name}' does not match skill ID '{skill_id}'"]
    return []


def main() -> int:
    """Main validation function."""
    repo_root = Path(__file__).parent
    skill_dirs = sorted(repo_root.glob("SK-*/"))

    if not skill_dirs:
        print("ERROR: No skill directories found (expected SK-01/, SK-02/, etc.)")
        return 1

    print(f"Validating {len(skill_dirs)} skill manifests...\n")

    # First pass: collect all skill IDs for dependency validation
    all_skill_ids: set[str] = set()
    for skill_dir in skill_dirs:
        skill_json_path = skill_dir / "skill.json"
        if skill_json_path.exists():
            try:
                with open(skill_json_path) as f:
                    data = json.load(f)
                if isinstance(data.get("id"), str):
                    all_skill_ids.add(data["id"])
            except (json.JSONDecodeError, OSError):
                pass  # Will be caught in second pass

    # Second pass: full validation
    all_errors: list[str] = []
    valid_count = 0

    for skill_dir in skill_dirs:
        skill_json_path = skill_dir / "skill.json"
        folder_name = skill_dir.name

        if not skill_json_path.exists():
            print(f"FAIL {folder_name}: skill.json not found")
            all_errors.append(f"{folder_name}: skill.json not found")
            continue

        try:
            with open(skill_json_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"FAIL {folder_name}: Invalid JSON - {e}")
            all_errors.append(f"{folder_name}: Invalid JSON - {e}")
            continue

        schema_errors = validate_schema(data, folder_name, all_skill_ids)

        if "id" in data:
            id_errors = validate_skill_id_matches_folder(data["id"], folder_name)
            schema_errors.extend(id_errors)

        if schema_errors:
            print(f"FAIL {folder_name}:")
            for error in schema_errors:
                print(error)
            all_errors.extend(schema_errors)
        else:
            print(f"PASS {folder_name}")
            valid_count += 1

    print(f"\n{valid_count}/{len(skill_dirs)} skills passed validation")

    if all_errors:
        print(f"\nTotal errors: {len(all_errors)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
