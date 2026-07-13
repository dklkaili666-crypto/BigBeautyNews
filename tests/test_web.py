from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_web_renderer_supports_dual_boards_and_legacy_archives():
    app = (ROOT / "web" / "app.js").read_text("utf-8")

    assert "data.geopoliticsItems || []" in app
    assert "data.geopoliticsTheme || ''" in app
    assert "一、AI 重要消息" in app
    assert "二、全球地缘与政经" in app
    assert "if (geopoliticsItems.length > 0)" in app
    assert "renderSection('', theme, items, 'ai')" in app


def test_web_renderer_keeps_date_navigation_and_safe_links():
    app = (ROOT / "web" / "app.js").read_text("utf-8")

    assert "../data/archive/${dateStr}.json" in app
    assert "safeHttpUrl(item.url)" in app
    assert 'rel="noopener noreferrer"' in app
    assert "btnPrev.addEventListener" in app
    assert "btnNext.addEventListener" in app
