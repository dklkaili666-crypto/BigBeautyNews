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
    monkeypatch.setattr(main, "fetch_all_sources", lambda sources: (articles, []))
    monkeypatch.setattr(main, "fetch_trending", lambda: [])
    monkeypatch.setattr(main, "fetch_hn_top_ai", lambda: [])
    monkeypatch.setattr(main, "dedup_candidates", lambda values: values)
    monkeypatch.setattr(main, "filter_ai_related", lambda values: values)
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
        "translate_top5",
        lambda values, *args: [
            {**item, "title_cn": f"中文标题{i}", "summary_cn": "中文摘要" * 25}
            for i, item in enumerate(values)
        ],
    )
    push_calls = []
    push_results = iter([False, True, True])

    def push_with_results(*args):
        push_calls.append(args)
        return next(push_results)

    monkeypatch.setattr(main, "push_to_wechat", push_with_results)
    monkeypatch.setattr(main, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(main, "DAILY_JSON_PATH", str(tmp_path / "data" / "daily-5-things.json"))
    monkeypatch.setattr(main, "HISTORY_JSON_PATH", str(tmp_path / "data" / "history.json"))
    monkeypatch.setattr(main, "ARCHIVE_DIR", str(tmp_path / "data" / "archive"))
    monkeypatch.setattr(main, "WEB_DIR", str(tmp_path / "web"))
    monkeypatch.setattr(main, "PUSH_HISTORY_PATH", str(tmp_path / "data" / "push-history.json"))
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path / "data"))

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
    assert set(external["items"][0]) == {"date", "title", "summary", "url", "source"}
    assert internal["dailyTheme"] == "模型竞争"
    assert internal["items"][0]["tags"] == ["AI"]
    first_status = json.loads((tmp_path / "data" / "run-history.json").read_text("utf-8"))["runs"][0]
    latest_status = json.loads((tmp_path / "data" / "run-status.json").read_text("utf-8"))
    assert first_status["status"] == "partial"
    assert first_status["generated"] is True
    assert first_status["pushed"] is False
    assert latest_status["status"] == "success"
    assert latest_status["committed"] is False
