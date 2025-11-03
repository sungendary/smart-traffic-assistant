from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="애플리케이션 헬스체크")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
