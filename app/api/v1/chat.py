from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import logging

from app.models.chat import ChatRequest, ChatResponse
from app.services.vector_service import semantic_search, build_faiss_index, get_faiss_stats
from app.services.job_service import get_jobs
from app.services.llm_service import generate_answer, stream_answer
from app.prompt_engine.prompt_builder import build_prompt
from app.services.question_validator import is_question_in_scope, get_rejection_message

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with AI (non-streaming)
    Returns complete response at once
    """
    user_message = request.message
    
    # Step 0: Validate question scope
    is_valid, reason = is_question_in_scope(user_message)
    if not is_valid:
        return ChatResponse(answer=get_rejection_message(reason))
    
    # Step 1: Vector search
    job_ids = semantic_search(user_message)

    # Step 2: Get job data
    job_context = await get_jobs(job_ids)

    # Step 3: Build prompt
    prompt = build_prompt(user_message, job_context)

    # Step 4: Call LLM
    answer = generate_answer(prompt)

    return ChatResponse(answer=answer)

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat with streaming response (typing effect)
    Returns text chunks as they are generated
    """
    user_message = request.message
    
    # Step 0: Validate question scope
    is_valid, reason = is_question_in_scope(user_message)
    if not is_valid:
        # Return rejection as plain text for streaming
        async def rejection_stream():
            yield get_rejection_message(reason)
        
        return StreamingResponse(
            rejection_stream(),
            media_type="text/plain; charset=utf-8"
        )
    
    # Step 1: Vector search
    job_ids = semantic_search(user_message)

    # Step 2: Get job data
    job_context = await get_jobs(job_ids)

    # Step 3: Build prompt
    prompt = build_prompt(user_message, job_context)

    # Step 4: Stream LLM response
    return StreamingResponse(
        stream_answer(prompt),
        media_type="text/plain; charset=utf-8"
    )

@router.get("/faiss-stats")
def get_vector_stats():
    """
    Get FAISS index statistics
    Shows: total vectors, memory usage, disk usage, job IDs
    """
    stats = get_faiss_stats()
    return stats

@router.post("/rebuild-index")
async def rebuild_index():
    """
    Manually rebuild FAISS index from database
    Use this after adding/updating many jobs
    """
    await build_faiss_index()
    stats = get_faiss_stats()
    return {
        "message": "FAISS index rebuilt successfully",
        "stats": stats
    }