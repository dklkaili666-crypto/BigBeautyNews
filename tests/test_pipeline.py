from pipeline.dedup import dedup_candidates
from pipeline.filter import filter_ai_related


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
