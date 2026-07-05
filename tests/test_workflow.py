from pathlib import Path


def test_daily_workflow_has_fallback_schedule_and_skips_duplicate_pushes():
    workflow = (
        Path(__file__).parents[1] / ".github" / "workflows" / "daily.yml"
    ).read_text("utf-8")

    assert "cron: '45 23 * * *'" in workflow
    assert "cron: '15 0 * * *'" in workflow
    assert "id: push-check" in workflow
    assert "steps.push-check.outputs.should_run == 'true'" in workflow
    assert "force_push" in workflow
    assert "python src/main.py --force-push" in workflow
