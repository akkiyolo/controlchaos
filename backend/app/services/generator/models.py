"""Generator schemas, profiles, and parameter configurations."""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class IndustryProfile(str, Enum):
    BANK = "bank"
    ASSET_MANAGER = "asset_manager"
    WEALTH_MANAGER = "wealth_manager"


class TransactionVolume(str, Enum):
    LOW = "low"        # ~1,000 GL entries/month
    MEDIUM = "medium"  # ~5,000 GL entries/month
    HIGH = "high"      # ~15,000 GL entries/month


class GeneratorParams(BaseModel):
    name: str = Field(default="Baseline Synthetic Ledger", min_length=3, max_length=100)
    seed: int = Field(default=42, ge=0, le=2147483647)
    entities_count: int = Field(default=3, ge=1, le=10)
    months: int = Field(default=12, ge=3, le=36)
    volume: TransactionVolume = Field(default=TransactionVolume.LOW)
    industry_profile: IndustryProfile = Field(default=IndustryProfile.BANK)
    currencies: List[str] = Field(default=["USD", "EUR", "GBP", "INR", "CHF"])
    include_decoys: bool = Field(default=True)
    start_date: str = Field(default="2025-01", pattern=r"^\d{4}-\d{2}$")


class DecoyAnomaly(BaseModel):
    decoy_id: str
    period: str
    entity_code: str
    account_code: str
    amount: float
    description: str
    reason_valid: str
