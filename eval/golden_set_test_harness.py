#!/usr/bin/env python3
"""
Golden Set Test Harness for TPM-Skills.

Loads all skill.json files, validates them using the shared validator,
and reports comprehensive pass/fail results for each skill.
"""

import json
import sys
from pathlib import Path

# Import shared validation logic — single source of truth
sys.path.insert(0, str(Path(__file__).parent.parent))
from validate_manifests import VALID_FAMILIES, FAMILY_LAYERS, VALID_STATUSES, validate_schema  # noqa: E402


class GoldenSetHarness:
    """Run golden-set validation on all skill manifests."""

    def __init__(self) -> None:
        self.results: list[dict] = []
        self.passed = 0
        self.failed = 0

    def test_skill(self, skill_path: Path, all_skill_ids: set[str]) -> dict:
        """Test a single skill.json file."""
        skill_name = skill_path.parent.name
        result: dict = {
            "skill": skill_name,
            "path": str(skill_path),
            "passed": False,
            "errors": [],
        }

        if not skill_path.exists():
            result["errors"].append("skill.json file not found")
            self.results.append(result)
            self.failed += 1
            return result

        try:
            with open(skill_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid JSON: {e}")
            self.results.append(result)
            self.failed += 1
            return result

        # Use shared validator
        errors = validate_schema(data, skill_name, all_skill_ids)

        # Additional check: ID matches folder name
        if "id" in data and data["id"] != skill_name:
            errors.append(
                f"  'id' value '{data['id']}' does not match folder '{skill_name}'"
            )

        if errors:
            result["errors"] = errors
            self.failed += 1
        else:
            result["passed"] = True
            result["data"] = data
            self.passed += 1

        self.results.append(result)
        return result

    def run(self, repo_root: Path) -> bool:
        """Run validation on all skills in the repository."""
        skill_dirs = sorted(repo_root.glob("SK-*/"))

        if not skill_dirs:
            print("ERROR: No skill directories found (expected SK-01/, SK-02/, etc.)")
            return False

        print(f"Golden Set Test Harness - Loading {len(skill_dirs)} skills...\n")

        # Collect all skill IDs first for dependency validation
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
                    pass

        # Validate each skill
        for skill_dir in skill_dirs:
            self.test_skill(skill_dir / "skill.json", all_skill_ids)

        return self.report()

    def report(self) -> bool:
        """Report test results."""
        total = self.passed + self.failed

        print("=" * 70)
        print("TEST RESULTS")
        print("=" * 70)

        for result in self.results:
            status = "PASS" if result["passed"] else "FAIL"
            print(f"\n{status}: {result['skill']}")
            if result["errors"]:
                for error in result["errors"]:
                    print(f"  - {error}")
            else:
                data = result.get("data", {})
                print(f"  Name: {data.get('name', 'N/A')}")
                print(f"  Family: {data.get('family', 'N/A')}")
                print(f"  Layer: {data.get('layer', 'N/A')}")
                print(f"  Has Tool: {data.get('has_tool', False)}")
                deps = data.get("dependencies", [])
                if deps:
                    print(f"  Dependencies: {', '.join(deps)}")

        print("\n" + "=" * 70)
        print(f"SUMMARY: {self.passed}/{total} skills passed")
        print("=" * 70)

        return self.failed == 0


def main() -> int:
    """Main test harness entry point."""
    repo_root = Path(__file__).parent.parent
    harness = GoldenSetHarness()
    success = harness.run(repo_root)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
