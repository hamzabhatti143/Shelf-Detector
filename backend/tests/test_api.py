import os
import tempfile

_TMP = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/test.db"
os.environ["DETECTOR"] = "mock"
os.environ["UPLOAD_DIR"] = f"{_TMP}/uploads"

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.detectors.base import Box, Detection  # noqa: E402
from app.main import app  # noqa: E402
from app.services.audit_service import build_issues  # noqa: E402


def _jpeg() -> bytes:
    rng = np.random.default_rng(0)
    image = rng.integers(0, 255, (480, 640, 3), dtype=np.uint8)
    ok, buffer = cv2.imencode(".jpg", image)
    assert ok
    return buffer.tobytes()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _post(client: TestClient, store_id: str = "clifton"):
    return client.post(
        "/v1/audits",
        files={"image": ("shelf.jpg", _jpeg(), "image/jpeg")},
        data={"store_id": store_id},
    )


def test_health(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "detector": "mock"}


def test_stores(client):
    assert len(client.get("/v1/stores").json()) == 3


def test_create_and_fetch_audit(client):
    response = _post(client)
    assert response.status_code == 201
    body = response.json()
    assert body["isDemo"] is True
    assert body["storeName"] == "Al-Noor Mart, Clifton"
    assert len(body["issues"]) == 2  # headroom false alarm is filtered out
    assert {i["type"] for i in body["issues"]} == {"out_of_stock"}

    fetched = client.get(f"/v1/audits/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]

    image = client.get(body["imageUrl"])
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/")

    assert any(a["id"] == body["id"] for a in client.get("/v1/audits").json())
    assert client.get("/v1/stats").status_code == 200


def test_unknown_store(client):
    assert _post(client, "nowhere").status_code == 422


def test_not_an_image(client):
    response = client.post(
        "/v1/audits",
        files={"image": ("a.txt", b"hello", "text/plain")},
        data={"store_id": "clifton"},
    )
    assert response.status_code == 415


def test_corrupt_image(client):
    response = client.post(
        "/v1/audits",
        files={"image": ("a.jpg", b"not really a jpeg", "image/jpeg")},
        data={"store_id": "clifton"},
    )
    assert response.status_code == 422


def test_audit_not_found(client):
    assert client.get("/v1/audits/aud_missing").status_code == 404


def test_headroom_empty_is_filtered():
    products = [Box(10 + i * 60, 100, 60 + i * 60, 200) for i in range(5)]
    headroom = Box(20, 0, 120, 40)  # above the products, no overlap
    real_gap = Box(310, 100, 420, 200)  # on the shelf, same height as products
    detection = Detection(width=640, height=480, products=products, empties=[headroom, real_gap])
    issues = build_issues(detection, get_settings())
    assert len(issues) == 1
    assert issues[0].shelf == 1