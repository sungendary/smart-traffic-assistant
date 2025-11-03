from fastapi import APIRouter

from ...schemas import LLMTaskStatusResponse
from ...services.llm_tasks import get_task_status

router = APIRouter()


@router.get("/tasks/{task_id}", response_model=LLMTaskStatusResponse)
async def fetch_task_status(task_id: str) -> LLMTaskStatusResponse:
    data = await get_task_status(task_id)
    return LLMTaskStatusResponse(**data)
