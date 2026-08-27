"""Data models for the Prior Approval Claim Validator."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class ParsedClaim:
    """Structured entities extracted from a technician's claim narrative."""

    vehicle_system: str
    symptom: str
    diagnosis: str
    repair_action: str
    confidence: float

    def __post_init__(self) -> None:
        self.confidence = _clamp(self.confidence)

    # -- serialization --

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ParsedClaim":
        return cls(
            vehicle_system=data["vehicle_system"],
            symptom=data["symptom"],
            diagnosis=data["diagnosis"],
            repair_action=data["repair_action"],
            confidence=data["confidence"],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "ParsedClaim":
        return cls.from_dict(json.loads(json_str))


@dataclass
class PartResult:
    """Validation result for a single requested part."""

    part_name: str
    relevance_score: float
    reason: str
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.relevance_score = _clamp(self.relevance_score)

    # -- serialization --

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PartResult":
        return cls(
            part_name=data["part_name"],
            relevance_score=data["relevance_score"],
            reason=data["reason"],
            evidence_refs=data.get("evidence_refs", []),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "PartResult":
        return cls.from_dict(json.loads(json_str))


@dataclass
class ClaimDecision:
    """Complete validation decision for a warranty claim."""

    claim_id: str
    decision: str  # AUTO_APPROVE | REVIEW | FLAG
    overall_score: float
    part_results: List[PartResult]
    explanation: str
    parsed_claim: ParsedClaim

    def __post_init__(self) -> None:
        self.overall_score = _clamp(self.overall_score)

    # -- serialization --

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "decision": self.decision,
            "overall_score": self.overall_score,
            "part_results": [pr.to_dict() for pr in self.part_results],
            "explanation": self.explanation,
            "parsed_claim": self.parsed_claim.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClaimDecision":
        return cls(
            claim_id=data["claim_id"],
            decision=data["decision"],
            overall_score=data["overall_score"],
            part_results=[PartResult.from_dict(pr) for pr in data["part_results"]],
            explanation=data["explanation"],
            parsed_claim=ParsedClaim.from_dict(data["parsed_claim"]),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "ClaimDecision":
        return cls.from_dict(json.loads(json_str))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, value))
