from fastapi import APIRouter

from ...core.config import settings

router = APIRouter()


@router.get("/maps", summary="프런트에서 사용할 Kakao 지도 키")
async def maps_config() -> dict[str, str]:
    return {"kakaoMapAppKey": settings.kakao_map_app_key}
