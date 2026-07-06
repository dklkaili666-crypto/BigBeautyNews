from pathlib import Path


def test_daily_workflow_has_fallback_schedule_and_skips_duplicate_pushes():
    workflow = (
        Path(__file__).parents[1] / ".github" / "workflows" / "daily.yml"
    ).read_text("utf-8")

    assert "cron: '45 23 * * *'" in workflow
    assert "cron: '15 0 * * *'" in workflow
    assert "cron: '35 0 * * *'" in workflow
    assert "cron: '55 0 * * *'" in workflow
    assert "cron: '20 1 * * *'" in workflow
    assert "id: push-check" in workflow
    assert "steps.push-check.outputs.should_run == 'true'" in workflow
    assert "force_push" in workflow
    assert "python src/main.py --force-push" in workflow
    assert "mark_latest_run_committed" in workflow


def test_daily_workflow_supports_phone_manual_push_trigger():
    workflow_path = Path(__file__).parents[1] / ".github" / "workflows" / "daily.yml"
    workflow = workflow_path.read_text("utf-8")
    template_path = (
        Path(__file__).parents[1] / ".github" / "ISSUE_TEMPLATE" / "manual-push.md"
    )

    assert "issues:" in workflow
    assert "issue_comment:" in workflow
    assert "github.actor == github.repository_owner" in workflow
    assert "/push-force" in workflow
    assert "FORCE_PUSH" in workflow
    assert template_path.exists()
    assert "/push-force" in template_path.read_text("utf-8")
