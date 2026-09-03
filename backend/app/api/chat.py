from fastapi import APIRouter, HTTPException, Depends
from typing import Union, Optional
from .schemas import ChatRequest
from ..conversation.conversation_coordinator import ConversationCoordinator
from ..conversation.schemas import ClarificationRequired
from ..coordinator.schemas import CoordinatorResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

# Lazy singleton — created on first request, not at import time.
# This avoids GROQ_API_KEY being checked before tests can set up the env.
_coordinator_instance: Optional[ConversationCoordinator] = None


def get_coordinator() -> ConversationCoordinator:
    global _coordinator_instance
    if _coordinator_instance is None:
        try:
            _coordinator_instance = ConversationCoordinator()
        except (OSError, EnvironmentError) as e:
            raise HTTPException(
                status_code=503,
                detail=f"Service configuration error: {e}",
            )
    return _coordinator_instance


@router.post("/chat", response_model=Union[CoordinatorResponse, ClarificationRequired])
def process_chat_message(
    request: ChatRequest,
    coordinator: ConversationCoordinator = Depends(get_coordinator)
):
    try:
        response = coordinator.process_turn(
            session_id=request.session_id,
            query_text=request.message,
            latitude=request.latitude,
            longitude=request.longitude,
            date_str=request.date_str,
            location_context=request.location_context,
        )
        return response
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail="Internal processing failure")

