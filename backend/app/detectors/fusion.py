from dataclasses import dataclass

import numpy as np

from app.constants import REASON_COVERED, REASON_DUPLICATE, REASON_KEPT

from .base import Box


@dataclass(frozen=True, slots=True)
class EmptyVerdict:
    box: Box
    kept: bool
    reason: str


def _as_array(boxes: list[Box]) -> np.ndarray:
    return np.array([[b.x1, b.y1, b.x2, b.y2] for b in boxes], dtype=float).reshape(-1, 4)


def iou_one_to_many(box: np.ndarray, others: np.ndarray) -> np.ndarray:
    if others.size == 0:
        return np.zeros(0)
    x1 = np.maximum(box[0], others[:, 0])
    y1 = np.maximum(box[1], others[:, 1])
    x2 = np.minimum(box[2], others[:, 2])
    y2 = np.minimum(box[3], others[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (box[2] - box[0]) * (box[3] - box[1])
    area_b = (others[:, 2] - others[:, 0]) * (others[:, 3] - others[:, 1])
    return inter / np.maximum(area_a + area_b - inter, 1e-9)


def fuse_scales(
    per_scale: list[list[Box]], iou_thr: float, min_votes: int, solo_conf: float
) -> list[Box]:
    """Keep a box only if at least `min_votes` scales found it, or it is very confident.
    Junk that appears at a single scale (patterns, label fragments) gets dropped."""
    min_votes = max(1, min(min_votes, len(per_scale)))
    candidates = [(box, idx) for idx, boxes in enumerate(per_scale) for box in boxes]
    candidates.sort(key=lambda item: item[0].conf, reverse=True)

    leaders: list[Box] = []
    votes: list[set[int]] = []
    leader_arr = np.zeros((0, 4))
    for box, idx in candidates:
        arr = np.array([box.x1, box.y1, box.x2, box.y2], dtype=float)
        ious = iou_one_to_many(arr, leader_arr)
        if ious.size and ious.max() >= iou_thr:
            votes[int(ious.argmax())].add(idx)
            continue
        leaders.append(box)
        votes.append({idx})
        leader_arr = np.vstack([leader_arr, arr])

    return [
        box for box, seen in zip(leaders, votes) if len(seen) >= min_votes or box.conf >= solo_conf
    ]


def covered_fraction(box: Box, others: list[Box]) -> float:
    """Fraction of `box` area covered by `others` (capped at 1)."""
    area = box.width * box.height
    if area <= 0 or not others:
        return 0.0
    arr = _as_array(others)
    x1 = np.maximum(box.x1, arr[:, 0])
    y1 = np.maximum(box.y1, arr[:, 1])
    x2 = np.minimum(box.x2, arr[:, 2])
    y2 = np.minimum(box.y2, arr[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    return float(min(inter.sum() / area, 1.0))


def verify_empties(
    candidates: list[Box], products: list[Box], max_overlap: float, dedup_iou: float
) -> list[EmptyVerdict]:
    """A real empty slot has no product in it. An 'empty' box sitting on a product
    (for example on a can label) is a false alarm."""
    verdicts: list[EmptyVerdict] = []
    kept_arr = np.zeros((0, 4))
    for box in sorted(candidates, key=lambda b: b.conf, reverse=True):
        arr = _as_array([box])[0]
        if kept_arr.size and iou_one_to_many(arr, kept_arr).max() >= dedup_iou:
            verdicts.append(EmptyVerdict(box, False, REASON_DUPLICATE))
            continue
        covered = covered_fraction(box, products)
        if covered >= max_overlap:
            verdicts.append(EmptyVerdict(box, False, REASON_COVERED.format(pct=covered * 100)))
            continue
        verdicts.append(EmptyVerdict(box, True, REASON_KEPT))
        kept_arr = np.vstack([kept_arr, arr])
    return verdicts

# ---- extra empty filters: shelf lip / headroom / frame edge ----
REASON_SLIVER = "too thin for its row ({pct:.0f}% of nearby product height), shelf lip?"
REASON_HEADROOM = "product directly below ({pct:.0f}% of width), headroom"
REASON_FRAME_EDGE = "touches frame edge with low confidence"


def _local_ref_height(box: Box, products: list[Box], k: int = 8) -> float | None:
    """Median height of the k products nearest to the candidate's centre."""
    if not products:
        return None
    arr = _as_array(products)
    cx, cy = (box.x1 + box.x2) / 2, (box.y1 + box.y2) / 2
    dist = np.hypot((arr[:, 0] + arr[:, 2]) / 2 - cx, (arr[:, 1] + arr[:, 3]) / 2 - cy)
    near = arr[np.argsort(dist)[:k]]
    return float(np.median(near[:, 3] - near[:, 1]))


def _product_below_fraction(box: Box, products: list[Box], ref_h: float) -> float:
    """Share of the candidate's width that has a product starting right under it."""
    if not products or box.width <= 0:
        return 0.0
    arr = _as_array(products)
    gap = arr[:, 1] - box.y2
    near = arr[(gap >= -0.15 * ref_h) & (gap <= 0.15 * ref_h)]
    if near.size == 0:
        return 0.0
    overlap = np.clip(np.minimum(box.x2, near[:, 2]) - np.maximum(box.x1, near[:, 0]), 0, None)
    return float(min(overlap.sum() / box.width, 1.0))


def filter_empties(
    verdicts: list[EmptyVerdict],
    products: list[Box],
    img_w: int,
    img_h: int,
    min_height_ratio: float = 0.70,
    headroom_width_frac: float = 0.50,
    edge_margin: float = 0.03,
    edge_min_conf: float = 0.40,
) -> list[EmptyVerdict]:
    out: list[EmptyVerdict] = []
    mx, my = img_w * edge_margin, img_h * edge_margin
    for v in verdicts:
        if not v.kept:
            out.append(v)
            continue
        b = v.box
        ref_h = _local_ref_height(b, products)
        if ref_h and b.height < min_height_ratio * ref_h:
            out.append(EmptyVerdict(b, False, REASON_SLIVER.format(pct=b.height / ref_h * 100)))
            continue
        if ref_h:
            frac = _product_below_fraction(b, products, ref_h)
            if frac >= headroom_width_frac:
                out.append(EmptyVerdict(b, False, REASON_HEADROOM.format(pct=frac * 100)))
                continue
        touches = b.x1 <= mx or b.y1 <= my or b.x2 >= img_w - mx or b.y2 >= img_h - my
        if touches and b.conf < edge_min_conf:
            out.append(EmptyVerdict(b, False, REASON_FRAME_EDGE))
            continue
        out.append(v)
    return out

def drop_small_background(products: list[Box], ratio: float, min_count: int = 12) -> list[Box]:
    """Aisle products in the background are far smaller than the main shelf's."""
    if len(products) < min_count:
        return products
    areas = np.array([b.width * b.height for b in products])
    ref = float(np.percentile(areas, 75))
    return [b for b, a in zip(products, areas) if a >= ratio * ref]

def suppress_contained(boxes: list[Box], min_cover: float) -> list[Box]:
    """Drop a box that lies (almost) entirely inside a bigger one: a duplicate from another
    scale, or a part of the same product (a bottle cap inside its bottle)."""
    if len(boxes) < 2 or min_cover > 1.0:
        return boxes
    ordered = sorted(boxes, key=lambda b: b.width * b.height, reverse=True)
    kept: list[Box] = []
    kept_arr = np.zeros((0, 4))
    for box in ordered:
        area = box.width * box.height
        if area <= 0:
            continue
        if kept_arr.size:
            w = np.clip(np.minimum(box.x2, kept_arr[:, 2]) - np.maximum(box.x1, kept_arr[:, 0]), 0, None)
            h = np.clip(np.minimum(box.y2, kept_arr[:, 3]) - np.maximum(box.y1, kept_arr[:, 1]), 0, None)
            if (w * h / area).max() >= min_cover:
                continue
        kept.append(box)
        kept_arr = np.vstack([kept_arr, [box.x1, box.y1, box.x2, box.y2]])
    return kept