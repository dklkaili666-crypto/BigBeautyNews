from config import GEOPOLITICS_RSS_SOURCES
from fetchers import rss_fetcher


def test_geopolitics_sources_are_the_approved_free_rss_feeds():
    assert [source["name"] for source in GEOPOLITICS_RSS_SOURCES] == [
        "SCMP China",
        "SCMP Global Economy",
        "NPR Politics",
        "NPR Business",
        "NPR World",
        "BBC World",
        "BBC Business",
        "The Guardian World",
    ]
    assert all(source["type"] == "rss" for source in GEOPOLITICS_RSS_SOURCES)
    assert all(source["url"].startswith("https://") for source in GEOPOLITICS_RSS_SOURCES)
    assert all(set(source) == {"name", "url", "type"} for source in GEOPOLITICS_RSS_SOURCES)


def test_geopolitics_source_failure_does_not_block_other_feeds(monkeypatch):
    sources = GEOPOLITICS_RSS_SOURCES[:2]

    def fake_fetch(source):
        if source["name"] == "SCMP China":
            raise RuntimeError("temporary failure")
        return [{
            "title": "Central bank changes interest rates",
            "url": "https://example.com/rates",
            "source": source["name"],
            "published": "2026-07-13T00:00:00Z",
            "summary": "Policy update",
        }]

    monkeypatch.setattr(rss_fetcher, "_fetch_one_source", fake_fetch)

    articles, errors = rss_fetcher.fetch_all_sources(sources)

    assert errors == ["SCMP China"]
    assert articles == [{
        "title": "Central bank changes interest rates",
        "url": "https://example.com/rates",
        "source": "SCMP Global Economy",
        "published": "2026-07-13T00:00:00Z",
        "summary": "Policy update",
    }]
