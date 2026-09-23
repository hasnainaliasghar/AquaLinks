"""Deterministic risk scoring.

The function :func:`score_risk` returns a :class:`RiskScore` from a set
of computed indices and optional field evidence. The score is a pure
function of its inputs — no LLM, no randomness — so it can be tested
and audited. The narrative reasoning produced by ``services.reasoning``
is separate; it never overrides the numeric score returned here.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from app.models.evidence import FieldEvidence, Odor, WaterColor
from app.models.risk_assessment import RiskLevel, Urgency
from app.models.spectral_index import IndexName
from app.services.indices import IndexAggregate

# Weights for each contributing factor. The base-score weights sum to 1.0
# before evidence adjustments are applied; evidence_bonus is added on top
# and the final value is clamped to [0, 1].
WEIGHTS: dict[str, float] = {
    "ndci": 0.40,
    "ndti": 0.25,
    "ndvi_shore": 0.10,
    "mndwi_floor": 0.10,
    "ndwi_floor": 0.15,
}

# How much each evidence flag contributes to the bonus.
EVIDENCE_WEIGHTS: dict[str, float] = {
    "algae_present": 0.20,
    "dead_fish_count_per_unit": 0.05,  # per fish, capped
    "complaints_per_unit": 0.04,  # per complaint, capped
    "rainfall_mm_per_10mm": 0.03,  # per 10 mm rainfall, capped
    "suspicious_color": 0.10,
    "suspicious_odor": 0.10,
}

EVIDENCE_CAPS: dict[str, float] = {
    "dead_fish_count_per_unit": 0.20,
    "complaints_per_unit": 0.12,
    "rainfall_mm_per_10mm": 0.10,
}


_SUSPICIOUS_COLORS = {
    WaterColor.GREEN,
    WaterColor.BROWN,
    WaterColor.YELLOW,
    WaterColor.BLACK,
    WaterColor.RED,
}
_SUSPICIOUS_ODORS = {Odor.FISHY, Odor.ROTTEN, Odor.CHEMICAL, Odor.SEWAGE, Odor.MUSTY}


@dataclass(slots=True, frozen=True)
class RiskScore:
    """Output of the deterministic risk model."""

    score: float
    level: RiskLevel
    urgency: Urgency
    contributors: dict[str, float] = field(default_factory=dict)


def _normalize(value: float, low: float, high: float) -> float:
    """Linearly scale ``value`` from ``[low, high]`` to ``[0, 1]``."""
    if high == low:
        return 0.0
    scaled = (value - low) / (high - low)
    return max(0.0, min(1.0, scaled))


def _index_lookup(indices: Iterable[IndexAggregate]) -> dict[IndexName, float]:
    return {idx.name: idx.value for idx in indices}


def _evidence_bonus(evidence: Iterable[FieldEvidence]) -> tuple[float, dict[str, float]]:
    """Aggregate evidence into a bonus in ``[0, 1]`` and per-driver breakdown."""

    items = list(evidence)
    if not items:
        return 0.0, {}

    # Use the latest evidence (most recent first) — the pipeline orders by
    # ``created_at desc`` before passing in.
    latest = items[0]

    contributors: dict[str, float] = {}

    if latest.algae_present:
        contributors["algae_present"] = EVIDENCE_WEIGHTS["algae_present"]

    if latest.water_color in _SUSPICIOUS_COLORS:
        contributors["suspicious_color"] = EVIDENCE_WEIGHTS["suspicious_color"]

    if latest.odor in _SUSPICIOUS_ODORS:
        contributors["suspicious_odor"] = EVIDENCE_WEIGHTS["suspicious_odor"]

    if latest.dead_fish_count > 0:
        contributors["dead_fish"] = min(
            EVIDENCE_WEIGHTS["dead_fish_count_per_unit"] * latest.dead_fish_count,
            EVIDENCE_CAPS["dead_fish_count_per_unit"],
        )

    if latest.complaints_count > 0:
        contributors["complaints"] = min(
            EVIDENCE_WEIGHTS["complaints_per_unit"] * latest.complaints_count,
            EVIDENCE_CAPS["complaints_per_unit"],
        )

    if latest.rainfall_mm > 0:
        contributors["recent_rainfall"] = min(
            EVIDENCE_WEIGHTS["rainfall_mm_per_10mm"] * (latest.rainfall_mm / 10.0),
            EVIDENCE_CAPS["rainfall_mm_per_10mm"],
        )

    bonus = min(sum(contributors.values()), 0.5)
    return bonus, contributors


def _bucket_level(score: float) -> RiskLevel:
    if score < 0.33:
        return RiskLevel.LOW
    if score < 0.66:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def _bucket_urgency(level: RiskLevel, evidence: Iterable[FieldEvidence]) -> Urgency:
    items = list(evidence)
    latest = items[0] if items else None

    has_severe_field = bool(
        latest
        and (latest.dead_fish_count >= 5 or latest.complaints_count >= 3 or latest.algae_present)
    )

    if level is RiskLevel.HIGH and has_severe_field:
        return Urgency.IMMEDIATE
    if level is RiskLevel.HIGH:
        return Urgency.ELEVATED
    if level is RiskLevel.MEDIUM and has_severe_field:
        return Urgency.ELEVATED
    if level is RiskLevel.MEDIUM:
        return Urgency.ROUTINE
    if has_severe_field:
        return Urgency.ELEVATED
    return Urgency.ROUTINE


def score_risk(
    indices: Iterable[IndexAggregate],
    evidence: Iterable[FieldEvidence] = (),
) -> RiskScore:
    """Compute the deterministic risk score.

    ``indices`` is iterable so the caller can pass either a list of
    ``SpectralIndex`` rows or freshly computed :class:`IndexAggregate`
    objects (both expose ``name`` and ``value``).
    """

    values = _index_lookup(indices)

    contributors: dict[str, float] = {}

    # NDCI: chlorophyll signal → bloom risk.
    ndci_norm = _normalize(values.get(IndexName.NDCI, 0.0), -0.1, 0.5)
    contributors["ndci"] = WEIGHTS["ndci"] * ndci_norm

    # NDTI: turbidity.
    ndti_norm = _normalize(values.get(IndexName.NDTI, 0.0), -0.2, 0.6)
    contributors["ndti"] = WEIGHTS["ndti"] * ndti_norm

    # NDVI over the water mask is a stress proxy — high NDVI inside water
    # often indicates floating biomass or shoreline encroachment.
    ndvi_norm = _normalize(values.get(IndexName.NDVI, 0.0), 0.0, 0.6)
    contributors["ndvi_shore"] = WEIGHTS["ndvi_shore"] * ndvi_norm

    # MNDWI floor: if MNDWI is low the water signal is weak, which makes the
    # other indices less reliable. Add a small "uncertainty" penalty.
    mndwi = values.get(IndexName.MNDWI, 0.0)
    mndwi_pen = 1.0 - _normalize(mndwi, 0.0, 0.5)
    contributors["mndwi_floor"] = WEIGHTS["mndwi_floor"] * mndwi_pen

    # NDWI floor: same idea — low NDWI = unreliable water signal.
    ndwi = values.get(IndexName.NDWI, 0.0)
    ndwi_pen = 1.0 - _normalize(ndwi, 0.0, 0.5)
    contributors["ndwi_floor"] = WEIGHTS["ndwi_floor"] * ndwi_pen

    base_score = sum(contributors.values())

    bonus, evidence_contrib = _evidence_bonus(evidence)
    contributors.update({f"evidence.{k}": v for k, v in evidence_contrib.items()})

    final = max(0.0, min(1.0, base_score + bonus))
    level = _bucket_level(final)
    urgency = _bucket_urgency(level, evidence)

    contributors["__base"] = base_score
    contributors["__evidence_bonus"] = bonus

    return RiskScore(score=final, level=level, urgency=urgency, contributors=contributors)
