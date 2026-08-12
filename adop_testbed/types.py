"""Shared data types for the ADOP MVP testbed.

`AuditLogRecord` mirrors the data contract published in
docs/LOG_SCHEMA.md (Section G.2 of the Final Project Notebook): timestamp,
session identifier, tool name, arguments, target resource, result status,
and scenario tag.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ScenarioTag = Literal["clean", "poisoned"]
ResultStatus = Literal["success", "error", "blocked"]
ServerName = Literal["filesystem", "git", "fetch", "memory"]
TaskCategory = Literal["issue_triage", "patch_drafting", "documentation_summarization"]


class AuditLogRecord(BaseModel):
    """One record in the frozen log corpus (JSON Lines, one object per line)."""

    timestamp: str = Field(description="ISO-8601 UTC timestamp of when the tool call completed.")
    session_id: str = Field(description="Identifier grouping every call made during one agent-host run.")
    server: ServerName = Field(description="MCP server that served the call.")
    tool_name: str = Field(description='Name of the tool invoked on that server (e.g. "git_diff").')
    arguments: dict[str, Any] = Field(description="Exact arguments passed to the tool, as received by the server.")
    target_resource: str = Field(description="Best-effort identification of the resource the call acted on.")
    result_status: ResultStatus = Field(description="Outcome of the call.")
    scenario_tag: ScenarioTag = Field(description="Whether this call happened during a clean or a poisoned run.")
    duration_ms: float = Field(description="Wall-clock duration of the call, in milliseconds.")
    result_summary: str = Field(description="Short human-readable summary of what happened, for triage.")
    task_id: str = Field(description="Task identifier from the fixed synthetic task set.")
    seq: int = Field(description="Sequence number of this call within the session, starting at 1.")
    annotations: list[str] = Field(
        default_factory=list,
        description=(
            "Optional teaching annotations describing which known weakness class, if any, this call "
            "exercised. Not part of the graded data contract; provided so the reference solutions in "
            "Section F have ground truth to validate their detectors against."
        ),
    )


class SyntheticTask(BaseModel):
    id: str
    scenario_tag: ScenarioTag
    category: TaskCategory
    title: str
    description: str
    instruction: str
