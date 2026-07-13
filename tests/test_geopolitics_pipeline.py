from datetime import datetime, timezone

from pipeline.dedup import exclude_cross_board_duplicates, is_same_event
from pipeline.geopolitics import (
    classify_primary_board,
    classify_regions,
    filter_geopolitics_related,
    select_fresh_geopolitics_window,
)


def test_filter_keeps_china_us_and_global_policy_events():
    articles = [
        {
            "title": "China announces new economic stimulus package",
            "summary": "Beijing targets economic growth with fiscal policy.",
        },
        {
            "title": "Federal Reserve cuts interest rates",
            "summary": "The United States central bank responds to inflation.",
        },
        {
            "title": "Russia and Ukraine agree to ceasefire talks",
            "summary": "Diplomatic negotiations seek to pause the war.",
        },
    ]

    result = filter_geopolitics_related(articles)

    assert len(result) == 3
    assert result[0]["regions"] == ["china"]
    assert result[1]["regions"] == ["us"]
    assert result[2]["regions"] == ["global"]
    assert all(item["geopoliticsRuleScore"] > 1 for item in result)


def test_filter_keeps_plural_event_terms_and_us_abbreviations():
    articles = [
        {"title": "U.S. imposes new sanctions on China", "summary": ""},
        {"title": "US raises tariffs on Chinese imports", "summary": ""},
        {
            "title": "European elections reshape economic policy",
            "summary": "New regulations feature in the campaign.",
        },
        {"title": "Iran tests missiles", "summary": "Regional security tensions rise."},
    ]

    result = filter_geopolitics_related(articles)

    assert [item["title"] for item in result] == [
        "U.S. imposes new sanctions on China",
        "US raises tariffs on Chinese imports",
        "European elections reshape economic policy",
        "Iran tests missiles",
    ]
    assert result[0]["regions"] == ["china", "us"]
    assert result[1]["regions"] == ["china", "us"]
    assert result[2]["regions"] == ["global"]


def test_lowercase_us_pronoun_is_not_classified_as_united_states():
    article = {
        "title": "The policy tells us how families save",
        "summary": "A household budget guide.",
    }

    assert classify_regions(article) == []
    assert filter_geopolitics_related([article]) == []


def test_filter_rejects_noise_and_incidental_policy_words():
    articles = [
        {"title": "Hollywood awards draw record audience", "summary": "Entertainment news."},
        {"title": "Opinion: What I think about Washington", "summary": "General commentary."},
        {"title": "US football league changes transfer policy", "summary": "A sports roster rule."},
        {"title": "China travel guide", "summary": "Food and lifestyle recommendations."},
    ]

    assert filter_geopolitics_related(articles) == []


def test_region_classification_uses_event_subject_not_source():
    article = {
        "title": "China and United States resume tariff talks",
        "summary": "Beijing and the White House restart trade diplomacy.",
        "source": "BBC World",
    }

    assert classify_regions(article) == ["china", "us"]


def test_crossover_event_is_assigned_to_dominant_board():
    export_control = {
        "title": "United States tightens AI chip export controls on China",
        "summary": "The rule restricts Nvidia GPU shipments.",
    }
    model_release = {
        "title": "OpenAI releases new GPT model",
        "summary": "The model improves reasoning benchmark scores.",
    }

    assert classify_primary_board(export_control) == "geopolitics"
    assert classify_primary_board(model_release) == "ai"


def test_ai_policy_without_geopolitical_actor_stays_in_ai_board():
    article = {
        "title": "OpenAI updates model safety policy",
        "summary": "The AI lab changes internal deployment rules.",
    }

    assert classify_primary_board(article) == "ai"


def test_freshness_window_uses_48_then_72_hours():
    now = datetime(2026, 7, 13, tzinfo=timezone.utc)
    articles = [
        {"title": f"Recent {i}", "published": "2026-07-12T00:00:00Z"}
        for i in range(4)
    ] + [{"title": "Older", "published": "2026-07-10T12:00:00Z"}]

    selected, window = select_fresh_geopolitics_window(articles, now=now)

    assert len(selected) == 5
    assert window == 72


def test_cross_board_duplicate_detection_uses_url_event_and_title():
    ai_items = [{
        "title": "US tightens AI chip export controls on China",
        "url": "https://example.com/story?utm_source=x",
        "eventId": "event-1",
    }]
    candidates = [
        {
            "title": "United States tightens AI chip export controls on China",
            "url": "https://example.com/story",
        },
        {
            "title": "Federal Reserve cuts interest rates",
            "url": "https://example.com/rates",
        },
    ]

    assert is_same_event(ai_items[0], candidates[0])
    assert exclude_cross_board_duplicates(candidates, ai_items) == [candidates[1]]
