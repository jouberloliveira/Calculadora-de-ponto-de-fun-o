"""IFPUG Function Point computation.

Weight tables follow IFPUG CPM 4.3.1:

| Type | low | medium | high |
|------|-----|--------|------|
| EI   | 3   | 4      | 6    |
| EO   | 4   | 5      | 7    |
| EQ   | 3   | 4      | 6    |
| ILF  | 7   | 10     | 15   |
| EIF  | 5   | 7      | 10   |

UFP   = sum of weighted functions.
VAF   = 0.65 + (sum(GSC) / 100), where each GSC is 0..5.
AFP   = UFP * VAF.
"""

from __future__ import annotations

from .models import (
    AnalysisResult,
    FPAFunction,
    FPASummary,
    FunctionType,
    LLMAnalysis,
    VAFFactor,
)

FP_WEIGHTS: dict[FunctionType, dict[str, int]] = {
    FunctionType.EI:  {"low": 3, "medium": 4, "high": 6},
    FunctionType.EO:  {"low": 4, "medium": 5, "high": 7},
    FunctionType.EQ:  {"low": 3, "medium": 4, "high": 6},
    FunctionType.ILF: {"low": 7, "medium": 10, "high": 15},
    FunctionType.EIF: {"low": 5, "medium": 7, "high": 10},
}


def weight_for(fn: FPAFunction) -> int:
    return FP_WEIGHTS[fn.type][fn.complexity]


def compute_ufp(functions: list[FPAFunction]) -> tuple[int, list[FPAFunction]]:
    """Return (UFP, functions with fp filled in)."""
    total = 0
    enriched: list[FPAFunction] = []
    for fn in functions:
        fp = weight_for(fn)
        total += fp
        enriched.append(fn.model_copy(update={"fp": fp}))
    return total, enriched


def compute_vaf(factors: list[VAFFactor]) -> float:
    """VAF = 0.65 + (sum(values) / 100). Bounded to [0.65, 1.35]."""
    total = sum(f.value for f in factors)
    vaf = 0.65 + (total / 100.0)
    # 14 GSCs * max 5 = 70 -> 1.35 ceiling. Clamp defensively.
    return max(0.65, min(1.35, round(vaf, 2)))


def compute_afp(ufp: int, vaf: float) -> float:
    return round(ufp * vaf, 2)


def compute_analysis(job_id: str, analysis: LLMAnalysis) -> AnalysisResult:
    ufp, fns = compute_ufp(analysis.functions)
    vaf = compute_vaf(analysis.vafFactors)
    afp = compute_afp(ufp, vaf)
    return AnalysisResult(
        jobId=job_id,
        status="done",
        summary=FPASummary(ufp=ufp, vaf=vaf, afp=afp),
        functions=fns,
        vafFactors=analysis.vafFactors,
    )
