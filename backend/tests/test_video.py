import os
import tempfile

_TMP = tempfile.mkdtemp()
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TMP}/video.db")
os.environ.setdefault("DETECTOR", "mock")
os.environ.setdefault("UPLOAD_DIR", f"{_TMP}/uploads")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.detectors.base import Box  # noqa: E402
from app.main import app  # noqa: E402
from app.services.video_service import stable_empties  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _write_video(path, frames: int = 20) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (320, 240))
    if not writer.isOpened():
        pytest.skip("OpenCV cannot write mp4 here")
    rng = np.random.default_rng(1)
    for _ in range(frames):
        writer.write(rng.integers(0, 255, (240, 320, 3), dtype=np.uint8))
    writer.release()


def test_stable_empties_needs_repeat_sightings():
    a = Box(100, 100, 200, 200)
    a_again = Box(102, 101, 201, 202)
    flicker = Box(500, 500, 560, 560)
    result = stable_empties([[a, flicker], [a_again], []], iou_thr=0.3, min_seen=2)
    assert result[0] == [a]
    assert result[1] == [a_again]
    assert result[2] == []


def test_video_job_flow(client, tmp_path):
    video = tmp_path / "shelf.mp4"
    _write_video(video)
    with video.open("rb") as f:
        response = client.post(
            "/v1/video-audits",
            files={"video": ("shelf.mp4", f, "video/mp4")},
            data={"store_id": "clifton"},
        )
    assert response.status_code == 202
    job_id = response.json()["jobId"]

    job = client.get(f"/v1/video-audits/{job_id}").json()
    assert job["status"] == "done", job
    report = client.get(f"/v1/audits/{job['auditId']}").json()
    assert report["framesAnalyzed"] >= 1
    assert report["isDemo"] is True


def test_video_rejects_non_video(client):
    response = client.post(
        "/v1/video-audits",
        files={"video": ("a.txt", b"hello", "text/plain")},
        data={"store_id": "clifton"},
    )
    assert response.status_code == 415


def test_unknown_job(client):
    assert client.get("/v1/video-audits/job_missing").status_code == 404