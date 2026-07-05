from pipeline.dedup import dedup_candidates
from datetime import datetime, timezone

from pipeline.filter import (
    exclude_historical_duplicates,
    filter_ai_related,
    filter_recent_articles,
)


def test_dedup_merges_similar_reports_and_tracks_sources():
    articles = [
        {"title": "OpenAI releases new GPT model today", "source": "Wired", "url": "https://a"},
        {"title": "OpenAI releases a new GPT model today", "source": "The Verge", "url": "https://b"},
        {"title": "Unrelated robotics funding news", "source": "TechCrunch", "url": "https://c"},
    ]

    result = dedup_candidates(articles)

    assert len(result) == 2
    assert result[0]["merged_sources"] == ["Wired", "The Verge"]


def test_dedup_merges_real_cross_source_headline_variant():
    articles = [
        {
            "title": "Trump drops restrictions on Anthropic’s Mythos and Fable models",
            "source": "TechCrunch",
            "url": "https://example.com/tc",
        },
        {
            "title": "The Trump Administration Is Lifting Its Export Controls on Anthropic’s Mythos and Fable AI Models",
            "source": "Wired",
            "url": "https://example.com/wired",
        },
    ]

    result = dedup_candidates(articles)

    assert len(result) == 1
    assert result[0]["merged_sources"] == ["TechCrunch", "Wired"]


def test_dedup_does_not_merge_similar_but_distinct_stories_from_same_source():
    articles = [
        {
            "title": "OpenAI launches a new model for coding agents",
            "source": "TechCrunch",
            "url": "https://example.com/coding",
        },
        {
            "title": "OpenAI launches a new model for science agents",
            "source": "TechCrunch",
            "url": "https://example.com/science",
        },
    ]

    assert len(dedup_candidates(articles)) == 2


def test_filter_matches_ai_terms_without_treating_raise_as_ai():
    articles = [
        {"title": "Airline raises ticket prices", "summary": "", "source": "TechCrunch"},
        {"title": "Startup builds a new AI agent", "summary": "", "source": "TechCrunch"},
        {"title": "Anything", "summary": "", "source": "GitHub Trending"},
    ]

    result = filter_ai_related(articles)

    assert [item["source"] for item in result] == ["TechCrunch", "GitHub Trending"]


def test_historical_filter_excludes_recent_urls_and_near_identical_events():
    articles = [
        {
            "title": "Microsoft launches a $2.5B AI deployment company",
            "url": "https://example.com/already-pushed",
        },
        {
            "title": "Anthropic and Samsung discuss a custom AI chip",
            "url": "https://example.com/same-event-new-source",
        },
        {
            "title": "Anthropic launches a new science product",
            "url": "https://example.com/new-event",
        },
    ]
    historical = [
        {
            "originalTitle": "Microsoft launches a $2.5B AI deployment company",
            "url": "https://example.com/already-pushed",
        },
        {
            "originalTitle": "Anthropic and Samsung discuss custom AI chips",
            "url": "https://other.example.com/anthropic-samsung",
        },
    ]

    result = exclude_historical_duplicates(articles, historical)

    assert [item["url"] for item in result] == ["https://example.com/new-event"]


def test_freshness_filter_keeps_recent_and_undated_realtime_sources():
    articles = [
        {"title": "Recent", "published": "2026-07-04T12:00:00Z"},
        {"title": "Old", "published": "2026-07-02T00:00:00Z"},
        {"title": "Trending", "published": "", "source": "GitHub Trending"},
    ]

    result = filter_recent_articles(
        articles,
        now=datetime(2026, 7, 5, 0, 0, tzinfo=timezone.utc),
        max_age_hours=48,
    )

    assert [item["title"] for item in result] == ["Recent", "Trending"]
