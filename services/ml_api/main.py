"""
FastAPI sentiment microservice for market news.

Phase 1 goals:
- Receive a batch of headlines.
- Score each headline using a lightweight Hugging Face sentiment model.
- Return normalized sentiment scores for downstream storage/analytics.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import pipeline


# Environment-driven model selection for easy A/B experiments.
MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "distilbert-base-uncased-finetuned-sst-2-english",
)


class SentimentRequest(BaseModel):
    """Batch request payload."""

    headlines: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="News headlines to score.",
    )


class HeadlineSentiment(BaseModel):
    """Single headline sentiment result."""

    headline: str
    label: Literal["POSITIVE", "NEGATIVE"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    # Normalized score in [-1, 1] to simplify downstream SQL analytics.
    normalized_score: float = Field(..., ge=-1.0, le=1.0)


class SentimentResponse(BaseModel):
    model: str
    results: list[HeadlineSentiment]


@lru_cache(maxsize=1)
def get_classifier():
    """
    Lazily initialize the classifier once per process.

    Keeping initialization lazy speeds up cold start handling and keeps startup
    failure easier to diagnose for local development.
    """
    return pipeline("sentiment-analysis", model=MODEL_NAME)


app = FastAPI(
    title="Market Sentiment ML API",
    version="0.1.0",
    description="Scores market/news headlines for sentiment.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple readiness probe used by orchestrators and local checks."""
    return {"status": "ok"}


@app.post("/v1/sentiment/headlines", response_model=SentimentResponse)
def score_headlines(payload: SentimentRequest) -> SentimentResponse:
    """
    Score a list of headlines and return a normalized sentiment output.

    Output mapping:
    - POSITIVE -> +confidence
    - NEGATIVE -> -confidence
    """
    try:
        classifier = get_classifier()
        raw_results = classifier(payload.headlines, truncation=True)
    except Exception as exc:
        # Surface a clear API failure to n8n callers.
        raise HTTPException(status_code=500, detail=f"Sentiment pipeline error: {exc}") from exc

    results: list[HeadlineSentiment] = []
    for headline, row in zip(payload.headlines, raw_results):
        label = str(row.get("label", "NEGATIVE")).upper()
        confidence = float(row.get("score", 0.0))
        normalized = confidence if label == "POSITIVE" else -confidence
        results.append(
            HeadlineSentiment(
                headline=headline,
                label="POSITIVE" if label == "POSITIVE" else "NEGATIVE",
                confidence=confidence,
                normalized_score=normalized,
            )
        )

    return SentimentResponse(model=MODEL_NAME, results=results)
