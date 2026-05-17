from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FunctionType(str, Enum):
    EI = "EI"
    EO = "EO"
    EQ = "EQ"
    ILF = "ILF"
    EIF = "EIF"


Complexity = Literal["low", "medium", "high"]


class FPAFunction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: FunctionType
    name: str = Field(min_length=1, max_length=200)
    complexity: Complexity
    fp: int | None = Field(default=None, ge=0, le=15)
    justification: str = Field(default="", max_length=2000)


class VAFFactor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=120)
    value: int = Field(ge=0, le=5)
    rationale: str = Field(default="", max_length=2000)


class LLMAnalysis(BaseModel):
    """Shape Ollama is expected to return."""
    model_config = ConfigDict(extra="ignore")

    functions: list[FPAFunction] = Field(default_factory=list)
    vafFactors: list[VAFFactor] = Field(default_factory=list)

    @field_validator("functions")
    @classmethod
    def _at_least_one_function(cls, v: list[FPAFunction]) -> list[FPAFunction]:
        if not v:
            raise ValueError("functions must contain at least one entry")
        return v


class FPASummary(BaseModel):
    ufp: int = Field(ge=0)
    vaf: float = Field(ge=0.65, le=1.35)
    afp: float = Field(ge=0)


class AnalysisResult(BaseModel):
    jobId: str
    status: Literal["pending", "running", "done", "error"]
    summary: FPASummary | None = None
    functions: list[FPAFunction] = Field(default_factory=list)
    vafFactors: list[VAFFactor] = Field(default_factory=list)
    error: str | None = None
