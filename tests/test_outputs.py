import json

from outputs.json_writer import (
    build_internal_digest,
    build_external_digest,
    archive_daily_json,
    load_recent_archive_items,
    update_history_index,
    validate_external_digest,
    validate_internal_digest,
)
from outputs.status import (
    build_run_status,
    mark_latest_run_committed,
    record_skipped_external_run,
    write_run_status,
)
from outputs.serverchan import build_markdown_message, push_to_wechat_with_result
from outputs.web_builder import write_web_data


def sample_items():
    return [
        {
            "rank": i + 1,
            "title": f"English {i}",
            "title_cn": f"中文标题{i}",
            "summary_cn": "中文摘要" * 25,
            "url": f"https://example.com/{i}",
            "source": "Example",
            "sourceTier": "tier2",
            "canonicalUrl": f"https://example.com/{i}",
            "eventId": f"event-{i}",
            "eventType": "model_release",
            "entities": ["OpenAI"],
            "tickers": [],
            "sourceCredibilityScore": 3,
            "marketImpactScore": 4,
            "noveltyScore": 5,
            "timelinessScore": 5,
            "entityImportanceScore": 4,
            "confidenceScore": 3,
            "totalScore": 4.25,
            "whyItMatters": "影响模型竞争。",
            "investmentImplication": "利好云厂商生态。",
            "riskNote": "",
            "relatedUrls": [],
            "primarySource": "Example",
            "warnings": [],
            "tags": ["大模型"],
        }
        for i in range(5)
    ]


def sample_geopolitics_items():
    return [
        {
            **item,
            "title": f"Geopolitics {index}",
            "title_cn": f"政经标题{index}",
            "url": f"https://example.com/geopolitics/{index}",
            "canonicalUrl": f"https://example.com/geopolitics/{index}",
            "eventId": f"geopolitics-event-{index}",
            "regions": ["china" if index < 2 else "us"],
            "geopoliticsEventTypes": ["policy"],
            "geopoliticsRuleScore": 4.0,
        }
        for index, item in enumerate(sample_items())
    ]


def test_output_schemas_keep_internal_fields_out_of_external_contract(tmp_path):
    internal = build_internal_digest(
        sample_items(),
        "模型竞争",
        geopolitics_items=sample_geopolitics_items(),
        geopolitics_theme="全球政策变化",
        date_str="2026-07-01",
        exported_at="2026-07-01T00:00:00Z",
    )
    external = build_external_digest(internal)
    archive_daily_json(internal, str(tmp_path / "archive"))
    write_web_data(internal, str(tmp_path / "web"))

    assert set(external["items"][0]) == {"date", "title", "summary", "url", "source"}
    assert internal["dailyTheme"] == "模型竞争"
    assert internal["geopoliticsTheme"] == "全球政策变化"
    assert len(internal["geopoliticsItems"]) == 5
    assert internal["items"][0]["rank"] == 1
    assert internal["items"][0]["published"] == ""
    assert internal["items"][0]["mergedSources"] == []
    assert internal["items"][0]["selectionReason"] == ""
    assert internal["items"][0]["eventId"] == "event-0"
    assert internal["items"][0]["sourceTier"] == "tier2"
    validate_external_digest(external)
    validate_internal_digest(internal)
    assert json.loads((tmp_path / "web" / "data.json").read_text("utf-8")) == internal


def test_schema_validation_rejects_bad_external_digest():
    bad = {"project": "daily-ai-5", "exportedAt": "now", "items": [{"title": "x"} for _ in range(5)]}

    try:
        validate_external_digest(bad)
    except ValueError as exc:
        assert "date" in str(exc)
    else:
        raise AssertionError("schema validation should reject missing fields")


def test_history_index_deduplicates_and_sorts_dates(tmp_path):
    path = tmp_path / "history.json"
    update_history_index(str(path), "2026-07-01")
    result = update_history_index(str(path), "2026-06-30")
    result = update_history_index(str(path), "2026-07-01")

    assert result["dates"] == ["2026-07-01", "2026-06-30"]


def test_recent_archive_loader_excludes_today_and_old_entries(tmp_path):
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    for date in ("2026-06-27", "2026-07-03", "2026-07-04", "2026-07-05"):
        (archive_dir / f"{date}.json").write_text(
            json.dumps({"items": [{"url": f"https://example.com/{date}"}]}),
            encoding="utf-8",
        )

    result = load_recent_archive_items(
        str(archive_dir),
        before_date="2026-07-05",
        days=7,
    )

    assert [item["url"] for item in result] == [
        "https://example.com/2026-07-03",
        "https://example.com/2026-07-04",
    ]


def test_archive_loader_reads_geopolitics_and_tolerates_legacy_files(tmp_path):
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    (archive_dir / "2026-07-03.json").write_text(
        json.dumps({"items": [{"url": "https://example.com/ai"}]}),
        encoding="utf-8",
    )
    (archive_dir / "2026-07-04.json").write_text(
        json.dumps({
            "items": [{"url": "https://example.com/ai-new"}],
            "geopoliticsItems": [{"url": "https://example.com/policy"}],
        }),
        encoding="utf-8",
    )

    result = load_recent_archive_items(
        str(archive_dir),
        before_date="2026-07-05",
        days=7,
        item_field="geopoliticsItems",
    )

    assert result == [{"url": "https://example.com/policy"}]


def test_run_status_files_capture_independent_state_flags(tmp_path):
    status = build_run_status(
        date_str="2026-07-05",
        status="partial",
        started_at="2026-07-04T23:45:00Z",
        finished_at="2026-07-04T23:46:00Z",
        candidate_count=10,
        selected_count=5,
        sources_available=3,
        llm_model="model",
        generated=True,
        pushed=False,
        committed=False,
        schema_valid=True,
        warnings=["Server酱推送失败"],
        errors=["push failed"],
    )

    write_run_status(status, str(tmp_path / "data"))

    current = json.loads((tmp_path / "data" / "run-status.json").read_text("utf-8"))
    history = json.loads((tmp_path / "data" / "run-history.json").read_text("utf-8"))
    error_log = json.loads((tmp_path / "data" / "error-log" / "2026-07-05.json").read_text("utf-8"))
    assert current["generated"] is True
    assert current["pushed"] is False
    assert history["runs"][0]["status"] == "partial"
    assert error_log["errors"] == ["push failed"]


def test_mark_latest_run_committed_updates_current_and_history(tmp_path):
    data_dir = tmp_path / "data"
    first_status = build_run_status(
        date_str="2026-07-04",
        status="success",
        started_at="2026-07-03T23:45:00Z",
        finished_at="2026-07-03T23:46:00Z",
        candidate_count=10,
        selected_count=5,
        sources_available=3,
        llm_model="model",
        generated=True,
        pushed=True,
        committed=True,
        schema_valid=True,
    )
    latest_status = build_run_status(
        date_str="2026-07-05",
        status="success",
        started_at="2026-07-04T23:45:00Z",
        finished_at="2026-07-04T23:46:00Z",
        candidate_count=10,
        selected_count=5,
        sources_available=3,
        llm_model="model",
        generated=True,
        pushed=True,
        committed=False,
        schema_valid=True,
    )
    write_run_status(first_status, str(data_dir))
    write_run_status(latest_status, str(data_dir))

    mark_latest_run_committed(str(data_dir))

    current = json.loads((data_dir / "run-status.json").read_text("utf-8"))
    history = json.loads((data_dir / "run-history.json").read_text("utf-8"))
    assert current["committed"] is True
    assert history["runs"][-1]["committed"] is True
    assert history["runs"][0]["date"] == "2026-07-04"


def test_skipped_external_fallback_is_recorded(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")

    record_skipped_external_run(str(tmp_path / "data"), "fallback")

    current = json.loads((tmp_path / "data" / "run-status.json").read_text("utf-8"))
    assert current["status"] == "skipped"
    assert current["trigger"] == "external_scheduler"
    assert current["scheduleSlot"] == "fallback"
    assert current["pushSkippedReason"] == "already_pushed"
    assert current["pushed"] is True
    assert current["workflowRunId"] == "12345"


def test_serverchan_message_contains_two_top_five_sections():
    title, markdown, plaintext = build_markdown_message(
        sample_items(),
        "2026-07-01",
        "模型竞争",
        geopolitics_items=sample_geopolitics_items(),
        geopolitics_theme="全球政策变化",
    )

    assert "2026-07-01" in title
    assert "每日 10 件事" in title
    assert markdown.count("[阅读原文]") == 10
    assert "一、AI 重要消息" in markdown
    assert "二、全球地缘与政经" in markdown
    assert "模型竞争" in plaintext
    assert "全球政策变化" in plaintext
    assert markdown.count("## 1.") == 2


def test_serverchan_push_result_captures_response_details(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = '{"code":0,"message":"ok","data":{"pushid":"123"}}'

        def json(self):
            return {"code": 0, "message": "ok", "data": {"pushid": "123"}}

    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr("outputs.serverchan.requests.post", fake_post)

    result = push_to_wechat_with_result(
        "SCT_TEST",
        sample_items(),
        "2026-07-01",
        "模型竞争",
        geopolitics_items=sample_geopolitics_items(),
        geopolitics_theme="全球政策变化",
    )

    assert result["ok"] is True
    assert result["pushAttempted"] is True
    assert result["sendkeyPresent"] is True
    assert result["serverchanEndpointType"] == "sct"
    assert result["pushHttpStatus"] == 200
    assert result["pushResponseCode"] == 0
    assert result["pushResponseMessage"] == "ok"
    assert result["pushId"] == "123"
    assert calls[0][1]["data"]["title"]
    assert calls[0][1]["data"]["desp"].count("[阅读原文]") == 10
