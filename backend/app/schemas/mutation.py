"""Schemas for Mutation Catalog and Campaigns."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class MutatorInfoDTO(BaseModel):
    key: str
    name: str
    description: str
    default_severity: str


class MutatorCatalogResponse(BaseModel):
    total: int
    mutators: List[MutatorInfoDTO]


class MutationItemConfig(BaseModel):
    class_name: str
    count: int = Field(default=1, ge=1, le=50)
    magnitude: str = Field(default="medium", pattern="^(small|medium|large)$")
    stealth: str = Field(default="subtle", pattern="^(obvious|subtle|adversarial)$")


class CreateCampaignRequest(BaseModel):
    parent_dataset_id: str
    campaign_name: str = Field(..., min_length=3, max_length=255)
    seed: int = Field(default=42)
    mutations: List[MutationItemConfig] = Field(..., min_length=1)


class MutationLedgerItemDTO(BaseModel):
    id: str
    dataset_id: str
    mutation_id: str
    class_name: str
    params: Dict[str, Any]
    affected_row_refs: List[str]
    expected_impact_amount: float
    injected_at: datetime


class MutationLedgerResponse(BaseModel):
    total: int
    mutations: List[MutationLedgerItemDTO]
