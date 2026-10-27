from app.config import get_settings
from app.constants import Severity
from app.detectors.base import Box, Detection
from app.detectors.fusion import fuse_scales, verify_empties
from app.services.audit_service import build_issues


def test_fuse_scales_requires_agreement():
    x = Box(0, 0, 100, 100, 0.30)
    x_again = Box(2, 2, 102, 102, 0.35)
    only_once = Box(300, 300, 400, 400, 0.30)
    confident = Box(600, 0, 700, 100, 0.90)
    out = fuse_scales([[x, only_once], [x_again, confident]], iou_thr=0.55, min_votes=2, solo_conf=0.55)
    assert {(round(b.x1), round(b.y1)) for b in out} == {(2, 2), (600, 0)}


def test_empty_inside_product_is_rejected():
    product = Box(100, 100, 200, 300)
    label_false_alarm = Box(120, 150, 180, 250, 0.20)
    real_gap = Box(400, 100, 480, 300, 0.15)
    verdicts = verify_empties([label_false_alarm, real_gap], [product], max_overlap=0.30, dedup_iou=0.45)
    assert [v.box for v in verdicts if v.kept] == [real_gap]


def test_low_confidence_empty_is_reported_as_possible():
    products = [Box(10 + i * 60, 100, 60 + i * 60, 200) for i in range(5)]
    gap = Box(310, 100, 420, 200, conf=0.2)
    detection = Detection(width=640, height=480, products=products, empties=[gap])
    issues = build_issues(detection, get_settings())
    assert len(issues) == 1
    assert issues[0].severity == Severity.LOW
    assert issues[0].title.startswith("Possible")