import json
from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.configure_external_scheduler import build_jobs, run_smoke_test, sync_jobs


def test_external_scheduler_jobs_match_prd_times_and_dispatch_inputs():
    jobs = build_jobs("github-token")

    assert [(job["schedule"]["hours"], job["schedule"]["minutes"]) for job in jobs] == [
        ([7], [45]),
        ([8], [15]),
    ]
    assert all(job["schedule"]["timezone"] == "Asia/Shanghai" for job in jobs)
    assert all(job["requestMethod"] == 1 for job in jobs)

    inputs = [json.loads(job["extendedData"]["body"])["inputs"] for job in jobs]
    assert inputs == [
        {
            "trigger_source": "external_scheduler",
            "schedule_slot": "primary",
            "force_push": "false",
            "push_test": "false",
        },
        {
            "trigger_source": "external_scheduler",
            "schedule_slot": "fallback",
            "force_push": "false",
            "push_test": "false",
        },
    ]
    assert all(
        job["extendedData"]["headers"]["Authorization"] == "Bearer github-token"
        for job in jobs
    )


def test_external_scheduler_sync_is_idempotent_and_verifies_both_jobs():
    stored = {}
    next_id = 1
    sleeps = []

    def fake_request(method, path, payload=None):
        nonlocal next_id
        if method == "GET" and path == "/jobs":
            return {
                "jobs": [
                    {"jobId": job_id, "title": job["title"]}
                    for job_id, job in stored.items()
                ]
            }
        if method == "PUT" and path == "/jobs":
            job_id = next_id
            next_id += 1
            stored[job_id] = payload["job"]
            return {"jobId": job_id}
        if method == "PATCH" and path.startswith("/jobs/"):
            job_id = int(path.rsplit("/", 1)[1])
            stored[job_id] = payload["job"]
            return {}
        if method == "GET" and path.startswith("/jobs/"):
            job_id = int(path.rsplit("/", 1)[1])
            details = {"jobId": job_id, **stored[job_id]}
            details["notification"] = {
                **details["notification"],
                "onSslCertExpiry": False,
                "onSslCertExpirySeconds": 604800,
            }
            return {"jobDetails": details}
        raise AssertionError((method, path))

    first = sync_jobs(
        "cron-key", "github-token", requester=fake_request, sleeper=sleeps.append
    )
    second = sync_jobs(
        "cron-key", "github-token", requester=fake_request, sleeper=sleeps.append
    )

    assert [item["title"] for item in first] == [
        "BigBeautyNews 07:45 primary",
        "BigBeautyNews 08:15 fallback",
    ]
    assert second == first
    assert len(stored) == 2
    assert sleeps == [1.1]


def test_temporary_external_trigger_is_removed_after_success():
    calls = []
    history_reads = 0

    def fake_request(method, path, payload=None):
        nonlocal history_reads
        calls.append((method, path))
        if method == "PUT":
            assert payload["job"]["saveResponses"] is True
            assert payload["job"]["schedule"] == {
                "timezone": "Asia/Shanghai",
                "expiresAt": 20260710100400,
                "hours": [10],
                "mdays": [10],
                "minutes": [3],
                "months": [7],
                "wdays": [-1],
            }
            return {"jobId": 99}
        if method == "GET" and path.endswith("/history"):
            history_reads += 1
            if history_reads == 1:
                return {"history": []}
            return {
                "history": [
                        {
                            "identifier": "99-smoke",
                            "status": 1,
                            "httpStatus": 200,
                        "date": 1783658581,
                        "datePlanned": 1783658580,
                        "jitter": 1000,
                    }
                ]
            }
        if method == "GET" and path.endswith("/history/99-smoke"):
            return {
                "jobHistoryDetails": {
                    "body": json.dumps(
                        {
                            "workflow_run_id": 123,
                            "html_url": "https://github.com/example/actions/runs/123",
                        }
                    )
                }
            }
        if method == "DELETE":
            return {}
        raise AssertionError((method, path))

    result = run_smoke_test(
        "cron-key",
        "github-token",
        requester=fake_request,
        now=datetime(2026, 7, 10, 10, 1, tzinfo=ZoneInfo("Asia/Shanghai")),
        sleeper=lambda _: None,
        max_polls=2,
    )

    assert result == {
        "httpStatus": 200,
        "status": 1,
        "date": 1783658581,
        "datePlanned": 1783658580,
        "jitter": 1000,
        "workflowRunId": 123,
        "workflowRunUrl": "https://github.com/example/actions/runs/123",
    }
    assert calls[-1] == ("DELETE", "/jobs/99")
