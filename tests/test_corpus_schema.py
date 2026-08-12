from __future__ import annotations

import json

import jsonschema
import pytest

from adop_testbed.host.agent_host import load_tasks
from adop_testbed.sandbox import PROJECT_ROOT

SCHEMA = json.loads((PROJECT_ROOT / "docs" / "log_record.schema.json").read_text(encoding="utf-8"))
# Only the graded, frozen corpus directories -- corpus/live-demo/ is
# generated, ungraded output from optional Live-mode runs (see
# scripts/live_mode.py) and is intentionally excluded here.
CORPUS_FILES = sorted(
    p for scenario in ("clean", "poisoned") for p in (PROJECT_ROOT / "corpus" / scenario).glob("*.jsonl")
)


def test_corpus_is_not_empty():
    assert CORPUS_FILES, "expected at least one frozen corpus file under corpus/*/*.jsonl"


@pytest.mark.parametrize("path", CORPUS_FILES, ids=lambda p: str(p.relative_to(PROJECT_ROOT)))
def test_every_record_matches_schema(path):
    validator = jsonschema.Draft202012Validator(SCHEMA)
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        record = json.loads(line)
        errors = sorted(validator.iter_errors(record), key=lambda e: e.path)
        assert not errors, f"{path}:{i}: {[e.message for e in errors]}"


@pytest.mark.parametrize("path", CORPUS_FILES, ids=lambda p: str(p.relative_to(PROJECT_ROOT)))
def test_scenario_tag_matches_directory(path):
    expected = path.parent.name
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        assert record["scenario_tag"] == expected


def test_task_ids_referenced_all_exist():
    known_ids = {t.id for t in load_tasks()}
    for path in CORPUS_FILES:
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            assert record["task_id"] in known_ids


def test_seq_is_globally_monotonic_per_session():
    by_session: dict[str, list[int]] = {}
    for path in CORPUS_FILES:
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            by_session.setdefault(record["session_id"], []).append(record["seq"])
    for session_id, seqs in by_session.items():
        seqs.sort()
        assert seqs == list(range(1, len(seqs) + 1)), f"seq gap or duplicate in session {session_id}: {seqs}"


def test_poisoned_corpus_contains_cve_annotations():
    poisoned = PROJECT_ROOT / "corpus" / "poisoned"
    annotations_seen: set[str] = set()
    for path in poisoned.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            annotations_seen.update(json.loads(line).get("annotations", []))
    assert "cve-2025-68144" in annotations_seen
    assert "untrusted_content_source" in annotations_seen
    assert "post_injection_context" in annotations_seen
