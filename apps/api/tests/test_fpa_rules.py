"""Tests for IFPUG calculation rules."""

from __future__ import annotations

from app.fpa.models import FPAFunction, FunctionType, LLMAnalysis, VAFFactor
from app.fpa.rules import compute_afp, compute_analysis, compute_ufp, compute_vaf


def test_compute_ufp_weights_each_function_type() -> None:
    fns = [
        FPAFunction(type=FunctionType.EI, name="Create User", complexity="low"),
        FPAFunction(type=FunctionType.EO, name="Generate Report", complexity="medium"),
        FPAFunction(type=FunctionType.EQ, name="Search", complexity="high"),
        FPAFunction(type=FunctionType.ILF, name="User Store", complexity="low"),
        FPAFunction(type=FunctionType.EIF, name="External Catalog", complexity="medium"),
    ]
    # 3 (EI low) + 5 (EO med) + 6 (EQ high) + 7 (ILF low) + 7 (EIF med) = 28
    ufp, enriched = compute_ufp(fns)
    assert ufp == 28
    assert [f.fp for f in enriched] == [3, 5, 6, 7, 7]


def test_compute_vaf_uses_ifpug_formula() -> None:
    # 14 GSCs all at value 3 -> sum 42 -> 0.65 + 0.42 = 1.07
    factors = [VAFFactor(name=f"GSC{i}", value=3) for i in range(14)]
    assert compute_vaf(factors) == 1.07


def test_compute_vaf_clamps_to_bounds() -> None:
    # No factors -> sum 0 -> 0.65 floor.
    assert compute_vaf([]) == 0.65
    # All maxed -> 14*5=70 -> 1.35 ceiling.
    factors = [VAFFactor(name=f"GSC{i}", value=5) for i in range(14)]
    assert compute_vaf(factors) == 1.35


def test_compute_afp_known_fixture() -> None:
    # Fixed example from issue:
    # UFP 158, VAF 1.05 -> AFP 165.9
    assert compute_afp(158, 1.05) == 165.9


def test_compute_analysis_end_to_end_fixture() -> None:
    """Known fixture: 1 EI low + 1 ILF medium + GSCs sum=40."""
    analysis = LLMAnalysis(
        functions=[
            FPAFunction(type=FunctionType.EI, name="Login", complexity="low"),
            FPAFunction(type=FunctionType.ILF, name="Users table", complexity="medium"),
        ],
        vafFactors=[VAFFactor(name=f"GSC{i}", value=v) for i, v in enumerate(
            [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2]  # sum = 40
        )],
    )
    result = compute_analysis("test-job", analysis)
    assert result.status == "done"
    assert result.summary is not None
    # UFP: EI low (3) + ILF medium (10) = 13
    assert result.summary.ufp == 13
    # VAF: 0.65 + 0.40 = 1.05
    assert result.summary.vaf == 1.05
    # AFP: 13 * 1.05 = 13.65
    assert result.summary.afp == 13.65
    # Functions enriched with fp.
    assert [f.fp for f in result.functions] == [3, 10]
