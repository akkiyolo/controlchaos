"""Sandboxed Safe DSL Interpreter and Backtester for Financial Control Rules.

Allows AI agents (Control Architect) to propose dynamic rules that execute safely
without arbitrary code execution risks.
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional

from app.services.controls.base import DatasetContext, FindingDTO


class SafeDSLEvaluator:
    """Safely evaluates boolean condition expressions over journal entry dicts."""

    ALLOWED_NODES = {
        ast.Expression,
        ast.BoolOp,
        ast.BinOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Attribute,
        ast.And,
        ast.Or,
        ast.Not,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.In,
        ast.NotIn,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.List,
        ast.Tuple,
    }

    @classmethod
    def validate_expression(cls, expr: str) -> None:
        """Parse and ensure expression contains ONLY safe AST nodes."""
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if type(node) not in cls.ALLOWED_NODES:
                raise ValueError(f"Disallowed DSL construct '{type(node).__name__}' in expression: {expr}")

    @classmethod
    def evaluate(cls, expr: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate boolean expression against context namespace."""
        cls.validate_expression(expr)
        tree = ast.parse(expr, mode="eval")

        def _eval(node: ast.AST) -> Any:
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            elif isinstance(node, (ast.List, ast.Tuple)):
                return [_eval(elt) for elt in node.elts]
            elif isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Name):
                if node.id in context:
                    return context[node.id]
                return None
            elif isinstance(node, ast.Attribute):
                val = _eval(node.value)
                return getattr(val, node.attr, None)
            elif isinstance(node, ast.UnaryOp):
                operand = _eval(node.operand)
                if isinstance(node.op, ast.Not):
                    return not operand
                elif isinstance(node.op, ast.USub):
                    return -operand
            elif isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                elif isinstance(node.op, ast.Sub):
                    return left - right
                elif isinstance(node.op, ast.Mult):
                    return left * right
                elif isinstance(node.op, ast.Div):
                    return left / right if right != 0 else 0
            elif isinstance(node, ast.BoolOp):
                if isinstance(node.op, ast.And):
                    return all(_eval(v) for v in node.values)
                elif isinstance(node.op, ast.Or):
                    return any(_eval(v) for v in node.values)
            elif isinstance(node, ast.Compare):
                left = _eval(node.left)
                for op, comp in zip(node.ops, node.comparators):
                    right = _eval(comp)
                    if isinstance(op, ast.Eq) and not (left == right):
                        return False
                    elif isinstance(op, ast.NotEq) and not (left != right):
                        return False
                    elif isinstance(op, ast.Lt) and not (left < right):
                        return False
                    elif isinstance(op, ast.LtE) and not (left <= right):
                        return False
                    elif isinstance(op, ast.Gt) and not (left > right):
                        return False
                    elif isinstance(op, ast.GtE) and not (left >= right):
                        return False
                    elif isinstance(op, ast.In) and left not in right:
                        return False
                    elif isinstance(op, ast.NotIn) and not (left not in right):
                        return False
                    left = right
                return True
            return False

        return bool(_eval(tree))


class DSLRuleRunner:
    """Executes a proposed DSL rule across a dataset and backtests detection effectiveness."""

    @classmethod
    def run_rule(
        cls,
        condition: str,
        severity: str,
        message: str,
        context: DatasetContext,
    ) -> List[FindingDTO]:
        """Apply DSL rule condition to all GL entries in dataset context."""
        SafeDSLEvaluator.validate_expression(condition)
        findings: List[FindingDTO] = []

        for gl in context.gl_entries:
            ctx = {
                "debit": float(getattr(gl, "debit", 0.0) or 0.0),
                "credit": float(getattr(gl, "credit", 0.0) or 0.0),
                "amount": float(getattr(gl, "debit", 0.0) or getattr(gl, "credit", 0.0)),
                "account_code": str(getattr(gl, "account_code", "")),
                "entity_id": str(getattr(gl, "entity_id", "")),
                "currency": str(getattr(gl, "currency", "")),
                "fx_rate": float(getattr(gl, "fx_rate", 1.0)),
                "source_system": str(getattr(gl, "source_system", "")).lower(),
                "created_by": str(getattr(gl, "created_by", "")).lower(),
                "approved_by": str(getattr(gl, "approved_by", "")).lower(),
                "description": str(getattr(gl, "description", "")).lower(),
            }

            try:
                matched = SafeDSLEvaluator.evaluate(condition, ctx)
                if matched:
                    gid = str(getattr(gl, "entry_id", "") or getattr(gl, "id", ""))
                    findings.append(
                        FindingDTO(
                            finding_id=f"FIND-DSL-{gid}",
                            control_id="dsl_custom_rule",
                            severity=severity,
                            description=f"{message} (Matched on entry {gid})",
                            affected_row_refs=[f"gl:{gid}"],
                            amount=float(str(ctx["amount"])),
                            account_code=str(ctx["account_code"]),
                        )
                    )
            except Exception:
                continue

        return findings

    @classmethod
    def backtest_rule(
        cls,
        condition: str,
        severity: str,
        message: str,
        context: DatasetContext,
        target_mutation_row_refs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Backtest proposed DSL rule: compute catches on target mutations and check false-positive impact."""
        findings = cls.run_rule(condition, severity, message, context)
        flagged_refs = set()
        for f in findings:
            flagged_refs.update(f.affected_row_refs)

        target_set = set(target_mutation_row_refs or [])
        true_positives = len(flagged_refs.intersection(target_set)) if target_set else len(flagged_refs)
        false_positives = len(flagged_refs - target_set) if target_set else 0

        return {
            "total_flagged": len(flagged_refs),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "passed_backtest": false_positives <= 2 and true_positives > 0,
        }
