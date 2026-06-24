from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class BinaryMetrics:
    auc: float
    f1: float
    precision: float
    recall: float
    fpr_at_tpr_99: float
    fpr_at_tpr_95: float
    threshold_at_tpr_99: float


def binary_metrics(
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float = 0.5,
) -> BinaryMetrics:
    from sklearn.metrics import (  # type: ignore[import-not-found]
        precision_recall_fscore_support,
        roc_auc_score,
        roc_curve,
    )

    preds = (scores >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="binary", zero_division=0
    )
    auc = float(roc_auc_score(labels, scores))

    fpr_curve, tpr_curve, thresholds = roc_curve(labels, scores)
    fpr_at_tpr_99 = _fpr_at_tpr(fpr_curve, tpr_curve, target_tpr=0.99)
    fpr_at_tpr_95 = _fpr_at_tpr(fpr_curve, tpr_curve, target_tpr=0.95)
    threshold_at_tpr_99 = _threshold_at_tpr(tpr_curve, thresholds, target_tpr=0.99)

    return BinaryMetrics(
        auc=auc,
        f1=float(f1),
        precision=float(precision),
        recall=float(recall),
        fpr_at_tpr_99=fpr_at_tpr_99,
        fpr_at_tpr_95=fpr_at_tpr_95,
        threshold_at_tpr_99=threshold_at_tpr_99,
    )


def _fpr_at_tpr(fpr: np.ndarray, tpr: np.ndarray, target_tpr: float) -> float:
    idx = np.searchsorted(tpr, target_tpr, side="left")
    if idx >= len(fpr):
        return 1.0
    return float(fpr[idx])


def _threshold_at_tpr(tpr: np.ndarray, thresholds: np.ndarray, target_tpr: float) -> float:
    idx = np.searchsorted(tpr, target_tpr, side="left")
    if idx >= len(thresholds):
        return 0.0
    return float(thresholds[idx])


# ────────────────────────────────────────────────────────────────────────
# Threshold-agnostic operating-point helpers
#
# These let us compare detectors at a fixed *detection rate* rather than a
# fixed probability threshold — so the comparison no longer depends on where
# each detector's 0.5 happens to fall. All operate on raw per-prompt scores,
# so they can be computed in post from dumped scores with no model inference.
# ────────────────────────────────────────────────────────────────────────


def threshold_at_tpr(scores: np.ndarray, labels: np.ndarray, target_tpr: float) -> float:
    """Decision threshold at which the detector catches ``target_tpr`` of attacks.

    Picked from the *attack* scores only: to catch a fraction ``target_tpr`` of
    attacks, the threshold is the ``(1 - target_tpr)`` quantile of attack scores
    (so that fraction of attacks score at or above it). Returns +inf if there
    are no attack samples (nothing can be caught).
    """
    attack = np.asarray(scores, dtype=float)[np.asarray(labels, dtype=int) == 1]
    if attack.size == 0:
        return float("inf")
    return float(np.quantile(attack, 1.0 - target_tpr))


def fpr_at_threshold(benign_scores: np.ndarray, threshold: float) -> float:
    """False-positive rate on a benign-only score array at ``threshold``."""
    benign = np.asarray(benign_scores, dtype=float)
    if benign.size == 0:
        return 0.0
    return float(np.mean(benign >= threshold))


def eer(scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    """Equal-error rate and its threshold (where FPR ≈ FNR).

    Returns ``(eer, threshold)``. Computed from the ROC curve as the point that
    minimises ``|FPR - FNR|``; EER is reported as the midpoint of the two there.
    """
    from sklearn.metrics import roc_curve  # type: ignore[import-not-found]

    fpr, tpr, thresholds = roc_curve(labels, scores)
    fnr = 1.0 - tpr
    idx = int(np.argmin(np.abs(fpr - fnr)))
    eer_val = float((fpr[idx] + fnr[idx]) / 2.0)
    return eer_val, float(thresholds[idx])


def roc_points(scores: np.ndarray, labels: np.ndarray, max_points: int = 256) -> dict:
    """ROC curve points for plotting: ``{"fpr": [...], "tpr": [...]}``.

    Down-sampled to at most ``max_points`` evenly-spaced points to keep the
    committed JSON small (the curve is smooth; full resolution isn't needed).
    """
    from sklearn.metrics import roc_curve  # type: ignore[import-not-found]

    fpr, tpr, _ = roc_curve(labels, scores)
    if len(fpr) > max_points:
        idx = np.linspace(0, len(fpr) - 1, max_points).round().astype(int)
        fpr, tpr = fpr[idx], tpr[idx]
    return {"fpr": [round(float(x), 5) for x in fpr], "tpr": [round(float(x), 5) for x in tpr]}
