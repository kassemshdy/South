"""Moving a ticket to To do or Approved starts the triage routine at once."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.models.enums import FeedbackStatus
from app.models.user import User
from app.services import triage_trigger
from tests.conftest import admin_headers

FIRE_URL = "https://api.anthropic.test/v1/claude_code/routines/trig_x/fire"
TOKEN = "sk-ant-oat01-test"


@pytest.fixture(autouse=True)
def _fresh() -> Iterator[None]:
    triage_trigger.reset()
    yield
    triage_trigger.reset()


def _configured() -> Settings:
    return Settings(claude_triage_fire_url=FIRE_URL, claude_triage_token=TOKEN)


def _recording() -> tuple[httpx.Client, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"type": "routine_fire"})

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def _now(value: float) -> Callable[[], float]:
    return lambda: value


def _inline(call: Callable[[], None]) -> None:
    call()


def test_a_move_to_todo_calls_the_fire_endpoint_with_the_bearer_token() -> None:
    client, seen = _recording()
    fired = triage_trigger.fire(
        "t-1", FeedbackStatus.TODO, settings=_configured(), client=client, run=_inline
    )

    assert fired and len(seen) == 1
    request = seen[0]
    assert str(request.url) == FIRE_URL
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert request.headers["anthropic-version"] == triage_trigger.API_VERSION
    text = json.loads(request.content)["text"]
    assert "t-1" in text and "TODO" in text


def test_only_the_ticket_id_and_column_are_sent() -> None:
    """Ticket text is written by other people; it reaches the routine through
    the board, never inside the message that starts it."""
    assert triage_trigger.request_body("t-1", FeedbackStatus.APPROVED) == {
        "text": (
            "A person moved support ticket t-1 to APPROVED. "
            "Run one pass of the triage-loop skill now."
        )
    }


@pytest.mark.parametrize(
    "status",
    [s for s in FeedbackStatus if s not in triage_trigger.FIRING_STATUSES],
)
def test_other_columns_start_nothing(status: FeedbackStatus) -> None:
    client, seen = _recording()
    assert not triage_trigger.fire(
        "t-1", status, settings=_configured(), client=client, run=_inline
    )
    assert seen == []


def test_nothing_is_called_without_both_variables() -> None:
    client, seen = _recording()
    for settings in (
        Settings(),
        Settings(claude_triage_fire_url=FIRE_URL),
        Settings(claude_triage_token=TOKEN),
    ):
        assert not triage_trigger.fire(
            "t-1", FeedbackStatus.TODO, settings=settings, client=client, run=_inline
        )
    assert seen == []


def test_moves_close_together_start_one_run() -> None:
    client, seen = _recording()
    settings = _configured()
    window = triage_trigger.DEBOUNCE_SECONDS

    def fire(at: float, status: FeedbackStatus = FeedbackStatus.TODO) -> bool:
        return triage_trigger.fire(
            "t-1", status, settings=settings, client=client, run=_inline, clock=_now(at)
        )

    assert fire(1000.0)
    assert not fire(1000.0 + window - 1, FeedbackStatus.APPROVED)
    assert fire(1000.0 + window)
    assert len(seen) == 2


def test_a_refused_or_failing_trigger_does_not_raise() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    for handler in (refuse, broken):
        triage_trigger.reset()
        client = httpx.Client(transport=httpx.MockTransport(handler))
        assert triage_trigger.fire(
            "t-1", FeedbackStatus.TODO, settings=_configured(), client=client, run=_inline
        )


def test_the_board_fires_on_a_move_into_todo_or_approved_only(
    client: TestClient, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, FeedbackStatus]] = []
    monkeypatch.setattr(
        triage_trigger, "fire", lambda ticket_id, status, **_: calls.append((ticket_id, status))
    )
    headers = admin_headers(client)
    ticket = client.post(
        "/api/admin/feedback/tickets", headers=headers, json={"title": "a bug"}
    ).json()
    for status in ("TODO", "TODO", "IN_PROGRESS", "NEEDS_APPROVAL", "APPROVED"):
        moved = client.post(
            f"/api/admin/feedback/tickets/{ticket['id']}/move",
            headers=headers,
            json={"status": status, "index": 0},
        )
        assert moved.status_code == 200, moved.text

    # A reorder within To do is not a hand-off; the service passes every
    # column change and the trigger decides which ones start a run.
    assert [s for _, s in calls] == [
        FeedbackStatus.TODO,
        FeedbackStatus.IN_PROGRESS,
        FeedbackStatus.NEEDS_APPROVAL,
        FeedbackStatus.APPROVED,
    ]
    assert {t for t, _ in calls} == {ticket["id"]}
