import json
from types import SimpleNamespace

from pipeline import geopolitics_ranker, translator


class FakeCompletions:
    def __init__(self, contents):
        self.contents = iter(contents)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=next(self.contents)))]
        )


def fake_client(contents):
    completions = FakeCompletions(contents)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def article(index, source, regions):
    return {
        "title": f"Policy event {index}",
        "url": f"https://example.com/{index}",
        "source": source,
        "regions": regions,
        "summary": "Major policy event with market impact.",
    }


def ranking(indices):
    return {
        "top5": [
            {"rank": rank, "source_article_index": index, "reason": "重要", "tags": ["政经"]}
            for rank, index in enumerate(indices, start=1)
        ],
        "geopolitics_theme": "全球政策变化",
    }


def test_geopolitics_ranking_retries_missing_us_and_selects_five(monkeypatch):
    articles = [
        article(0, "SCMP China", ["china"]),
        article(1, "SCMP Global Economy", ["china"]),
        article(2, "BBC World", ["global"]),
        article(3, "NPR World", ["global"]),
        article(4, "The Guardian World", ["global"]),
        article(5, "NPR Politics", ["us"]),
    ]
    client, completions = fake_client([
        json.dumps(ranking([0, 1, 2, 3, 4]), ensure_ascii=False),
        json.dumps(ranking([0, 1, 2, 3, 5]), ensure_ascii=False),
    ])
    monkeypatch.setattr(geopolitics_ranker, "OpenAI", lambda **kwargs: client)

    result = geopolitics_ranker.call_geopolitics_ranking(
        articles, "key", "https://api", "model"
    )
    selected = geopolitics_ranker.select_geopolitics_top5(articles, result)

    assert len(completions.calls) == 2
    assert [item["url"] for item in selected] == [
        "https://example.com/0",
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
        "https://example.com/5",
    ]
    assert completions.calls[0]["model"] == "model"


def test_geopolitics_ranking_rejects_duplicate_indices(monkeypatch):
    articles = [article(i, "BBC World", ["global"]) for i in range(6)]
    client, _ = fake_client([
        json.dumps(ranking([0, 0, 1, 2, 3])),
        json.dumps(ranking([0, 0, 1, 2, 3])),
    ])
    monkeypatch.setattr(geopolitics_ranker, "OpenAI", lambda **kwargs: client)

    try:
        geopolitics_ranker.call_geopolitics_ranking(articles, "key", "https://api", "model")
    except RuntimeError as exc:
        assert "排序调用失败" in str(exc)
    else:
        raise AssertionError("duplicate indices should fail")


def test_geopolitics_translation_uses_existing_client_and_preserves_metadata(monkeypatch):
    translated = {
        "items": [
            {"rank": i + 1, "title_cn": f"政经标题{i}", "summary_cn": "政经摘要" * 25}
            for i in range(5)
        ]
    }
    client, completions = fake_client([json.dumps(translated, ensure_ascii=False)])
    captured = {}

    def make_client(**kwargs):
        captured.update(kwargs)
        return client

    monkeypatch.setattr(translator, "OpenAI", make_client)
    top5 = [
        {
            "rank": i + 1,
            "title": f"English {i}",
            "url": f"https://trusted/{i}",
            "source": "BBC World",
            "regions": ["global"],
        }
        for i in range(5)
    ]

    result = translator.translate_geopolitics_top5(
        top5, "key", "https://api", "model"
    )

    assert captured == {"api_key": "key", "base_url": "https://api"}
    assert completions.calls[0]["model"] == "model"
    assert result[0]["url"] == "https://trusted/0"
    assert result[0]["regions"] == ["global"]
    assert result[0]["originalTitle"] == "English 0"
