"""
schemas.py

Pydantic response models for the Conversation layer (Step 13).

ClarificationRequired is returned when the system needs more information
from the user before it can invoke the underlying coordinator. This keeps
the response format structured and machine-readable — no free-form strings.
"""

from typing import List
from pydantic import BaseModel, Field


class ClarificationRequired(BaseModel):
    """
    Returned when the conversation layer cannot resolve a required input value
    from either the current request or the stored session state.

    The 'missing' list contains the names of the fields that are absent so
    that a client UI can prompt the user for exactly the right information.

    IMPORTANT: This model is produced deterministically — it is NEVER
    produced based on LLM output. The LLM cannot invent missing values.
    """

    success: bool = Field(
        default=False,
        description="Always False for a clarification request.",
    )
    needs_clarification: bool = Field(
        default=True,
        description="Always True, signals the caller that more info is needed.",
    )
    missing: List[str] = Field(
        description="Names of the required fields that could not be resolved.",
    )
    message: str = Field(
        description="Human-readable explanation of what is needed.",
    )
