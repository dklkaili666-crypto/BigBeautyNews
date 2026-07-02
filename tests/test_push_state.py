from outputs.push_state import mark_pushed, was_pushed


def test_push_state_only_marks_date_after_success(tmp_path):
    path = tmp_path / "push-history.json"

    assert was_pushed(str(path), "2026-07-02") is False

    mark_pushed(str(path), "2026-07-02")

    assert was_pushed(str(path), "2026-07-02") is True
    assert was_pushed(str(path), "2026-07-03") is False
