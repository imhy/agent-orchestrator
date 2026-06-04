# Copyright 2026 Geser Dugarov
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import unittest

os.environ.setdefault("ORCHESTRATOR_SKIP_DOTENV", "1")

from orchestrator import base_sync, github, workflow
from orchestrator.state_machine import (
    ControlLabel,
    WorkflowLabel,
    coerce_workflow_label,
)

from tests.fakes import FakeGitHubClient, make_issue


class WorkflowLabelEnumTest(unittest.TestCase):
    """`WorkflowLabel` is a `StrEnum`: members ARE their wire strings, so
    every existing string comparison, JSON serialization, and frozenset
    membership keeps working unchanged."""

    def test_member_equals_its_wire_string(self) -> None:
        self.assertEqual(WorkflowLabel.VALIDATING, "validating")
        self.assertEqual(WorkflowLabel.IN_REVIEW, "in_review")
        self.assertTrue(WorkflowLabel.DONE == "done")

    def test_json_serializes_as_plain_string(self) -> None:
        payload = {"label": WorkflowLabel.BLOCKED}
        self.assertEqual(json.dumps(payload), '{"label": "blocked"}')

    def test_frozenset_membership_both_directions(self) -> None:
        # Plain string against an enum-valued set, and enum against a
        # string-seeded set -- both must hold (hash/eq match str).
        self.assertIn("blocked", workflow._FAMILY_AWARE_LABELS)
        self.assertIn(WorkflowLabel.BLOCKED, workflow._FAMILY_AWARE_LABELS)
        self.assertIn("validating", base_sync._PR_REFRESH_DETOUR_LABELS)
        self.assertIn(WorkflowLabel.FIXING, base_sync._PR_REFRESH_DETOUR_LABELS)

    def test_workflow_labels_frozenset_is_the_enum(self) -> None:
        self.assertEqual(github.WORKFLOW_LABELS, frozenset(WorkflowLabel))
        self.assertIn("question", github.WORKFLOW_LABELS)

    def test_spec_table_is_exhaustive(self) -> None:
        self.assertEqual(
            {spec[0] for spec in github.WORKFLOW_LABEL_SPECS},
            set(WorkflowLabel),
        )

    def test_control_labels_are_not_workflow_states(self) -> None:
        # backlog / hold_base_sync are modifiers, not FSM states: they must
        # not leak into the workflow vocabulary.
        self.assertEqual(ControlLabel.BACKLOG, "backlog")
        self.assertNotIn(ControlLabel.BACKLOG, github.WORKFLOW_LABELS)
        self.assertNotIn(ControlLabel.HOLD_BASE_SYNC, github.WORKFLOW_LABELS)


class CoerceWorkflowLabelTest(unittest.TestCase):
    def test_valid_string_returns_member(self) -> None:
        self.assertIs(coerce_workflow_label("validating"), WorkflowLabel.VALIDATING)

    def test_member_is_idempotent(self) -> None:
        self.assertIs(
            coerce_workflow_label(WorkflowLabel.DONE), WorkflowLabel.DONE
        )

    def test_typo_raises_with_helpful_message(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            coerce_workflow_label("validatign")
        msg = str(ctx.exception)
        self.assertIn("validatign", msg)
        self.assertIn("valid workflow label", msg)


class LabelWriteTypoGuardTest(unittest.TestCase):
    """Every orchestrator-authored workflow-label write coerces, so a
    typo raises instead of applying an invisible label. The fake mirrors
    the real client, so the whole fake-backed suite shares the guard."""

    def test_set_workflow_label_rejects_typo(self) -> None:
        gh = FakeGitHubClient()
        issue = make_issue(1, label="implementing")
        gh.add_issue(issue)
        with self.assertRaises(ValueError):
            gh.set_workflow_label(issue, "vaildating")

    def test_set_workflow_label_accepts_enum_and_string(self) -> None:
        gh = FakeGitHubClient()
        issue = make_issue(1, label="implementing")
        gh.add_issue(issue)
        gh.set_workflow_label(issue, WorkflowLabel.VALIDATING)
        self.assertEqual(gh.workflow_label(issue), WorkflowLabel.VALIDATING)
        gh.set_workflow_label(issue, "documenting")  # plain string still ok
        self.assertEqual(gh.workflow_label(issue), WorkflowLabel.DOCUMENTING)

    def test_workflow_label_returns_typed_member(self) -> None:
        gh = FakeGitHubClient()
        issue = make_issue(1, label="fixing")
        gh.add_issue(issue)
        result = gh.workflow_label(issue)
        self.assertIsInstance(result, WorkflowLabel)
        self.assertIs(result, WorkflowLabel.FIXING)

    def test_create_child_issue_rejects_typo(self) -> None:
        gh = FakeGitHubClient()
        with self.assertRaises(ValueError):
            gh.create_child_issue(
                title="t", body="b", parent_number=1, labels=["blokced"],
            )


if __name__ == "__main__":
    unittest.main()
