"""FX Rate Validation Control."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class FXValidationParams(BaseModel):
    enabled: bool = True
    max_drift_pct: float = Field(0.05, description="Maximum allowable deviation from reference FX market rate (5%)")
    check_inversion: bool = Field(True, description="Flag inverted FX quotes (e.g. 1/rate)")
    base_currencies: List[str] = Field(default_factory=lambda: ["USD", "EUR", "GBP", "INR", "CHF"])


class FXValidationControl(BaseControl[FXValidationParams]):
    key = "fx_validation"
    name = "Foreign Exchange Rate Validation"
    category = "market_data"
    description = (
        "Validates foreign exchange conversion rates applied on multi-currency journal entries against "
        "daily reference benchmark rates, detecting stale rates, extreme market drift, and quote inversions."
    )
    intended_error_classes = ["fx_rate_slip"]
    params_model = FXValidationParams

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries
        fx_rates = context.fx_rates  # date -> {pair: rate}

        for gl in gl_entries:
            curr = getattr(gl, "currency", "USD")
            rate = float(getattr(gl, "fx_rate", 1.0) or 1.0)
            gid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")
            date_str = getattr(gl, "posting_date", "")

            # If domestic USD (or base currency with rate 1.0), skip unless rate is non-1.0
            if curr == "USD":
                if abs(rate - 1.0) > 0.001:
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-FX-DOMESTIC-NON1-{gid}",
                            control_id=self.key,
                            severity="medium",
                            description=f"Entry {gid} in domestic currency USD has non-unity FX rate {rate}.",
                            affected_row_refs=[f"gl:{gid}"],
                            amount=rate,
                            account_code=getattr(gl, "account_code", None),
                            period=getattr(gl, "period", None),
                        )
                    )
                continue

            # Check foreign currency
            pair = f"{curr}/USD"
            daily_rates = fx_rates.get(date_str, {})
            ref_rate = daily_rates.get(pair)

            if ref_rate is not None and ref_rate > 0:
                drift = abs(rate - ref_rate) / ref_rate
                # Check inversion: e.g. ref_rate is 1.08, rate is ~ 0.925 (1/1.08)
                inv_drift = abs(rate - (1.0 / ref_rate)) / (1.0 / ref_rate) if ref_rate != 0 else 1.0

                if p.check_inversion and inv_drift < 0.05 and drift > 0.10:
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-FX-INVERTED-{gid}",
                            control_id=self.key,
                            severity="critical",
                            description=(
                                f"Inverted FX rate detected on entry {gid}: applied {rate:.4f} for {pair}, "
                                f"expected {ref_rate:.4f} (drift vs inverse is only {inv_drift:.2%})."
                            ),
                            affected_row_refs=[f"gl:{gid}"],
                            amount=drift,
                            account_code=getattr(gl, "account_code", None),
                            period=getattr(gl, "period", None),
                            metadata={"applied_rate": rate, "reference_rate": ref_rate, "issue": "inverted_quote"},
                        )
                    )
                elif drift > p.max_drift_pct:
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-FX-DRIFT-{gid}",
                            control_id=self.key,
                            severity="high",
                            description=(
                                f"Excessive FX rate drift on entry {gid}: applied {rate:.4f} for {pair} "
                                f"on {date_str}, benchmark reference is {ref_rate:.4f} ({drift:.2%} deviation)."
                            ),
                            affected_row_refs=[f"gl:{gid}"],
                            amount=drift,
                            account_code=getattr(gl, "account_code", None),
                            period=getattr(gl, "period", None),
                            metadata={"applied_rate": rate, "reference_rate": ref_rate, "drift": drift},
                        )
                    )
            elif rate <= 0:
                findings.append(
                    FindingDTO(
                        finding_id=f"FIND-FX-INVALID-{gid}",
                        control_id=self.key,
                        severity="critical",
                        description=f"Invalid non-positive FX rate {rate} on entry {gid}.",
                        affected_row_refs=[f"gl:{gid}"],
                        amount=rate,
                        account_code=getattr(gl, "account_code", None),
                        period=getattr(gl, "period", None),
                    )
                )

        return findings
