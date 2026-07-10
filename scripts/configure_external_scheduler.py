#!/usr/bin/env python3
"""Configure the two cron-job.org triggers required by PRD OPS-01."""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections.abc import Callable
from datetime import datetime, timedelta
from getpass import getpass
from time import sleep
from urllib import error, request
from zoneinfo import ZoneInfo


WORKFLOW_DISPATCH_URL = (
    "https://api.github.com/repos/dklkaili666-crypto/BigBeautyNews/"
    "actions/workflows/daily.yml/dispatches"
)
CRON_REQUEST_POST = 1
CRON_STATUS_OK = 1
EVERY = -1


def build_jobs(github_token: str) -> list[dict]:
    jobs = []
    for slot, hour, minute in (("primary", 7, 45), ("fallback", 8, 15)):
        body = json.dumps(
            {
                "ref": "master",
                "inputs": {
                    "trigger_source": "external_scheduler",
                    "schedule_slot": slot,
                    "force_push": "false",
                    "push_test": "false",
                },
            },
            separators=(",", ":"),
        )
        jobs.append(
            {
                "title": f"BigBeautyNews {hour:02d}:{minute:02d} {slot}",
                "url": WORKFLOW_DISPATCH_URL,
                "enabled": True,
                "saveResponses": False,
                "requestMethod": CRON_REQUEST_POST,
                "requestTimeout": 30,
                "schedule": {
                    "timezone": "Asia/Shanghai",
                    "expiresAt": 0,
                    "hours": [hour],
                    "mdays": [EVERY],
                    "minutes": [minute],
                    "months": [EVERY],
                    "wdays": [EVERY],
                },
                "extendedData": {
                    "headers": {
                        "Accept": "application/vnd.github+json",
                        "Authorization": f"Bearer {github_token}",
                        "Content-Type": "application/json",
                        "X-GitHub-Api-Version": "2026-03-10",
                    },
                    "body": body,
                },
                "notification": {
                    "onFailure": True,
                    "onFailureCount": 1,
                    "onSuccess": True,
                    "onDisable": True,
                },
            }
        )
    return jobs


def _cron_requester(api_key: str) -> Callable[[str, str, dict | None], dict]:
    def send(method: str, path: str, payload: dict | None = None) -> dict:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"https://api.cron-job.org{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except error.HTTPError as exc:
            raise RuntimeError(
                f"cron-job.org API {method} {path} failed with HTTP {exc.code}"
            ) from exc

    return send


def sync_jobs(
    cron_api_key: str,
    github_token: str,
    requester: Callable[[str, str, dict | None], dict] | None = None,
    sleeper: Callable[[float], None] = sleep,
) -> list[dict]:
    send = requester or _cron_requester(cron_api_key)
    expected_jobs = build_jobs(github_token)
    existing = {
        item["title"]: item["jobId"]
        for item in send("GET", "/jobs").get("jobs", [])
        if item.get("title")
    }
    verified = []
    created_job = False

    for expected in expected_jobs:
        job_id = existing.get(expected["title"])
        if job_id is None:
            if created_job:
                sleeper(1.1)
            job_id = send("PUT", "/jobs", {"job": expected})["jobId"]
            created_job = True
        else:
            send("PATCH", f"/jobs/{job_id}", {"job": expected})

        actual = send("GET", f"/jobs/{job_id}")["jobDetails"]
        schedule_matches = all(
            actual.get("schedule", {}).get(key) == value
            for key, value in expected["schedule"].items()
        )
        request_matches = all(
            actual.get(key) == expected[key]
            for key in ("title", "url", "enabled", "requestMethod")
        ) and actual.get("extendedData", {}).get("body") == expected["extendedData"][
            "body"
        ]
        if not schedule_matches or not request_matches:
            raise RuntimeError(f"cron job verification failed: {expected['title']}")
        verified.append(
            {
                "jobId": job_id,
                "title": actual["title"],
                "enabled": actual["enabled"],
                "timezone": actual["schedule"]["timezone"],
                "hours": actual["schedule"]["hours"],
                "minutes": actual["schedule"]["minutes"],
            }
        )

    return verified


def _build_smoke_job(github_token: str, now: datetime | None = None) -> dict:
    current = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    target = current.replace(second=0, microsecond=0) + timedelta(minutes=2)
    expires = target + timedelta(minutes=1)
    job = copy.deepcopy(build_jobs(github_token)[1])
    job["title"] = f"BigBeautyNews OPS-01 smoke {target:%Y%m%d%H%M}"
    job["saveResponses"] = True
    job["notification"] = {
        "onFailure": False,
        "onFailureCount": 1,
        "onSuccess": False,
        "onDisable": False,
    }
    job["schedule"] = {
        "timezone": "Asia/Shanghai",
        "expiresAt": int(expires.strftime("%Y%m%d%H%M%S")),
        "hours": [target.hour],
        "mdays": [target.day],
        "minutes": [target.minute],
        "months": [target.month],
        "wdays": [EVERY],
    }
    return job


def run_smoke_test(
    cron_api_key: str,
    github_token: str,
    requester: Callable[[str, str, dict | None], dict] | None = None,
    now: datetime | None = None,
    sleeper: Callable[[float], None] = sleep,
    max_polls: int = 18,
) -> dict:
    send = requester or _cron_requester(cron_api_key)
    job_id = send("PUT", "/jobs", {"job": _build_smoke_job(github_token, now)})[
        "jobId"
    ]
    try:
        for _ in range(max_polls):
            sleeper(10)
            history = send("GET", f"/jobs/{job_id}/history").get("history", [])
            if not history:
                continue
            latest = history[0]
            if latest.get("status") != CRON_STATUS_OK or latest.get(
                "httpStatus"
            ) != 200:
                raise RuntimeError(
                    "temporary external trigger failed: "
                    f"status={latest.get('status')} http={latest.get('httpStatus')}"
                )
            identifier = latest.get("identifier", "")
            details = send("GET", f"/jobs/{job_id}/history/{identifier}").get(
                "jobHistoryDetails", {}
            )
            try:
                github_response = json.loads(details.get("body") or "{}")
            except json.JSONDecodeError as exc:
                raise RuntimeError("GitHub dispatch response was not valid JSON") from exc
            workflow_run_id = github_response.get("workflow_run_id")
            workflow_run_url = github_response.get("html_url")
            if not workflow_run_id or not workflow_run_url:
                raise RuntimeError("GitHub dispatch did not return a workflow run")
            return {
                "httpStatus": latest["httpStatus"],
                "status": latest["status"],
                "date": latest.get("date"),
                "datePlanned": latest.get("datePlanned"),
                "jitter": latest.get("jitter"),
                "workflowRunId": workflow_run_id,
                "workflowRunUrl": workflow_run_url,
            }
        raise RuntimeError("temporary external trigger did not run within 3 minutes")
    finally:
        send("DELETE", f"/jobs/{job_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    github_token = os.getenv("GITHUB_ACTIONS_TOKEN", "")
    if not github_token:
        print("Create a fine-grained token: https://github.com/settings/personal-access-tokens/new")
        github_token = getpass("GitHub token (BigBeautyNews, Actions write only): ")
    cron_api_key = os.getenv("CRON_JOB_API_KEY", "")
    if not cron_api_key:
        print("Create an API key: https://console.cron-job.org/settings")
        cron_api_key = getpass("cron-job.org API key: ")
    if not cron_api_key or not github_token:
        print("Both keys are required", file=sys.stderr)
        return 2

    result = (
        run_smoke_test(cron_api_key, github_token)
        if args.smoke
        else sync_jobs(cron_api_key, github_token)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
