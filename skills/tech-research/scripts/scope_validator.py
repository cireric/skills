from __future__ import annotations


_VALID_GOAL_TYPES: set[str] = {
    "panoramic_understanding",
    "tech_selection",
    "feasibility_assessment",
    "competitive_comparison",
    "exploratory",
}
_VALID_AUDIENCES: set[str] = {"myself", "team_sharing", "decision_maker"}
_VALID_TIME_CONSTRAINTS: set[str] = {"hours", "days", "weeks"}
_VALID_QUALITY_STANDARDS: set[str] = {"3_sources", "demo_poc", "comparison_matrix"}


def validate_scope(data: dict) -> list[str]:
    errors: list[str] = []
    if "topic" not in data or not data["topic"]:
        errors.append("Missing required field: topic")
    std = data.get("standardized", {})
    if not std:
        errors.append("Missing required field: standardized")
        return errors
    goal = std.get("goal_type", "")
    if goal not in _VALID_GOAL_TYPES:
        errors.append(f"Invalid goal_type: {goal!r}. Must be one of {sorted(_VALID_GOAL_TYPES)}")
    audience = std.get("audience", "")
    if audience not in _VALID_AUDIENCES:
        errors.append(f"Invalid audience: {audience!r}. Must be one of {sorted(_VALID_AUDIENCES)}")
    time_constraint = std.get("time_constraint", "")
    if time_constraint not in _VALID_TIME_CONSTRAINTS:
        errors.append(
            f"Invalid time_constraint: {time_constraint!r}. "
            f"Must be one of {sorted(_VALID_TIME_CONSTRAINTS)}"
        )
    quality = std.get("quality_standard", "")
    if quality and quality not in _VALID_QUALITY_STANDARDS:
        errors.append(
            f"Invalid quality_standard: {quality!r}. "
            f"Must be one of {sorted(_VALID_QUALITY_STANDARDS)}"
        )
    if goal == "tech_selection" and not std.get("candidates"):
        errors.append("tech_selection requires 'candidates' field")
    if goal == "competitive_comparison" and not std.get("comparison_dimensions"):
        errors.append("competitive_comparison requires 'comparison_dimensions' field")
    if goal == "feasibility_assessment" and not std.get("technology"):
        errors.append("feasibility_assessment requires 'technology' field")
    return errors
