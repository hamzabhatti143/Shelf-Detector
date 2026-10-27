import os
import tempfile

_TMP = tempfile.mkdtemp()
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TMP}/tags.db")
os.environ.setdefault("DETECTOR", "mock")
os.environ.setdefault("UPLOAD_DIR", f"{_TMP}/uploads")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.detectors.base import Box  # noqa: E402
from app.main import app  # noqa: E402
from app.services.price_tags import (  # noqa: E402
    OcrToken,
    PriceTagReading,
    inside_fraction,
    parse_price,
    read_line,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("179", 179.0),
        ("599", 599.0),
        ("2.29", 2.29),
        ("2,29", 2.29),
        ("4.50", 4.5),
        ("12.5", 12.5),
        ("$2.29", 2.29),
        ("Rs 450", 450.0),
        ("1,299.50", 1299.5),
        ("1.299,50", 1299.5),
        ("1,000,000", 1000000.0),
        ("1,00,000", 100000.0),
        (".50", 0.5),
        ("١٧٩", 179.0),
        ("٢٫٢٩", 2.29),
        ("۱۷۹", 179.0),
        ("1,299", None),
        ("1.299", None),
        ("1.2345", None),
        ("2.29 3.99", None),
        ("abc", None),
        ("", None),
        ("0", None),
    ],
)
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_big_digit_with_raised_small_digits_is_read_as_printed():
    big = OcrToken(10, 20, 50, 80, "5", 0.9)
    small = OcrToken(55, 20, 85, 45, "99", 0.8)
    below = OcrToken(55, 90, 90, 110, "375", 0.9)  # weight, printed on another line
    assert read_line([big, small, below], join=True) == ("599", 599.0, 0.8)


def test_single_price_token_is_not_changed():
    token = OcrToken(0, 0, 80, 40, "179", 0.95)
    assert read_line([token], join=True) == ("179", 179.0, 0.95)


def test_no_numbers_found():
    assert read_line([OcrToken(0, 0, 10, 10, "abc", 0.9)], join=True) is None


def test_whole_tag_crop_takes_only_the_tallest_number():
    big = OcrToken(10, 10, 90, 60, "450", 0.9)
    barcode = OcrToken(10, 70, 60, 85, "12345", 0.9)
    assert read_line([big, barcode], join=False)[0] == "450"


def test_inside_fraction():
    tag = Box(0, 0, 100, 100)
    assert inside_fraction(Box(10, 10, 50, 40), tag) == 1.0
    assert inside_fraction(Box(150, 0, 200, 50), tag) == 0.0


class StubReader:
    def read(self, image):
        return [PriceTagReading(box=Box(10, 20, 110, 70, 0.9), text="2.29", price=2.29, ocr_confidence=0.8)]


class BrokenReader:
    def read(self, image):
        raise RuntimeError("boom")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _post(client):
    rng = np.random.default_rng(0)
    ok, buffer = cv2.imencode(".jpg", rng.integers(0, 255, (480, 640, 3), dtype=np.uint8))
    assert ok
    return client.post(
        "/v1/audits",
        files={"image": ("shelf.jpg", buffer.tobytes(), "image/jpeg")},
        data={"store_id": "clifton"},
    )


def test_price_tags_reach_the_report(client, monkeypatch):
    monkeypatch.setattr(app.state.audit_service, "_tag_reader", StubReader())
    response = _post(client)
    assert response.status_code == 201
    tags = response.json()["priceTags"]
    assert len(tags) == 1
    assert tags[0]["text"] == "2.29"
    assert tags[0]["price"] == 2.29
    assert 0 <= tags[0]["box"]["x"] <= 100


def test_broken_tag_reader_does_not_break_the_audit(client, monkeypatch):
    monkeypatch.setattr(app.state.audit_service, "_tag_reader", BrokenReader())
    response = _post(client)
    assert response.status_code == 201
    assert response.json()["priceTags"] == []