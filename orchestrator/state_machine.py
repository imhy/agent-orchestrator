# Copyright 2026 Geser Dugarov
# SPDX-License-Identifier: Apache-2.0
"""Typed workflow states for the orchestrator's label-based state machine.

`WorkflowLabel` is the single source of truth for the workflow label
vocabulary. It is a `StrEnum`, so every member *is* its on-the-wire
string: existing string comparisons (`label == "validating"`), JSON
serialization of pinned state, and PyGithub label writes keep working
unchanged. The point of the enum is not to replace the strings but to
give them one authoritative definition, IDE/refactor support, and a
membership set the typo guard can validate against.

`ControlLabel` holds operator-applied *modifiers* (`backlog`,
`hold_base_sync`) that coexist with a workflow label and pause/redirect
processing without being workflow states themselves -- an issue is
`implementing` + `backlog` at once. They are deliberately NOT workflow
states and never flow through `set_workflow_label` or the transition
table.

The transition table and guard live in this module too (added alongside
`validate_transition`); `github.set_workflow_label` is the single
chokepoint that calls them.
"""
from __future__ import annotations

from enum import StrEnum


class WorkflowLabel(StrEnum):
    """The workflow states. Member value == the GitHub label string."""

    DECOMPOSING = "decomposing"
    READY = "ready"
    BLOCKED = "blocked"
    UMBRELLA = "umbrella"
    IMPLEMENTING = "implementing"
    VALIDATING = "validating"
    DOCUMENTING = "documenting"
    IN_REVIEW = "in_review"
    FIXING = "fixing"
    RESOLVING_CONFLICT = "resolving_conflict"
    QUESTION = "question"
    DONE = "done"
    REJECTED = "rejected"


class ControlLabel(StrEnum):
    """Operator-applied modifiers that coexist with a workflow label.

    Not workflow states: they gate or redirect processing while leaving
    the underlying `WorkflowLabel` intact (a child can be `ready` +
    `backlog` -- "ready in the FSM, but operator-held"). Never passed to
    `set_workflow_label` and never present in the transition table.
    """

    BACKLOG = "backlog"
    HOLD_BASE_SYNC = "hold_base_sync"


def coerce_workflow_label(value: str) -> WorkflowLabel:
    """Return the `WorkflowLabel` for ``value`` or raise ``ValueError``.

    Called at every orchestrator-authored workflow-label write
    (`set_workflow_label`, `create_child_issue`) so a typo'd label name
    fails loudly instead of being applied as a literal GitHub label and
    then silently demoted to unlabeled-pickup on the next tick (a label
    not in `WorkflowLabel` is invisible to `workflow_label`).

    Accepts an existing `WorkflowLabel` (idempotent) or its string value.
    """
    try:
        return WorkflowLabel(value)
    except ValueError:
        valid = ", ".join(repr(str(m)) for m in WorkflowLabel)
        raise ValueError(
            f"{value!r} is not a valid workflow label; expected one of: {valid}"
        ) from None
