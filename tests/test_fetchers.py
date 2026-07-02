from fetchers import github_trending, hacker_news, rss_fetcher


class FakeResponse:
    def __init__(self, *, content=b"", text="", json_data=None, status=200):
        self.content = content
        self.text = text
        self._json_data = json_data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


def test_rss_fetcher_normalizes_feed_entries(monkeypatch):
    feed = b"""<rss version="2.0"><channel><item>
      <title>Anthropic&amp;#8217;s new AI model</title><link>https://example.com/a</link>
      <pubDate>Wed, 01 Jul 2026 00:00:00 GMT</pubDate>
      <description>Summary</description>
    </item></channel></rss>"""
    monkeypatch.setattr(
        rss_fetcher.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(content=feed),
    )

    articles, errors = rss_fetcher.fetch_all_sources(
        [{"name": "Example", "url": "https://example.com/feed", "type": "rss"}]
    )

    assert errors == []
    assert articles == [{
        "title": "Anthropic’s new AI model",
        "url": "https://example.com/a",
        "source": "Example",
        "published": "2026-07-01T00:00:00Z",
        "summary": "Summary",
    }]


def test_github_trending_only_returns_ai_repositories(monkeypatch):
    page = """<article class="Box-row">
      <h2><a href="/org/agent-kit">org / agent-kit</a></h2>
      <p>A framework for building LLM agents</p>
      <span itemprop="programmingLanguage">Python</span>
      <span class="d-inline-block float-sm-right">123 stars today</span>
    </article><article class="Box-row">
      <h2><a href="/org/web">org / web</a></h2>
      <p>A regular web framework</p>
      <span itemprop="programmingLanguage">Python</span>
    </article>"""
    monkeypatch.setattr(
        github_trending.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(text=page),
    )

    result = github_trending.fetch_trending()

    assert len(result) == 1
    assert result[0]["stars_today"] == 123
    assert result[0]["url"] == "https://github.com/org/agent-kit"
    assert result[0]["title"].startswith("org/agent-kit:")


def test_hacker_news_filters_by_score_and_ai_title(monkeypatch):
    stories = {
        "top": [1, 2],
        1: {"title": "A new open source LLM", "score": 100, "descendants": 20, "url": "https://a"},
        2: {"title": "A gardening story", "score": 200, "descendants": 3},
    }

    def fake_get(url, **kwargs):
        key = "top" if "topstories" in url else int(url.rsplit("/", 1)[-1].split(".")[0])
        return FakeResponse(json_data=stories[key])

    monkeypatch.setattr(hacker_news.requests, "get", fake_get)

    result = hacker_news.fetch_hn_top_ai(limit=2, min_score=50)

    assert [item["title"] for item in result] == ["A new open source LLM"]
