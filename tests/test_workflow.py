from pathlib import Path


def test_daily_workflow_uses_external_scheduler_and_skips_duplicate_pushes():
    workflow = (
        Path(__file__).parents[1] / ".github" / "workflows" / "daily.yml"
    ).read_text("utf-8")

    assert "\n  schedule:\n" not in workflow
    assert "trigger_source:" in workflow
    assert "schedule_slot:" in workflow
    assert "external_scheduler" in workflow
    assert "inputs.trigger_source == 'external_scheduler'" in workflow
    assert "Validate workflow dispatch inputs" in workflow
    assert '[[ "$SCHEDULE_SLOT" =~ ^(primary|fallback)$ ]]' in workflow
    assert 'os.environ[\'SCHEDULE_SLOT\']' in workflow
    assert "id: push-check" in workflow
    assert "steps.push-check.outputs.should_run == 'true'" in workflow
    assert "force_push" in workflow
    assert "push_test" in workflow
    assert "git pull --ff-only origin master" in workflow
    assert "python src/main.py --force-push" in workflow
    assert "mark_latest_run_committed" in workflow
    assert "record_skipped_external_run" in workflow
    assert "steps.push-check.outputs.should_run == 'false'" in workflow
    assert "python -m outputs.serverchan --test" in workflow


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


def test_daily_workflow_stops_pages_but_keeps_data_commit_and_raw_contract():
    workflow = (
        Path(__file__).parents[1] / ".github" / "workflows" / "daily.yml"
    ).read_text("utf-8")

    assert "pages: write" not in workflow
    assert "id-token: write" not in workflow
    assert "github-pages" not in workflow
    assert "actions/configure-pages" not in workflow
    assert "actions/upload-pages-artifact" not in workflow
    assert "actions/deploy-pages" not in workflow
    assert "_site" not in workflow
    assert "contents: write" in workflow
    assert "git add data/ web/data.json" in workflow
    assert "git push" in workflow
