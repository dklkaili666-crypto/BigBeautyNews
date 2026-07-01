import json

import main


def test_pipeline_writes_external_and_internal_outputs_and_ignores_push_failure(
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
    monkeypatch.setattr(main, "push_to_wechat", lambda *args: False)
    monkeypatch.setattr(main, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(main, "DAILY_JSON_PATH", str(tmp_path / "data" / "daily-5-things.json"))
    monkeypatch.setattr(main, "HISTORY_JSON_PATH", str(tmp_path / "data" / "history.json"))
    monkeypatch.setattr(main, "ARCHIVE_DIR", str(tmp_path / "data" / "archive"))
    monkeypatch.setattr(main, "WEB_DIR", str(tmp_path / "web"))

    result = main.run_pipeline()

    external = json.loads((tmp_path / "data" / "daily-5-things.json").read_text("utf-8"))
    internal = json.loads((tmp_path / "web" / "data.json").read_text("utf-8"))
    assert result["status"] == "ok"
    assert set(external["items"][0]) == {"date", "title", "summary", "url", "source"}
    assert internal["dailyTheme"] == "模型竞争"
    assert internal["items"][0]["tags"] == ["AI"]
