"""Benford's Law First-Digit Conformity Control."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.controls.base import BaseControl, DatasetContext, FindingDTO


class BenfordAnalysisParams(BaseModel):
    enabled: bool = True
    min_sample_size: int = Field(50, description="Minimum transaction sample size required to perform Chi-square test")
    critical_chi2: float = Field(15.51, description="Chi-square critical value at alpha=0.05 with 8 degrees of freedom")
    mad_threshold: float = Field(0.018, description="Mean Absolute Deviation (MAD) non-conformity threshold")


class BenfordAnalysisControl(BaseControl[BenfordAnalysisParams]):
    key = "benford_analysis"
    name = "Benford's Law Conformity Analysis"
    category = "forensic"
    description = (
        "Applies forensic digit analysis evaluating leading digit distribution conformity against Benford's Law "
        "(P(d) = log10(1 + 1/d)) using Chi-square goodness-of-fit and Mean Absolute Deviation (MAD) to uncover fabricated figures."
    )
    intended_error_classes = ["benford_manipulation"]
    params_model = BenfordAnalysisParams

    @staticmethod
    def get_first_digit(val: float) -> Optional[int]:
        s = f"{abs(val):.4f}".lstrip("0").replace(".", "")
        if s and s[0].isdigit() and s[0] != "0":
            return int(s[0])
        return None

    def run(self, context: DatasetContext, params: Optional[Dict[str, Any]] = None) -> List[FindingDTO]:
        p = self.validate_params(params or {})
        if not p.enabled:
            return []

        findings: List[FindingDTO] = []
        gl_entries = context.gl_entries

        # Group entries by account family (first digit of account code, e.g. 1xxx, 2xxx, 4xxx, 5xxx)
        family_digits: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        family_rows: Dict[str, List[str]] = defaultdict(list)
        family_totals: Dict[str, int] = defaultdict(int)

        for gl in gl_entries:
            amt = float(getattr(gl, "debit", 0.0) or getattr(gl, "credit", 0.0))
            if amt <= 10.0:
                continue
            fd = self.get_first_digit(amt)
            if fd is None:
                continue

            acc = getattr(gl, "account_code", "")
            fam = acc[0] if acc else "0"
            gid = getattr(gl, "entry_id", "") or getattr(gl, "id", "")

            family_digits[fam][fd] += 1
            family_totals[fam] += 1
            family_rows[fam].append(f"gl:{gid}")

        # Theoretical Benford distribution
        expected_p = {d: math.log10(1.0 + 1.0 / d) for d in range(1, 10)}

        for fam, total in family_totals.items():
            if total < p.min_sample_size:
                continue

            chi2 = 0.0
            mad = 0.0
            obs_dist = {}

            for d in range(1, 10):
                obs = family_digits[fam].get(d, 0)
                exp = total * expected_p[d]
                chi2 += ((obs - exp) ** 2) / exp
                obs_prop = obs / total
                mad += abs(obs_prop - expected_p[d])
                obs_dist[d] = round(obs_prop, 4)

            mad /= 9.0

            if chi2 > p.critical_chi2 or mad > p.mad_threshold:
                fam_names = {
                    "1": "Assets",
                    "2": "Liabilities",
                    "3": "Equity",
                    "4": "Revenue",
                    "5": "Operating Expenses",
                }
                fam_label = fam_names.get(fam, f"Account Family {fam}")

                findings.append(
                    FindingDTO(
                        finding_id=f"FIND-BENFORD-FAM-{fam}",
                        control_id=self.key,
                        severity="high",
                        description=(
                            f"Benford's Law anomaly detected in {fam_label} ({fam}xxx): "
                            f"Sample N={total}, Chi-square={chi2:.2f} (critical {p.critical_chi2:.2f}), "
                            f"MAD={mad:.4f} (threshold {p.mad_threshold:.4f}). Potential fabricated or biased amounts."
                        ),
                        affected_row_refs=family_rows[fam][:15],
                        amount=float(chi2),
                        account_code=f"{fam}000",
                        period=None,
                        metadata={
                            "family": fam,
                            "n": total,
                            "chi2": round(chi2, 2),
                            "mad": round(mad, 4),
                            "observed_dist": obs_dist,
                        },
                    )
                )

        return findings
