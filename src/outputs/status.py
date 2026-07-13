"""运行状态文件输出。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import json
import os
from zoneinfo import ZoneInfo


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_run_status(
    *,
    date_str: str,
    status: str,
    started_at: str,
    finished_at: str,
    candidate_count: int,
    selected_count: int,
    sources_available: int,
    llm_model: str,
    generated: bool,
    pushed: bool,
    committed: bool,
    schema_valid: bool,
    geopolitics_candidate_count: int = 0,
    geopolitics_selected_count: int = 0,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status_doc = {
        "date": date_str,
        "status": status,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "candidateCount": candidate_count,
        "selectedCount": selected_count,
        "aiCandidateCount": candidate_count,
        "aiSelectedCount": selected_count,
        "geopoliticsCandidateCount": geopolitics_candidate_count,
        "geopoliticsSelectedCount": geopolitics_selected_count,
        "sourcesAvailable": sources_available,
        "llmModel": llm_model,
        "generated": generated,
        "pushed": pushed,
        "committed": committed,
        "schemaValid": schema_valid,
        "warnings": list(warnings or []),
        "errors": list(errors or []),
    }
    status_doc.update(extra or {})
    return status_doc


def write_run_status(status: dict[str, Any], data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    status_path = os.path.join(data_dir, "run-status.json")
    history_path = os.path.join(data_dir, "run-history.json")
    with open(status_path, "w", encoding="utf-8") as file:
        json.dump(status, file, ensure_ascii=False, indent=2)

    history: dict[str, Any] = {"runs": []}
    if os.path.exists(history_path):
        try:
            with open(history_path, encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, dict):
                history = loaded
        except (OSError, json.JSONDecodeError):
            history = {"runs": []}
    loaded_runs = history.get("runs")
    runs: list[dict[str, Any]] = (
        [run for run in loaded_runs if isinstance(run, dict)]
        if isinstance(loaded_runs, list)
        else []
    )
    runs.append(status)
    history = {"runs": runs[-30:]}
    with open(history_path, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)

    if status.get("status") in {"failed", "partial"}:
        error_dir = os.path.join(data_dir, "error-log")
        os.makedirs(error_dir, exist_ok=True)
        error_path = os.path.join(error_dir, f"{status.get('date')}.json")
        with open(error_path, "w", encoding="utf-8") as file:
            json.dump(status, file, ensure_ascii=False, indent=2)


def record_skipped_external_run(data_dir: str, schedule_slot: str) -> None:
    """Record an external scheduler run skipped after an earlier successful push."""
    timestamp = utc_now()
    status = build_run_status(
        date_str=datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d"),
        status="skipped",
        started_at=timestamp,
        finished_at=timestamp,
        candidate_count=0,
        selected_count=0,
        sources_available=0,
        llm_model="",
        generated=False,
        pushed=True,
        committed=False,
        schema_valid=True,
        extra={
            "trigger": "external_scheduler",
            "scheduleSlot": schedule_slot,
            "workflowRunId": os.getenv("GITHUB_RUN_ID", ""),
            "pushAttempted": False,
            "pushSkippedReason": "already_pushed",
        },
    )
    write_run_status(status, data_dir)


def mark_latest_run_committed(data_dir: str) -> None:
    """Mark the latest status as committed immediately before the workflow commits data."""
    status_path = os.path.join(data_dir, "run-status.json")
    history_path = os.path.join(data_dir, "run-history.json")

    with open(status_path, encoding="utf-8") as file:
        status = json.load(file)
    if isinstance(status, dict):
        status["committed"] = True
    with open(status_path, "w", encoding="utf-8") as file:
        json.dump(status, file, ensure_ascii=False, indent=2)

    if not os.path.exists(history_path):
        return
    with open(history_path, encoding="utf-8") as file:
        history = json.load(file)
    runs = history.get("runs") if isinstance(history, dict) else None
    if not isinstance(runs, list) or not runs:
        return
    if isinstance(runs[-1], dict):
        runs[-1]["committed"] = True
    with open(history_path, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
