"""Base classes and schemas for financial mutation testing (the 'mutants')."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


@dataclass
class MutationRecordDTO:
    """Ground truth record of an injected accounting mutation."""

    mutation_id: str
    class_name: str
    description: str
    severity: str  # low, medium, high, critical
    stealth: str  # obvious, subtle, adversarial
    magnitude: str  # small, medium, large
    expected_impact_amount: float
    affected_row_refs: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    location_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "class_name": self.class_name,
            "description": self.description,
            "severity": self.severity,
            "stealth": self.stealth,
            "magnitude": self.magnitude,
            "expected_impact_amount": round(self.expected_impact_amount, 2),
            "affected_row_refs": self.affected_row_refs,
            "params": self.params,
            "location_details": self.location_details,
        }


class BaseMutationParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    magnitude: str = Field("medium", pattern="^(small|medium|large)$")
    stealth: str = Field("subtle", pattern="^(obvious|subtle|adversarial)$")
    account_filter: Optional[List[str]] = None
    entity_filter: Optional[List[str]] = None


@dataclass
class MutableDatasetBundle:
    """In-memory bundle of dataset objects ready for copy-on-write mutation."""

    dataset_id: str
    gl_entries: List[Any]
    subledger_entries: List[Any]
    budget_entries: List[Any]
    treasury_positions: List[Any]


class BaseMutator(ABC):
    """Abstract Base Class for all 20 Financial Mutators."""

    key: str
    name: str
    description: str
    default_severity: str = "high"

    @abstractmethod
    def apply(
        self,
        dataset: MutableDatasetBundle,
        rng: random.Random,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[MutationRecordDTO]:
        """Inject mutation into the dataset bundle and return ground truth record."""
        pass
