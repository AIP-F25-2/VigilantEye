"""Pydantic schemas for LLM output validation."""

from typing import List

from pydantic import BaseModel, Field, field_validator


class SuspicionAnalysis(BaseModel):
    """Schema for LLM threat analysis output."""

    is_suspicious: bool = Field(description="Whether the situation is deemed suspicious")

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for the assessment (0.0-1.0)",
    )

    threat_level: str = Field(
        pattern="^(low|medium|high|critical)$",
        description="Threat level classification",
    )

    reasoning: str = Field(
        min_length=10,
        max_length=2000,
        description="Detailed explanation of the assessment",
    )

    recommended_action: str = Field(
        pattern="^(alert|monitor|escalate|ignore)$",
        description="Recommended action to take",
    )

    key_factors: List[str] = Field(
        min_items=1,
        max_items=10,
        description="Key factors that influenced the decision",
    )

    @field_validator("threat_level")
    @classmethod
    def validate_threat_level(cls, v: str) -> str:
        allowed = ["low", "medium", "high", "critical"]
        if v not in allowed:
            raise ValueError(f"threat_level must be one of {allowed}")
        return v

    @field_validator("recommended_action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = ["alert", "monitor", "escalate", "ignore"]
        if v not in allowed:
            raise ValueError(f"recommended_action must be one of {allowed}")
        return v

