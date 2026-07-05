from pipeline.dedup import dedup_candidates
from datetime import datetime, timezone

from pipeline.filter import (
    exclude_historical_duplicates,
    filter_ai_related,
    filter_recent_articles,
)
from pipeline.enrichment import enrich_articles, canonicalize_url


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


def test_filter_keeps_investment_entity_news_without_literal_ai():
    articles = [
        {
            "title": "Microsoft raises capex forecast again",
            "summary": "Data center power and cloud infrastructure spending will rise.",
            "source": "TechCrunch",
        },
        {
            "title": "Airline raises ticket prices",
            "summary": "Travel demand remains strong.",
            "source": "TechCrunch",
        },
    ]

    result = filter_ai_related(articles)

    assert [item["title"] for item in result] == [
        "Microsoft raises capex forecast again"
    ]


def test_filter_rejects_generic_policy_news_without_ai_context():
    articles = [
        {
            "title": "The UK tobacco ban might not work",
            "summary": "A new policy could change smoking rules for young people.",
            "source": "MIT Technology Review",
        },
        {
            "title": "White House AI export control policy targets advanced GPUs",
            "summary": "New regulation affects Nvidia accelerators and AI data centers.",
            "source": "The Verge",
        },
    ]

    result = filter_ai_related(articles)

    assert [item["title"] for item in result] == [
        "White House AI export control policy targets advanced GPUs"
    ]


def test_filter_rejects_generic_policy_news_with_only_incidental_ai_mention():
    articles = [
        {
            "title": "The UK tobacco ban might not work",
            "summary": "The article briefly says children are learning about AI at school.",
            "source": "MIT Technology Review",
        },
        {
            "title": "AI safety policy targets frontier model labs",
            "summary": "The rule affects OpenAI and Anthropic deployment practices.",
            "source": "The Verge",
        },
    ]

    result = filter_ai_related(articles)

    assert [item["title"] for item in result] == [
        "AI safety policy targets frontier model labs"
    ]


def test_enrichment_adds_source_tier_event_id_scores_and_canonical_url():
    articles = [
        {
            "title": "Microsoft raises capex forecast again",
            "url": "https://Example.com/path/?utm_source=x&gclid=y#section",
            "source": "TechCrunch",
            "summary": "Azure data center spending rises for AI infrastructure.",
            "published": "2026-07-05T00:00:00Z",
        }
    ]

    result = enrich_articles(articles)

    assert result[0]["sourceTier"] == "tier2"
    assert result[0]["canonicalUrl"] == "https://example.com/path"
    assert result[0]["eventId"]
    assert "Microsoft" in result[0]["entities"]
    assert result[0]["eventType"] == "capex"
    assert 0 <= result[0]["marketImpactScore"] <= 5
    assert result[0]["totalScore"] > 0


def test_enrichment_does_not_boost_generic_regulation_without_ai_context():
    result = enrich_articles([
        {
            "title": "The UK tobacco ban might not work",
            "url": "https://example.com/tobacco",
            "source": "MIT Technology Review",
            "summary": "A new policy could change smoking rules for young people.",
            "published": "2026-07-05T00:00:00Z",
        }
    ])

    assert result[0]["eventType"] == "unknown"
    assert result[0]["marketImpactScore"] < 4


def test_enrichment_extracts_high_frequency_ai_entities():
    result = enrich_articles([
        {
            "title": "Midjourney asks studios to disclose AI usage",
            "url": "https://example.com/midjourney",
            "source": "TechCrunch",
            "summary": "usestrix/strix trends on GitHub as AI security tooling grows.",
        }
    ])

    assert result[0]["entities"] == ["Midjourney", "Strix"]


def test_canonical_url_normalizes_tracking_parameters():
    assert (
        canonicalize_url("HTTPS://Example.com/a/?utm_campaign=x&fbclid=y&keep=1#x")
        == "https://example.com/a?keep=1"
    )


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


def test_historical_filter_excludes_event_ids_and_github_repo_cooldown():
    articles = [
        {
            "title": "Follow old event",
            "url": "https://example.com/new-url",
            "canonicalUrl": "https://example.com/new-url",
            "eventId": "event-1",
            "source": "TechCrunch",
        },
        {
            "title": "Trending repo again",
            "url": "https://github.com/org/repo?utm_source=x",
            "canonicalUrl": "https://github.com/org/repo",
            "eventId": "event-2",
            "source": "GitHub Trending",
        },
        {
            "title": "New event",
            "url": "https://example.com/new",
            "canonicalUrl": "https://example.com/new",
            "eventId": "event-3",
            "source": "TechCrunch",
        },
    ]
    historical = [
        {
            "url": "https://example.com/old-url",
            "canonicalUrl": "https://example.com/old-url",
            "eventId": "event-1",
        },
        {
            "url": "https://github.com/org/repo",
            "canonicalUrl": "https://github.com/org/repo",
            "source": "GitHub Trending",
        },
    ]

    result = exclude_historical_duplicates(articles, historical)

    assert [item["title"] for item in result] == ["New event"]


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
