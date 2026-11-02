from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: Optional[str] = Field(default=None, max_length=100000)
    provider: Optional[str] = None
    regenerate: bool = False


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class ClassifyIn(TextIn):
    labels: list[str] = Field(min_length=2, max_length=20)


class SummarizeIn(TextIn):
    method: Literal["extractive", "abstractive"] = "extractive"
    sentences: int = Field(default=3, ge=1, le=10)


class KeywordsIn(TextIn):
    top_k: int = Field(default=10, ge=1, le=50)


class DemoIn(BaseModel):
    mode: Literal["bow", "tfidf", "ngrams", "cosine"]
    texts: list[str] = Field(min_length=1, max_length=20)
    n: int = Field(default=2, ge=1, le=3)


class ChartSpec(BaseModel):
    type: Literal["bar", "line", "histogram", "scatter", "pie", "box", "heatmap"]
    x: Optional[str] = None
    y: Optional[str] = None
    agg: str = "sum"
    bins: int = Field(default=10, ge=2, le=100)


class GroupByIn(BaseModel):
    by: str
    column: str
    agg: str = "mean"


class CleanIn(BaseModel):
    ops: list[dict] = Field(max_length=30)
    apply: bool = False


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class TrainIn(BaseModel):
    hidden: int = 32
    lr: float = 0.01
    batch: int = 32
    epochs: int = 20
