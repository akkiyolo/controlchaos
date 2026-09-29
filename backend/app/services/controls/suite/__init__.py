"""Export all 15 financial controls."""

from typing import Any, List, Type

from app.services.controls.base import BaseControl
from app.services.controls.suite.account_classification import AccountClassificationControl
from app.services.controls.suite.accrual_completeness import AccrualCompletenessControl
from app.services.controls.suite.benford_analysis import BenfordAnalysisControl
from app.services.controls.suite.cutoff_check import CutoffCheckControl
from app.services.controls.suite.duplicate_detection import DuplicateDetectionControl
from app.services.controls.suite.fx_validation import FXValidationControl
from app.services.controls.suite.gl_subledger_recon import GLSubledgerReconControl
from app.services.controls.suite.intercompany_elimination import IntercompanyEliminationControl
from app.services.controls.suite.journal_risk_score import JournalRiskScoreControl
from app.services.controls.suite.segregation_of_duties import SegregationOfDutiesControl
from app.services.controls.suite.statistical_outliers import StatisticalOutliersControl
from app.services.controls.suite.tb_integrity import TrialBalanceIntegrityControl
from app.services.controls.suite.threshold_splitting import ThresholdSplittingControl
from app.services.controls.suite.treasury_controls import TreasuryControls
from app.services.controls.suite.variance_threshold import VarianceThresholdControl

ALL_CONTROLS: List[Type[BaseControl[Any]]] = [
    GLSubledgerReconControl,
    TrialBalanceIntegrityControl,
    DuplicateDetectionControl,
    CutoffCheckControl,
    VarianceThresholdControl,
    AccrualCompletenessControl,
    FXValidationControl,
    ThresholdSplittingControl,
    SegregationOfDutiesControl,
    JournalRiskScoreControl,
    BenfordAnalysisControl,
    IntercompanyEliminationControl,
    AccountClassificationControl,
    TreasuryControls,
    StatisticalOutliersControl,
]

__all__ = [
    "ALL_CONTROLS",
    "GLSubledgerReconControl",
    "TrialBalanceIntegrityControl",
    "DuplicateDetectionControl",
    "CutoffCheckControl",
    "VarianceThresholdControl",
    "AccrualCompletenessControl",
    "FXValidationControl",
    "ThresholdSplittingControl",
    "SegregationOfDutiesControl",
    "JournalRiskScoreControl",
    "BenfordAnalysisControl",
    "IntercompanyEliminationControl",
    "AccountClassificationControl",
    "TreasuryControls",
    "StatisticalOutliersControl",
]
