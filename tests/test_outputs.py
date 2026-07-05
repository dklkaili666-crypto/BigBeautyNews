import json

from outputs.json_writer import (
    build_internal_digest,
    build_external_digest,
    archive_daily_json,
    load_recent_archive_items,
    update_history_index,
)
from outputs.serverchan import build_markdown_message
from outputs.web_builder import write_web_data


def sample_items():
    return [
        {
            "rank": i + 1,
            "title": f"English {i}",
            "title_cn": f"中文标题{i}",
            "summary_cn": "中文摘要" * 25,
            "url": f"https://example.com/{i}",
            "source": "Example",
            "tags": ["大模型"],
        }
        for i in range(5)
    ]


def test_output_schemas_keep_internal_fields_out_of_external_contract(tmp_path):
    internal = build_internal_digest(
        sample_items(),
        "模型竞争",
        date_str="2026-07-01",
        exported_at="2026-07-01T00:00:00Z",
    )
    external = build_external_digest(internal)
    archive_daily_json(internal, str(tmp_path / "archive"))
    write_web_data(internal, str(tmp_path / "web"))

    assert set(external["items"][0]) == {"date", "title", "summary", "url", "source"}
    assert internal["dailyTheme"] == "模型竞争"
    assert internal["items"][0]["rank"] == 1
    assert internal["items"][0]["published"] == ""
    assert internal["items"][0]["mergedSources"] == []
    assert internal["items"][0]["selectionReason"] == ""
    assert json.loads((tmp_path / "web" / "data.json").read_text("utf-8")) == internal


def test_history_index_deduplicates_and_sorts_dates(tmp_path):
    path = tmp_path / "history.json"
    update_history_index(str(path), "2026-07-01")
    result = update_history_index(str(path), "2026-06-30")
    result = update_history_index(str(path), "2026-07-01")

    assert result["dates"] == ["2026-07-01", "2026-06-30"]


def test_recent_archive_loader_excludes_today_and_old_entries(tmp_path):
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    for date in ("2026-06-27", "2026-07-03", "2026-07-04", "2026-07-05"):
        (archive_dir / f"{date}.json").write_text(
            json.dumps({"items": [{"url": f"https://example.com/{date}"}]}),
            encoding="utf-8",
        )

    result = load_recent_archive_items(
        str(archive_dir),
        before_date="2026-07-05",
        days=7,
    )

    assert [item["url"] for item in result] == [
        "https://example.com/2026-07-03",
        "https://example.com/2026-07-04",
    ]


def test_serverchan_message_contains_five_markdown_links():
    title, markdown, plaintext = build_markdown_message(sample_items(), "2026-07-01", "模型竞争")

    assert "2026-07-01" in title
    assert markdown.count("[阅读原文]") == 5
    assert "模型竞争" in plaintext
