"""Treasury Liquidity and Cash Reconciliation Controls."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class TreasuryControlsParams(BaseModel):
    enabled: bool = True
    lcr_floor_pct: float = Field(100.0, description="Minimum regulatory Liquidity Coverage Ratio (LCR) percentage")
    staleness_max_days: int = Field(5, description="Maximum days cash balance may remain completely static")


class TreasuryControls(BaseControl[TreasuryControlsParams]):
    key = "treasury_controls"
    name = "Treasury Liquidity & Cash Controls"
    category = "treasury"
    description = (
        "Monitors institutional treasury metrics: enforces Basel III Liquidity Coverage Ratio (LCR >= 100%), "
        "detects frozen/stale cash balances across operating accounts, and identifies cash reconciliation anomalies."
    )
    intended_error_classes = ["treasury_buffer_error", "stale_balance"]
    params_model = TreasuryControlsParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        treasury_pos = context.treasury_positions

        # Group treasury positions by entity
        by_entity: Dict[str, List[Any]] = defaultdict(list)
        for pos in treasury_pos:
            ent = getattr(pos, "entity_id", "")
            by_entity[ent].append(pos)

        for ent, positions in by_entity.items():
            # Sort chronologically
            positions.sort(key=lambda x: getattr(x, "as_of_date", ""))

            consecutive_identical_days = 0
            last_cash = None

            for pos in positions:
                date_str = getattr(pos, "as_of_date", "")
                pid = getattr(pos, "id", "")
                cash = float(getattr(pos, "cash_balance", 0.0))
                hqla = float(getattr(pos, "hqla", 0.0))
                net_outflow = float(getattr(pos, "net_outflow_30d", 0.0))
                lcr = float(getattr(pos, "lcr_ratio", 0.0))

                # Check 1: LCR Floor Breach
                if lcr < p.lcr_floor_pct:
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-LCR-BREACH-{ent}-{date_str}",
                            control_id=self.key,
                            severity="critical",
                            description=(
                                f"Liquidity Coverage Ratio breach for entity {ent} on {date_str}: "
                                f"LCR is {lcr:.1f}% (Regulatory floor is {p.lcr_floor_pct:.1f}%). "
                                f"HQLA: {hqla:,.2f}, 30-Day Net Outflows: {net_outflow:,.2f}."
                            ),
                            affected_row_refs=[f"treasury:{pid}"],
                            amount=net_outflow - hqla if net_outflow > hqla else 0.0,
                            account_code="TREASURY-LCR",
                            period=None,
                            metadata={"as_of_date": date_str, "lcr": lcr, "hqla": hqla, "net_outflow": net_outflow},
                        )
                    )

                # Check 2: Negative Cash or HQLA
                if cash < 0 or hqla < 0:
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-CASH-DEFICIT-{ent}-{date_str}",
                            control_id=self.key,
                            severity="critical",
                            description=(
                                f"Negative liquidity buffer on entity {ent} ({date_str}): "
                                f"Cash: {cash:,.2f}, HQLA: {hqla:,.2f}."
                            ),
                            affected_row_refs=[f"treasury:{pid}"],
                            amount=abs(min(cash, hqla)),
                            account_code="TREASURY-CASH",
                            period=None,
                        )
                    )

                # Check 3: Stale Cash Balance
                if last_cash is not None and abs(cash - last_cash) < 0.01:
                    consecutive_identical_days += 1
                else:
                    consecutive_identical_days = 1
                    last_cash = cash

                if consecutive_identical_days >= p.staleness_max_days:
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-CASH-STALE-{ent}-{date_str}",
                            control_id=self.key,
                            severity="high",
                            description=(
                                f"Stale treasury cash balance detected on entity {ent}: "
                                f"Balance of {cash:,.2f} has remained completely unchanged for {consecutive_identical_days} consecutive days (ending {date_str})."
                            ),
                            affected_row_refs=[f"treasury:{pid}"],
                            amount=cash,
                            account_code="TREASURY-CASH",
                            period=None,
                            metadata={"consecutive_days": consecutive_identical_days, "as_of_date": date_str},
                        )
                    )
                    consecutive_identical_days = 0  # reset after reporting

        return findings
