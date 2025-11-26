"""Schema linter for Phase W (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict, Any, List


def lint_schemas(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lint collected schemas across phases.

    Returns:
    {
      "valid": bool,
      "errors": [ { "phase": str, "field": str, "issue": str } ],
      "warnings": [ { "phase": str, "field": str, "issue": str } ],
      "summary": str
    }
    """
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    if not isinstance(inputs, dict):
        return {
            "valid": False,
            "errors": [{"phase": "all", "field": "", "issue": "inputs_not_dict"}],
            "warnings": [],
            "summary": "Invalid inputs",
        }

    for phase, payload in inputs.items():
        if not isinstance(payload, dict):
            warnings.append({"phase": phase, "field": "", "issue": "missing_or_not_dict"})
            continue
        # Simple lint: check a few common fields
        for field, value in payload.items():
            if value is None:
                warnings.append({"phase": phase, "field": field, "issue": "missing_value"})
            elif isinstance(value, (int, float, str, bool, list, dict)):
                continue
            else:
                errors.append({"phase": phase, "field": field, "issue": "invalid_type"})
        # If minimal expected fields absent, warn
        if not payload:
            warnings.append({"phase": phase, "field": "", "issue": "empty_payload"})

    valid = len(errors) == 0
    summary = "Schemas linted successfully" if valid else "Schema linting found errors"
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }
