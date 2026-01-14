from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.chat_schema import ChatRequest, ChatResponse
from app.services.vector_service import semantic_search
from app.services.job_service import get_jobs
from app.services.llm_service import generate_answer, stream_answer
from app.prompt_engine.prompt_builder import build_prompt

router = APIRouter()


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Chat with AI (non-streaming)
    Returns complete response at once
    """
    user_message = request.message

    # Step 1: Vector search
    job_ids = semantic_search(user_message)

    # Step 2: Get job data
    job_context = get_jobs(job_ids)

    # Step 3: Build prompt
    prompt = build_prompt(user_message, job_context)

    # Step 4: Call LLM
    answer = generate_answer(prompt)

    return ChatResponse(answer=answer)

@router.post("/stream")
def chat_stream(request: ChatRequest):
    """
    Chat with streaming response (typing effect)
    Returns text chunks as they are generated
    """
    user_message = request.message

    # Step 1: Vector search
    job_ids = semantic_search(user_message)

    # Step 2: Get job data
    job_context = get_jobs(job_ids)

    # Step 3: Build prompt
    prompt = build_prompt(user_message, job_context)

    # Step 4: Stream LLM response
    return StreamingResponse(
        stream_answer(prompt),
        media_type="text/plain; charset=utf-8"
    )