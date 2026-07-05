import json
from types import SimpleNamespace

from pipeline import ranker, translator


class FakeCompletions:
    def __init__(self, contents):
        self.contents = iter(contents)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=next(self.contents)))]
        )


def fake_client(contents):
    completions = FakeCompletions(contents)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


def test_ranking_retries_invalid_json_and_selects_unique_articles(monkeypatch):
    payload = {
        "top5": [
            {"rank": i + 1, "source_article_index": i, "reason": f"reason {i}", "tags": ["AI"]}
            for i in range(5)
        ],
        "daily_theme": "模型竞争",
    }
    client, completions = fake_client(["not-json", json.dumps(payload)])
    monkeypatch.setattr(ranker, "OpenAI", lambda **kwargs: client)
    articles = [{"title": f"Article {i}", "url": f"https://{i}", "source": "X"} for i in range(6)]

    ranking = ranker.call_llm_ranking(articles, "key", "https://api", "model")
    selected = ranker.select_top5(articles, ranking)

    assert completions.calls == 2
    assert [item["rank"] for item in selected] == [1, 2, 3, 4, 5]
    assert selected[0]["tags"] == ["AI"]


def test_ranking_retries_when_top_five_are_dominated_by_one_source(monkeypatch):
    concentrated = {
        "top5": [
            {"rank": i + 1, "source_article_index": i, "reason": "重要", "tags": ["AI"]}
            for i in range(5)
        ],
        "daily_theme": "模型竞争",
    }
    diversified_indices = [0, 1, 5, 6, 8]
    diversified = {
        "top5": [
            {"rank": i + 1, "source_article_index": index, "reason": "重要", "tags": ["AI"]}
            for i, index in enumerate(diversified_indices)
        ],
        "daily_theme": "模型竞争",
    }
    client, completions = fake_client([
        json.dumps(concentrated),
        json.dumps(diversified),
    ])
    monkeypatch.setattr(ranker, "OpenAI", lambda **kwargs: client)
    articles = [
        *[{"title": f"TC {i}", "url": f"https://tc/{i}", "source": "TechCrunch"} for i in range(5)],
        *[{"title": f"Wired {i}", "url": f"https://wired/{i}", "source": "Wired"} for i in range(3)],
        *[{"title": f"Verge {i}", "url": f"https://verge/{i}", "source": "The Verge"} for i in range(2)],
    ]

    result = ranker.call_llm_ranking(articles, "key", "https://api", "model")

    assert completions.calls == 2
    assert [item["source_article_index"] for item in result["top5"]] == diversified_indices


def test_ranking_warns_when_retry_still_violates_source_diversity(monkeypatch):
    concentrated = {
        "top5": [
            {"rank": i + 1, "source_article_index": i, "reason": "重要", "tags": ["AI"]}
            for i in range(5)
        ],
        "daily_theme": "模型竞争",
    }
    client, completions = fake_client([
        json.dumps(concentrated),
        json.dumps(concentrated),
    ])
    monkeypatch.setattr(ranker, "OpenAI", lambda **kwargs: client)
    articles = [
        *[{"title": f"TC {i}", "url": f"https://tc/{i}", "source": "TechCrunch"} for i in range(5)],
        *[{"title": f"Wired {i}", "url": f"https://wired/{i}", "source": "Wired"} for i in range(3)],
        *[{"title": f"Verge {i}", "url": f"https://verge/{i}", "source": "The Verge"} for i in range(2)],
    ]

    result = ranker.call_llm_ranking(articles, "key", "https://api", "model")

    assert completions.calls == 2
    assert result["warnings"] == ["Top 5 来源过度集中: {'TechCrunch': 5}"]


def test_translation_accepts_near_target_summary_and_preserves_metadata(monkeypatch, caplog):
    translated = {
        "items": [
            {"rank": i + 1, "title_cn": f"标题{i}", "summary_cn": "摘要" * 40}
            for i in range(5)
        ]
    }
    client, _ = fake_client([json.dumps(translated, ensure_ascii=False)])
    monkeypatch.setattr(translator, "OpenAI", lambda **kwargs: client)
    top5 = [
        {
            "rank": i + 1,
            "title": f"English {i}",
            "url": f"https://trusted/{i}",
            "source": "Trusted",
            "tags": ["AI"],
        }
        for i in range(5)
    ]

    result = translator.translate_top5(top5, "key", "https://api", "model")

    assert result[0]["url"] == "https://trusted/0"
    assert result[0]["source"] == "Trusted"
    assert result[0]["originalTitle"] == "English 0"
    assert "建议范围" in caplog.text
