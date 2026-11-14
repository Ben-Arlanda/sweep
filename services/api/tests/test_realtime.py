"""Change notices: a commit in one Member's request reaches the other Members' devices.

The end-to-end tests use Starlette's TestClient (it supports WebSockets and runs the app's
startup, so the real Postgres LISTEN loop is running). Everything else uses httpx.
"""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from starlette.websockets import WebSocketDisconnect

from app.config import Settings
from app.main import create_app
from app.realtime import Hub
from tests.conftest import FakeIssuer

pytestmark = pytest.mark.timeout(10)  # a missing notice would otherwise hang forever


# --- Hub (in-memory fan-out) ---------------------------------------------------------


def test_hub_only_delivers_to_the_households_subscribers() -> None:
    hub = Hub()
    ours, theirs = uuid.uuid4(), uuid.uuid4()
    mine, other = hub.subscribe(ours), hub.subscribe(theirs)

    hub.publish(ours, {"type": "changed"})

    assert mine.get_nowait() == {"type": "changed"}
    assert other.empty()


def test_a_slow_subscriber_is_told_to_resync_instead_of_growing_forever() -> None:
    hub = Hub(queue_size=2)
    household = uuid.uuid4()
    queue = hub.subscribe(household)

    for n in range(5):
        hub.publish(household, {"type": "changed", "version": n})

    # It missed some notices, so the only useful message left is "refetch everything".
    assert queue.get_nowait() == {"type": "resync"}
    assert queue.empty()


def test_unsubscribe_stops_delivery() -> None:
    hub = Hub()
    household = uuid.uuid4()
    queue = hub.subscribe(household)

    hub.unsubscribe(household, queue)
    hub.publish(household, {"type": "changed"})

    assert queue.empty()
    assert hub.subscriber_count() == 0


def test_resync_reaches_everyone() -> None:
    hub = Hub()
    a, b = hub.subscribe(uuid.uuid4()), hub.subscribe(uuid.uuid4())

    hub.publish_all({"type": "resync"})

    assert a.get_nowait() == b.get_nowait() == {"type": "resync"}


# --- End to end through Postgres ----------------------------------------------------


@pytest.fixture
def live(database_url: str, db: Engine, fake_issuer: FakeIssuer) -> Iterator[TestClient]:
    app = create_app(Settings(database_url=database_url), token_verifier=fake_issuer.verifier())
    with TestClient(app) as client:  # `with` runs startup, which starts the listener
        yield client


def headers(issuer: FakeIssuer, subject: str) -> dict[str, str]:
    return issuer.headers(subject) | {"Idempotency-Key": str(uuid.uuid4())}


def setup_household(client: TestClient, issuer: FakeIssuer, owner: str, *joiners: str) -> str:
    r = client.post(
        "/households", json={"name": "H", "display_name": owner}, headers=headers(issuer, owner)
    )
    assert r.status_code == 201, r.text
    for joiner in joiners:
        code = client.post("/households/current/invites", headers=headers(issuer, owner)).json()[
            "code"
        ]
        r = client.post(
            f"/invites/{code}/accept",
            json={"display_name": joiner},
            headers=headers(issuer, joiner),
        )
        assert r.status_code == 200, r.text
    list_id: str = client.get("/lists", headers=issuer.headers(owner)).json()[0]["id"]
    return list_id


def add(client: TestClient, issuer: FakeIssuer, subject: str, list_id: str) -> None:
    r = client.post(
        f"/lists/{list_id}/items", json={"text": "Milk"}, headers=headers(issuer, subject)
    )
    assert r.status_code == 201, r.text


def test_other_members_are_told_when_the_list_changes(
    live: TestClient, fake_issuer: FakeIssuer
) -> None:
    list_id = setup_household(live, fake_issuer, "alice", "bob")

    with live.websocket_connect("/ws") as bob:
        bob.send_json({"type": "auth", "token": fake_issuer.token("bob")})
        assert bob.receive_json() == {"type": "subscribed"}

        add(live, fake_issuer, "alice", list_id)

        notice: dict[str, Any] = bob.receive_json()
        # An id and a version, never the data: Bob refetches through the normal API,
        # so permission checks still apply.
        assert notice == {
            "type": "changed",
            "entity": "shopping_list",
            "id": list_id,
            "version": 2,
        }


def test_notices_never_cross_households(live: TestClient, fake_issuer: FakeIssuer) -> None:
    alices_list = setup_household(live, fake_issuer, "alice")
    mallorys_list = setup_household(live, fake_issuer, "mallory")

    with live.websocket_connect("/ws") as mallory:
        mallory.send_json({"type": "auth", "token": fake_issuer.token("mallory")})
        assert mallory.receive_json() == {"type": "subscribed"}

        add(live, fake_issuer, "alice", alices_list)
        add(live, fake_issuer, "mallory", mallorys_list)

        # Notices arrive in commit order, so if Alice's had leaked it would come first.
        assert mallory.receive_json()["id"] == mallorys_list


def test_a_rolled_back_change_sends_no_notice(live: TestClient, fake_issuer: FakeIssuer) -> None:
    list_id = setup_household(live, fake_issuer, "alice")

    with live.websocket_connect("/ws") as alice:
        alice.send_json({"type": "auth", "token": fake_issuer.token("alice")})
        assert alice.receive_json() == {"type": "subscribed"}

        # Fails validation inside the service, after the list version was bumped and the
        # NOTIFY was queued. Postgres throws both away on rollback.
        missing = f"/lists/{list_id}/items/{uuid.uuid4()}"
        assert (
            live.patch(
                missing, json={"text": "x"}, headers=headers(fake_issuer, "alice")
            ).status_code
            == 404
        )
        add(live, fake_issuer, "alice", list_id)

        assert alice.receive_json()["version"] == 2


def test_socket_rejects_a_bad_token(live: TestClient) -> None:
    with live.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": "not-a-jwt"})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 4401


def test_socket_rejects_someone_without_a_household(
    live: TestClient, fake_issuer: FakeIssuer
) -> None:
    with live.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": fake_issuer.token("nobody")})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 4403


def test_socket_rejects_a_first_message_that_is_not_auth(live: TestClient) -> None:
    with live.websocket_connect("/ws") as ws:
        ws.send_json({"type": "hello"})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 4401
