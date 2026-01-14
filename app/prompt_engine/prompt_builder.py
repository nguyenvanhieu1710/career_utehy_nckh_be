from app.prompt_engine.system_prompt import SYSTEM_PROMPT


def build_prompt(user_message: str, job_context: str) -> str:
    return f"""
[SYSTEM PROMPT]
{SYSTEM_PROMPT}

[JOB DATA]
{job_context}

[USER QUESTION]
{user_message}

Hãy trả lời dựa trên dữ liệu trên.
"""
