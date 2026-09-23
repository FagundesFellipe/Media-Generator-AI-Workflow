"""State models and reducers for the content generation LangGraph workflow."""

import operator
from typing import Annotated, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from typing_extensions import TypedDict


def merge_parallel_state_updates(left: dict, right: dict) -> dict:
    """Reducer for state keys written concurrently by the yt/li/x subgraphs in the same superstep."""
    return {**left, **right}


class SourceCodeBlock(BaseModel):
    """A single fenced code block extracted verbatim from the source material."""

    source_block_id: str
    programming_language: str
    original_source_code: str


class ExtractedContentBrief(BaseModel):
    """Structured extraction of the source transcript/markdown produced by `ingest_context`."""

    content_summary: str
    extracted_key_points: list[str]
    source_code_blocks: list[SourceCodeBlock] = []


class GeneratedArtifactState(BaseModel):
    """One platform artifact (e.g. LI post, X thread) and its current review status."""

    artifact_type: str
    generated_content: dict
    rendered_asset_paths: list[str] = []
    human_review_status: Literal["pending", "approved", "rejected"] = "pending"


class ContentReviewDecision(BaseModel):
    """A human's decision on a single artifact at the `review_gate` interrupt."""

    review_outcome: Literal["approved", "rejected", "pending"]
    reviewer_feedback: str | None = None


class ThumbnailFaceInput(BaseModel):
    """User-supplied photo/frame and consent flag for the YouTube thumbnail agent."""

    face_image_path: str
    user_consent_confirmed: bool


class ContentGenerationGraphState(TypedDict):
    """State schema for `generation_graph`; one instance per `thread_id`/run."""

    graph_messages: Annotated[list[AnyMessage], add_messages]
    content_generation_run_id: str
    source_briefing_id: str
    input_source_type: Literal["transcript", "markdown"]
    target_platforms: list[str]
    content_generation_instructions: str
    original_content_text: str
    extracted_content_brief: ExtractedContentBrief
    platforms_requiring_semantic_memory_refresh: Annotated[set[str], operator.or_]
    content_generation_cycle: Literal["fresh", "regen"]
    artifact_regeneration_targets_by_platform: Annotated[
        dict[str, list[str]], merge_parallel_state_updates
    ]
    generated_artifacts_by_id: Annotated[
        dict[str, GeneratedArtifactState], merge_parallel_state_updates
    ]
    human_review_decisions_by_artifact_id: Annotated[
        dict[str, ContentReviewDecision], merge_parallel_state_updates
    ]
    thumbnail_face_input: ThumbnailFaceInput | None
