"""Bug/feedback ticketing, its Kanban board, and owner reporting.

Two things matter here. The board's own bookkeeping — column order,
resolved_at, attachment and comment counts — must stay correct across a drag.
And the boundary between reporting and triaging must hold: any signed-in
account may report a problem, but reporting grants no view of the board, not
even of the ticket the reporter filed, because reading one back would show
the board's internal state and an administrator's notes on it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.feedback import FeedbackTicket
from app.models.user import User
from tests.conftest import admin_headers, sign_in
from tests.samples import ar


def _create(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    payload = {"title": ar("feedback.bug_title"), "priority": "MEDIUM"}
    payload.update(overrides)
    response = client.post("/api/admin/feedback/tickets", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- Authorization -----------------------------------------------------


def test_owner_routes_are_rejected(client: TestClient) -> None:
    """A business/talent owner is not an administrator and has no business
    on this board at all."""
    headers = sign_in(client, "03960001")
    assert client.get("/api/admin/feedback/tickets", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/admin/feedback/tickets", headers=headers, json={"title": ar("feedback.bug_title")}
        ).status_code
        == 403
    )


def test_unauthenticated_is_rejected(client: TestClient) -> None:
    assert client.get("/api/admin/feedback/tickets").status_code == 401


# --- Creation and the board ---------------------------------------------


def test_new_ticket_lands_in_backlog(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    ticket = _create(client, headers)
    assert ticket["status"] == "BACKLOG"
    assert ticket["sort_order"] == 0
    assert ticket["reporter"]["email"] == admin.email
    assert ticket["assignee"] is None
    assert ticket["attachment_count"] == 0
    assert ticket["comment_count"] == 0


def test_board_lists_every_ticket_ordered_by_column_then_position(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    first = _create(client, headers, title=ar("feedback.bug_title"))
    second = _create(client, headers, title=ar("feedback.feature_title"))

    board = client.get("/api/admin/feedback/tickets", headers=headers).json()
    ids = [t["id"] for t in board]
    assert ids == [first["id"], second["id"]]
    assert [t["sort_order"] for t in board] == [0, 1]


# --- Moving across the board ---------------------------------------------


def test_move_to_another_column_renumbers_both_columns(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    first = _create(client, headers, title=ar("feedback.bug_title"))
    second = _create(client, headers, title=ar("feedback.feature_title"))

    moved = client.post(
        f"/api/admin/feedback/tickets/{first['id']}/move",
        headers=headers,
        json={"status": "IN_PROGRESS", "index": 0},
    )
    assert moved.status_code == 200, moved.text
    board = {t["id"]: t for t in moved.json()}

    # The moved ticket is alone in its new column at position 0...
    assert board[first["id"]]["status"] == "IN_PROGRESS"
    assert board[first["id"]]["sort_order"] == 0
    # ...and the ticket left behind closes the gap in BACKLOG.
    assert board[second["id"]]["status"] == "BACKLOG"
    assert board[second["id"]]["sort_order"] == 0


def test_reorder_within_the_same_column(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    first = _create(client, headers, title=ar("feedback.bug_title"))
    second = _create(client, headers, title=ar("feedback.feature_title"))

    # Move the second ticket ahead of the first, within BACKLOG.
    moved = client.post(
        f"/api/admin/feedback/tickets/{second['id']}/move",
        headers=headers,
        json={"status": "BACKLOG", "index": 0},
    )
    assert moved.status_code == 200, moved.text
    board = moved.json()
    assert [t["id"] for t in board] == [second["id"], first["id"]]
    assert [t["sort_order"] for t in board] == [0, 1]


def test_moving_into_done_sets_resolved_at_and_moving_out_clears_it(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    ticket = _create(client, headers)

    done = client.post(
        f"/api/admin/feedback/tickets/{ticket['id']}/move",
        headers=headers,
        json={"status": "DONE", "index": 0},
    )
    assert done.status_code == 200, done.text
    detail = client.get(f"/api/admin/feedback/tickets/{ticket['id']}", headers=headers).json()
    assert detail["status"] == "DONE"
    assert detail["resolved_at"] is not None

    reopened = client.post(
        f"/api/admin/feedback/tickets/{ticket['id']}/move",
        headers=headers,
        json={"status": "TODO", "index": 0},
    )
    assert reopened.status_code == 200, reopened.text
    detail = client.get(f"/api/admin/feedback/tickets/{ticket['id']}", headers=headers).json()
    assert detail["status"] == "TODO"
    assert detail["resolved_at"] is None


# --- Update, assignment, comments -----------------------------------------


def test_update_edits_fields_without_touching_status(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    ticket = _create(client, headers)

    updated = client.put(
        f"/api/admin/feedback/tickets/{ticket['id']}",
        headers=headers,
        json={"priority": "URGENT", "description": ar("feedback.bug_description")},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["priority"] == "URGENT"
    assert body["description"] == ar("feedback.bug_description")
    assert body["status"] == "BACKLOG"


def test_ticket_can_be_assigned_to_an_administrator(
    client: TestClient, db: Session, admin: User
) -> None:
    headers = admin_headers(client)
    ticket = _create(client, headers)

    second_admin = User(email="second-admin@example.com", role=UserRole.ADMIN, display_name="second")
    db.add(second_admin)
    db.commit()

    assignees = client.get("/api/admin/feedback/assignees", headers=headers).json()
    assert {a["email"] for a in assignees} == {admin.email, second_admin.email}

    assigned = client.put(
        f"/api/admin/feedback/tickets/{ticket['id']}",
        headers=headers,
        json={"assignee_id": str(second_admin.id)},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assignee"]["email"] == second_admin.email


def test_assigning_to_a_non_admin_is_rejected(
    client: TestClient, db: Session, admin: User
) -> None:
    """The picker only ever offers administrators, but the API must not
    trust a request-supplied id blindly — an owner id must not silently
    become a valid assignee."""
    headers = admin_headers(client)
    ticket = _create(client, headers)

    owner = User(phone_number="+9613960099", role=UserRole.OWNER)
    db.add(owner)
    db.commit()

    response = client.put(
        f"/api/admin/feedback/tickets/{ticket['id']}",
        headers=headers,
        json={"assignee_id": str(owner.id)},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_assignee"


def test_comments_accumulate_and_are_counted(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    ticket = _create(client, headers)

    commented = client.post(
        f"/api/admin/feedback/tickets/{ticket['id']}/comments",
        headers=headers,
        json={"body": ar("feedback.comment_repro")},
    )
    assert commented.status_code == 200, commented.text
    body = commented.json()
    assert body["comment_count"] == 1
    assert body["comments"][0]["body"] == ar("feedback.comment_repro")
    assert body["comments"][0]["author_display_name"] == admin.display_name


# --- Deletion --------------------------------------------------------------


def test_delete_removes_the_ticket(client: TestClient, db: Session, admin: User) -> None:
    headers = admin_headers(client)
    ticket = _create(client, headers)

    deleted = client.delete(f"/api/admin/feedback/tickets/{ticket['id']}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert client.get(f"/api/admin/feedback/tickets/{ticket['id']}", headers=headers).status_code == 404
    assert db.get(FeedbackTicket, ticket["id"]) is None


def test_getting_an_unknown_ticket_404s(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    response = client.get(
        "/api/admin/feedback/tickets/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404


# --- Attachments -------------------------------------------------------


@pytest.fixture
def jpeg_bytes() -> bytes:
    # The attachment service only sniffs the three-byte JPEG magic number —
    # unlike ImageService, it never decodes the file — so padding after the
    # header is all a test needs.
    return b"\xff\xd8\xff" + b"\x00" * 64


def test_upload_and_download_a_screenshot_attachment(
    client: TestClient, admin: User, jpeg_bytes: bytes
) -> None:
    headers = admin_headers(client)
    ticket = _create(client, headers)

    uploaded = client.post(
        f"/api/admin/feedback/tickets/{ticket['id']}/attachments",
        headers=headers,
        files={"file": ("screenshot.jpg", jpeg_bytes, "image/jpeg")},
        data={"kind": "SCREENSHOT"},
    )
    assert uploaded.status_code == 201, uploaded.text
    body = uploaded.json()
    assert body["attachment_count"] == 1
    attachment = body["attachments"][0]
    assert attachment["kind"] == "SCREENSHOT"

    downloaded = client.get(
        f"/api/admin/feedback/tickets/{ticket['id']}/attachments/{attachment['id']}/download",
        headers=headers,
    )
    assert downloaded.status_code == 200
    assert downloaded.content == jpeg_bytes

    deleted = client.delete(
        f"/api/admin/feedback/tickets/{ticket['id']}/attachments/{attachment['id']}",
        headers=headers,
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["attachment_count"] == 0


def test_a_document_tagged_photo_is_rejected(client: TestClient, admin: User) -> None:
    """The client-supplied kind must match what the bytes actually are — a
    PDF cannot masquerade as a photo, the same distrust the image and
    verification-document pipelines already apply."""
    headers = admin_headers(client)
    ticket = _create(client, headers)

    response = client.post(
        f"/api/admin/feedback/tickets/{ticket['id']}/attachments",
        headers=headers,
        files={"file": ("doc.pdf", b"%PDF-1.4\n%fake pdf body", "application/pdf")},
        data={"kind": "PHOTO"},
    )
    assert response.status_code == 415


def test_attachment_limit_is_enforced(client: TestClient, admin: User, jpeg_bytes: bytes) -> None:
    headers = admin_headers(client)
    ticket = _create(client, headers)

    for _ in range(8):
        response = client.post(
            f"/api/admin/feedback/tickets/{ticket['id']}/attachments",
            headers=headers,
            files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
            data={"kind": "PHOTO"},
        )
        assert response.status_code == 201, response.text

    over_limit = client.post(
        f"/api/admin/feedback/tickets/{ticket['id']}/attachments",
        headers=headers,
        files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
        data={"kind": "PHOTO"},
    )
    assert over_limit.status_code == 422
    assert over_limit.json()["error"]["code"] == "attachment_limit_reached"


# --- Owner reporting -----------------------------------------------------
#
# The widget is shown to every signed-in account, so the endpoint behind it
# has to accept one. What an owner must NOT gain is any view of the board.


def test_an_owner_can_report_a_problem(client: TestClient) -> None:
    headers = sign_in(client, "03960001")

    response = client.post(
        "/api/feedback",
        headers=headers,
        json={
            "title": ar("feedback.bug_title"),
            "description": ar("feedback.bug_description"),
            "page_path": "/products",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == ar("feedback.bug_title")
    assert set(body) == {"id", "title", "created_at"}


def test_a_reported_ticket_reaches_the_board_in_the_backlog(
    client: TestClient, admin: User
) -> None:
    owner = sign_in(client, "03960001")
    client.post("/api/feedback", headers=owner, json={"title": ar("feedback.bug_title")})

    board = client.get("/api/admin/feedback/tickets", headers=admin_headers(client)).json()
    reported = [t for t in board if t["title"] == ar("feedback.bug_title")]
    assert len(reported) == 1
    assert reported[0]["status"] == "BACKLOG"


def test_a_reporter_does_not_set_their_own_priority(client: TestClient, admin: User) -> None:
    """Asked to rank their own problem everyone answers urgent, so the field
    would carry no information. The widget hides the picker; this is the half
    a direct post cannot get around."""
    owner = sign_in(client, "03960001")
    client.post(
        "/api/feedback",
        headers=owner,
        json={"title": ar("feedback.bug_title"), "priority": "URGENT"},
    )

    board = client.get("/api/admin/feedback/tickets", headers=admin_headers(client)).json()
    assert board[0]["priority"] == "MEDIUM"


def test_reporting_still_grants_no_view_of_the_board(client: TestClient) -> None:
    headers = sign_in(client, "03960001")
    submitted = client.post(
        "/api/feedback", headers=headers, json={"title": ar("feedback.bug_title")}
    ).json()
    ticket_id = submitted["id"]

    # Not even the ticket they filed themselves: reading it back would show
    # the board's internal state, and an administrator's notes on it.
    assert client.get("/api/admin/feedback/tickets", headers=headers).status_code == 403
    assert (
        client.get(f"/api/admin/feedback/tickets/{ticket_id}", headers=headers).status_code == 403
    )
    assert (
        client.put(
            f"/api/admin/feedback/tickets/{ticket_id}",
            headers=headers,
            json={"priority": "URGENT"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/admin/feedback/tickets/{ticket_id}/move",
            headers=headers,
            json={"status": "DONE", "index": 0},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/admin/feedback/tickets/{ticket_id}/comments",
            headers=headers,
            json={"body": ar("feedback.comment_repro")},
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/admin/feedback/tickets/{ticket_id}", headers=headers).status_code
        == 403
    )


def test_reporting_requires_an_account(client: TestClient) -> None:
    response = client.post("/api/feedback", json={"title": ar("feedback.bug_title")})

    assert response.status_code == 401


def test_a_reporter_can_attach_a_screenshot_to_their_own_report(
    client: TestClient, admin: User, jpeg_bytes: bytes
) -> None:
    headers = sign_in(client, "03960001")
    submitted = client.post(
        "/api/feedback", headers=headers, json={"title": ar("feedback.bug_title")}
    ).json()

    response = client.post(
        f"/api/feedback/{submitted['id']}/attachments",
        headers=headers,
        files={"file": ("shot.jpg", jpeg_bytes, "image/jpeg")},
        data={"kind": "SCREENSHOT"},
    )

    assert response.status_code == 201, response.text
    detail = client.get(
        f"/api/admin/feedback/tickets/{submitted['id']}", headers=admin_headers(client)
    ).json()
    assert len(detail["attachments"]) == 1
    assert detail["attachments"][0]["kind"] == "SCREENSHOT"


def test_a_reporter_cannot_attach_to_someone_elses_ticket(
    client: TestClient, admin: User, jpeg_bytes: bytes
) -> None:
    """404 rather than 403, so the response does not confirm to one account
    that another account's ticket id exists."""
    someone_elses = _create(client, admin_headers(client))["id"]
    headers = sign_in(client, "03960001")

    response = client.post(
        f"/api/feedback/{someone_elses}/attachments",
        headers=headers,
        files={"file": ("shot.jpg", jpeg_bytes, "image/jpeg")},
        data={"kind": "SCREENSHOT"},
    )

    assert response.status_code == 404


def test_a_reporters_attachment_bytes_stay_admin_gated(
    client: TestClient, admin: User, jpeg_bytes: bytes
) -> None:
    """A screenshot can show whatever was on the reporter's screen, so the
    download route is admin-only even for the person who uploaded it."""
    headers = sign_in(client, "03960001")
    submitted = client.post(
        "/api/feedback", headers=headers, json={"title": ar("feedback.bug_title")}
    ).json()
    client.post(
        f"/api/feedback/{submitted['id']}/attachments",
        headers=headers,
        files={"file": ("shot.jpg", jpeg_bytes, "image/jpeg")},
        data={"kind": "SCREENSHOT"},
    )
    detail = client.get(
        f"/api/admin/feedback/tickets/{submitted['id']}", headers=admin_headers(client)
    ).json()
    attachment_id = detail["attachments"][0]["id"]

    response = client.get(
        f"/api/admin/feedback/tickets/{submitted['id']}/attachments/{attachment_id}/download",
        headers=headers,
    )

    assert response.status_code == 403


# --- The link to the roadmap ---------------------------------------------
#
# Without this column a triage agent can only guess which issue serves which
# ticket by comparing titles, which is exactly the guess it should not make.


def test_a_ticket_starts_with_no_linked_issue(client: TestClient, admin: User) -> None:
    assert _create(client, admin_headers(client))["github_issue_number"] is None


def test_a_ticket_can_be_linked_to_an_issue_and_unlinked_again(
    client: TestClient, admin: User
) -> None:
    headers = admin_headers(client)
    ticket = _create(client, headers)

    linked = client.put(
        f"/api/admin/feedback/tickets/{ticket['id']}",
        headers=headers,
        json={"github_issue_number": 46},
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["github_issue_number"] == 46

    unlinked = client.put(
        f"/api/admin/feedback/tickets/{ticket['id']}",
        headers=headers,
        json={"github_issue_number": None},
    )
    assert unlinked.status_code == 200, unlinked.text
    assert unlinked.json()["github_issue_number"] is None


def test_editing_something_else_leaves_the_link_alone(client: TestClient, admin: User) -> None:
    """`exclude_unset` is what makes this true, and it is the property the
    board relies on every time a card is edited."""
    headers = admin_headers(client)
    ticket = _create(client, headers)
    client.put(
        f"/api/admin/feedback/tickets/{ticket['id']}",
        headers=headers,
        json={"github_issue_number": 46},
    )

    edited = client.put(
        f"/api/admin/feedback/tickets/{ticket['id']}",
        headers=headers,
        json={"priority": "URGENT"},
    )

    assert edited.json()["github_issue_number"] == 46


def test_an_issue_number_below_one_is_rejected(client: TestClient, admin: User) -> None:
    """GitHub numbers issues from 1, so a 0 is a caller's bug. Better a 422
    than a card carrying a link that goes nowhere."""
    headers = admin_headers(client)
    ticket = _create(client, headers)

    response = client.put(
        f"/api/admin/feedback/tickets/{ticket['id']}",
        headers=headers,
        json={"github_issue_number": 0},
    )

    assert response.status_code == 422


def test_the_link_survives_a_move_across_the_board(client: TestClient, admin: User) -> None:
    headers = admin_headers(client)
    ticket = _create(client, headers)
    client.put(
        f"/api/admin/feedback/tickets/{ticket['id']}",
        headers=headers,
        json={"github_issue_number": 46},
    )

    board = client.post(
        f"/api/admin/feedback/tickets/{ticket['id']}/move",
        headers=headers,
        json={"status": "IN_PROGRESS", "index": 0},
    ).json()

    assert board[0]["github_issue_number"] == 46


def test_a_reporter_cannot_link_an_issue(client: TestClient) -> None:
    """The submission schema has no such field, so it is dropped rather than
    refused -- the ticket is still filed, just not linked."""
    headers = sign_in(client, "03960001")

    response = client.post(
        "/api/feedback",
        headers=headers,
        json={"title": ar("feedback.bug_title"), "github_issue_number": 46},
    )

    assert response.status_code == 201
    assert "github_issue_number" not in response.json()
