"""What each tool actually asks the API for.

Driven through ``MCPServer.call_tool`` rather than by calling the closures
directly, so the argument schemas the model sees are exercised too.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from south_mcp.client import SouthClient
from south_mcp.server import build_server
from tests.stub_api import StubApi

TICKETS = "/api/admin/feedback/tickets"


@pytest.fixture
def stub() -> StubApi:
    return StubApi()


def call(stub: StubApi, tool: str, **arguments: Any) -> Any:
    client = SouthClient(stub.config, transport=stub.transport)
    server = build_server(stub.config, client)
    result = asyncio.run(server.call_tool(tool, arguments))
    if result.is_error:
        raise AssertionError(f"{tool} failed: {result.content}")

    # A tool returning a list arrives as {"result": [...]}; one returning a
    # mapping arrives as the mapping itself.
    structured = result.structured_content
    if structured is not None:
        return structured["result"] if set(structured) == {"result"} else structured
    return result.content[0].text


def tools_of(stub: StubApi) -> list[Any]:
    server = build_server(stub.config, SouthClient(stub.config, transport=stub.transport))
    return asyncio.run(server.list_tools())


def a_ticket(**overrides: Any) -> dict[str, Any]:
    ticket = {
        "id": "t1",
        "title": "Search returns nothing",
        "status": "TODO",
        "priority": "HIGH",
        "assignee": {"email": "dev@example.com"},
    }
    ticket.update(overrides)
    return ticket


# --- the trap this design exists to avoid --------------------------------


def test_a_status_change_goes_through_move_not_the_edit_route(stub: StubApi) -> None:
    """The edit route silently ignores `status` and answers 200, so a tool
    that mirrored it would report a move that never happened."""
    stub.on("POST", f"{TICKETS}/t1/move", [a_ticket(status="IN_PROGRESS")])
    stub.on("GET", f"{TICKETS}/t1", a_ticket(status="IN_PROGRESS"))

    call(stub, "update_ticket", ticket_id="t1", status="IN_PROGRESS")

    assert ("POST", f"{TICKETS}/t1/move") in stub.calls
    assert ("PUT", f"{TICKETS}/t1") not in stub.calls


def test_editing_fields_uses_the_edit_route_and_does_not_move_anything(stub: StubApi) -> None:
    stub.on("PUT", f"{TICKETS}/t1", a_ticket(priority="URGENT"))
    stub.on("GET", f"{TICKETS}/t1", a_ticket(priority="URGENT"))

    call(stub, "update_ticket", ticket_id="t1", priority="URGENT")

    assert ("PUT", f"{TICKETS}/t1") in stub.calls
    assert f"{TICKETS}/t1/move" not in stub.paths()


def test_fields_and_a_status_in_one_call_do_both(stub: StubApi) -> None:
    stub.on("PUT", f"{TICKETS}/t1", a_ticket())
    stub.on("POST", f"{TICKETS}/t1/move", [a_ticket(status="DONE")])
    stub.on("GET", f"{TICKETS}/t1", a_ticket(status="DONE"))

    call(stub, "update_ticket", ticket_id="t1", priority="LOW", status="DONE", index=2)

    assert ("PUT", f"{TICKETS}/t1") in stub.calls
    assert ("POST", f"{TICKETS}/t1/move") in stub.calls
    assert stub.bodies[stub.calls.index(("POST", f"{TICKETS}/t1/move"))] == {
        "status": "DONE",
        "index": 2,
    }


def test_an_update_with_nothing_to_change_makes_no_write_call(stub: StubApi) -> None:
    stub.on("GET", f"{TICKETS}/t1", a_ticket())

    call(stub, "update_ticket", ticket_id="t1")

    assert stub.paths("PUT") == []
    assert stub.paths("POST") == []


# --- creation and comments ------------------------------------------------


def test_create_ticket_lets_the_server_decide_status_and_position(stub: StubApi) -> None:
    stub.on("POST", TICKETS, a_ticket(status="BACKLOG"))

    call(stub, "create_ticket", title="Broken filter", description="On /products")

    body = stub.bodies[0]
    assert body["title"] == "Broken filter"
    assert "status" not in body
    assert "sort_order" not in body


def test_comment_posts_the_body_only(stub: StubApi) -> None:
    stub.on("POST", f"{TICKETS}/t1/comments", a_ticket())

    call(stub, "comment_on_ticket", ticket_id="t1", body="Fixed in PR #99")

    assert stub.bodies[0] == {"body": "Fixed in PR #99"}


# --- reads -----------------------------------------------------------------


def test_list_tickets_filters_by_status_priority_assignee_and_title(stub: StubApi) -> None:
    stub.on(
        "GET",
        TICKETS,
        [
            a_ticket(id="t1", status="TODO", priority="HIGH"),
            a_ticket(id="t2", status="DONE", priority="HIGH"),
            a_ticket(id="t3", status="TODO", priority="LOW", title="Map pin drifts"),
            a_ticket(id="t4", status="TODO", priority="HIGH", assignee=None),
        ],
    )

    assert [t["id"] for t in call(stub, "list_tickets", status="TODO")] == ["t1", "t3", "t4"]
    assert [t["id"] for t in call(stub, "list_tickets", priority="LOW")] == ["t3"]
    assert [t["id"] for t in call(stub, "list_tickets", query="map pin")] == ["t3"]
    assert [
        t["id"] for t in call(stub, "list_tickets", assignee_email="dev@example.com")
    ] == ["t1", "t2", "t3"]


def test_an_unassigned_ticket_does_not_crash_the_assignee_filter(stub: StubApi) -> None:
    stub.on("GET", TICKETS, [a_ticket(assignee=None)])

    assert call(stub, "list_tickets", assignee_email="dev@example.com") == []


def test_business_listings_are_readable_in_any_status(stub: StubApi) -> None:
    stub.on("GET", "/api/admin/businesses", {"items": [{"name": "A shop"}]})

    call(stub, "list_businesses", status="PENDING_REVIEW", query="shop")

    assert ("GET", "/api/admin/businesses") in stub.calls


def test_taxonomy_reads_all_three_vocabularies(stub: StubApi) -> None:
    stub.on("GET", "/api/admin/categories", [{"slug": "food"}])
    stub.on("GET", "/api/admin/locations", [{"slug": "tyre"}])
    stub.on("GET", "/api/admin/talent-skills", [{"slug": "welding"}])

    result = call(stub, "list_taxonomy")

    assert set(result) == {"categories", "locations", "talent_skills"}


# --- the shape of the tool list ------------------------------------------


def test_no_tool_can_moderate_a_listing_or_read_a_personal_document() -> None:
    """Approving or suspending a listing decides whether a real person's shop
    is visible, and the verification documents are scans of identity papers.
    Neither belongs behind a tool an agent can reach from ticket text."""
    names = {tool.name for tool in tools_of(StubApi())}
    forbidden = {"approve", "reject", "suspend", "reactivate", "delete", "document", "download"}

    assert not [name for name in names if any(word in name for word in forbidden)]


def test_every_tool_declares_whether_it_writes() -> None:
    for tool in tools_of(StubApi()):
        assert tool.annotations is not None, tool.name
        assert tool.annotations.read_only_hint is not None, tool.name
