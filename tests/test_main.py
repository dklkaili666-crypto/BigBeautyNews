import json

import main


def test_pipeline_retries_failed_push_then_skips_duplicate_success(
    monkeypatch, tmp_path
):
    articles = [
        {
            "title": f"AI article {i}",
            "url": f"https://example.com/{i}",
            "source": "Example",
            "summary": "English summary",
        }
        for i in range(6)
    ]
    geopolitics_articles = [
        {
            "title": f"United States central bank interest rate policy {i}",
            "url": f"https://policy.example.com/{i}",
            "source": "NPR Politics",
            "summary": "Federal Reserve policy affects inflation and economic growth.",
        }
        for i in range(6)
    ]

    def fetch_sources(sources):
        if sources and sources[0]["name"] == "SCMP China":
            return geopolitics_articles, []
        return articles, []

    monkeypatch.setattr(main, "fetch_all_sources", fetch_sources)
    monkeypatch.setattr(main, "fetch_trending", lambda: [])
    monkeypatch.setattr(main, "fetch_hn_top_ai", lambda: [])
    monkeypatch.setattr(main, "dedup_candidates", lambda values: values)
    monkeypatch.setattr(main, "filter_ai_related", lambda values: values)
    monkeypatch.setattr(main, "filter_geopolitics_related", lambda values: values)
    monkeypatch.setattr(
        main,
        "call_llm_ranking",
        lambda *args, **kwargs: {
            "top5": [
                {"source_article_index": i, "reason": "重要", "tags": ["AI"]}
                for i in range(5)
            ],
            "daily_theme": "模型竞争",
        },
    )
    monkeypatch.setattr(
        main,
        "call_geopolitics_ranking",
        lambda *args, **kwargs: {
            "top5": [
                {"source_article_index": i, "reason": "重要", "tags": ["政经"]}
                for i in range(5)
            ],
            "geopolitics_theme": "全球政策",
        },
    )
    monkeypatch.setattr(
        main,
        "translate_top5",
        lambda values, *args: [
            {**item, "title_cn": f"中文标题{i}", "summary_cn": "中文摘要" * 25}
            for i, item in enumerate(values)
        ],
    )
    monkeypatch.setattr(
        main,
        "translate_geopolitics_top5",
        lambda values, *args: [
            {**item, "title_cn": f"政经标题{i}", "summary_cn": "政经摘要" * 25}
            for i, item in enumerate(values)
        ],
    )
    push_calls = []
    push_results = iter([False, True, True])

    def push_with_results(*args, **kwargs):
        push_calls.append((args, kwargs))
        ok = next(push_results)
        return {
            "ok": ok,
            "pushAttempted": True,
            "pushHttpStatus": 200,
            "pushResponseCode": 0 if ok else 1,
            "pushResponseMessage": "" if ok else "failed",
            "pushResponseBodyPreview": "{}",
            "sendkeyPresent": True,
            "serverchanEndpointType": "sct",
            "pushId": "push-1" if ok else "",
        }

    monkeypatch.setattr(main, "push_to_wechat_with_result", push_with_results)
    monkeypatch.setattr(main, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(main, "DAILY_JSON_PATH", str(tmp_path / "data" / "daily-5-things.json"))
    monkeypatch.setattr(main, "HISTORY_JSON_PATH", str(tmp_path / "data" / "history.json"))
    monkeypatch.setattr(main, "ARCHIVE_DIR", str(tmp_path / "data" / "archive"))
    monkeypatch.setattr(main, "WEB_DIR", str(tmp_path / "web"))
    monkeypatch.setattr(main, "PUSH_HISTORY_PATH", str(tmp_path / "data" / "push-history.json"))
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BIGBEAUTYNEWS_TRIGGER", "external_scheduler")
    monkeypatch.setenv("BIGBEAUTYNEWS_SCHEDULE_SLOT", "primary")

    result = main.run_pipeline()
    second_result = main.run_pipeline()
    third_result = main.run_pipeline()
    forced_result = main.run_pipeline(force_push=True)

    external = json.loads((tmp_path / "data" / "daily-5-things.json").read_text("utf-8"))
    internal = json.loads((tmp_path / "web" / "data.json").read_text("utf-8"))
    assert result["status"] == "error"
    assert result["reason"] == "Server酱推送失败"
    assert second_result["status"] == "ok"
    assert third_result["status"] == "ok"
    assert forced_result["status"] == "ok"
    assert len(push_calls) == 3
    assert len(push_calls[0][1]["geopolitics_items"]) == 5
    assert set(external["items"][0]) == {"date", "title", "summary", "url", "source"}
    assert internal["dailyTheme"] == "模型竞争"
    assert internal["geopoliticsTheme"] == "全球政策"
    assert len(internal["geopoliticsItems"]) == 5
    assert internal["items"][0]["tags"] == ["AI"]
    first_status = json.loads((tmp_path / "data" / "run-history.json").read_text("utf-8"))["runs"][0]
    latest_status = json.loads((tmp_path / "data" / "run-status.json").read_text("utf-8"))
    assert first_status["status"] == "partial"
    assert first_status["generated"] is True
    assert first_status["pushed"] is False
    assert latest_status["status"] == "success"
    assert latest_status["committed"] is False
    assert latest_status["pushAttempted"] is True
    assert latest_status["pushHttpStatus"] == 200
    assert latest_status["pushResponseCode"] == 0
    assert latest_status["trigger"] == "external_scheduler"
    assert latest_status["scheduleSlot"] == "primary"
    assert latest_status["aiSelectedCount"] == 5
    assert latest_status["geopoliticsSelectedCount"] == 5
    assert latest_status["digestHash"]


def test_pipeline_does_not_push_when_geopolitics_candidates_are_insufficient(
    monkeypatch, tmp_path
):
    ai_articles = [
        {
            "title": f"OpenAI model release {i}",
            "url": f"https://ai.example.com/{i}",
            "source": "TechCrunch",
            "summary": "New AI model benchmark.",
        }
        for i in range(6)
    ]
    geopolitics_articles = [
        {
            "title": "Federal Reserve interest rate policy",
            "url": "https://policy.example.com/1",
            "source": "NPR Politics",
            "summary": "United States inflation policy.",
        }
    ]

    monkeypatch.setattr(
        main,
        "fetch_all_sources",
        lambda sources: (
            (geopolitics_articles if sources and sources[0]["name"] == "SCMP China" else ai_articles),
            [],
        ),
    )
    monkeypatch.setattr(main, "fetch_trending", lambda: [])
    monkeypatch.setattr(main, "fetch_hn_top_ai", lambda: [])
    monkeypatch.setattr(main, "dedup_candidates", lambda values: values)
    monkeypatch.setattr(main, "filter_ai_related", lambda values: values)
    monkeypatch.setattr(main, "filter_geopolitics_related", lambda values: values)
    push_calls = []
    monkeypatch.setattr(
        main,
        "push_to_wechat_with_result",
        lambda *args: push_calls.append(args),
    )
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(main, "ARCHIVE_DIR", str(tmp_path / "data" / "archive"))

    result = main.run_pipeline()

    assert result["status"] == "error"
    assert "政经 1 篇" in result["reason"]
    assert push_calls == []
    status = json.loads((tmp_path / "data" / "run-status.json").read_text("utf-8"))
    assert status["geopoliticsCandidateCount"] == 1
    assert status["pushed"] is False


def test_cross_board_duplicate_is_replaced_from_dominant_board_pool():
    duplicate_ai = {
        "title": "US AI chip export controls on China",
        "url": "https://example.com/export",
        "rank": 1,
    }
    ai_selected = [duplicate_ai] + [
        {"title": f"AI {i}", "url": f"https://ai/{i}", "rank": i + 1}
        for i in range(1, 5)
    ]
    geopolitics_selected = [
        {**duplicate_ai, "summary": "United States tariff and export control policy"}
    ] + [
        {"title": f"Policy {i}", "url": f"https://policy/{i}", "rank": i + 1}
        for i in range(1, 5)
    ]
    ai_candidates = [
        *ai_selected,
        {
            "title": "OpenAI launches a new reasoning model",
            "summary": "AI benchmark improvement",
            "url": "https://ai/replacement",
            "totalScore": 5,
        },
    ]

    ai_result, geopolitics_result = main.resolve_cross_board_duplicates(
        ai_selected,
        geopolitics_selected,
        ai_candidates,
        geopolitics_selected,
    )

    assert ai_result[0]["url"] == "https://ai/replacement"
    assert geopolitics_result[0]["url"] == "https://example.com/export"
