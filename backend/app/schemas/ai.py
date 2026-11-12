from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    subject_id: int | None = None
    topic: str = Field(default="", max_length=160)
    save: bool = True  # store this question in "My Doubts"


class SourceOut(BaseModel):
    document_id: int
    title: str
    filename: str
    subject: str
    topic: str
    unit: str
    version: int
    refs: list[int]       # passage numbers ([1], [2]...) that came from this document
    cited: bool           # the answer actually cites one of those passages
    score: float
    snippet: str


class RelevanceOut(BaseModel):
    level: str            # high | medium | low
    score: float          # best cosine similarity between the question and a retrieved passage


class AskResponse(BaseModel):
    mode: str
    answerable: bool
    answer: str
    explanation: str
    key_points: list[str]
    sources: list[SourceOut]
    relevance: RelevanceOut | None
    doubt_id: int | None
    saved: bool
