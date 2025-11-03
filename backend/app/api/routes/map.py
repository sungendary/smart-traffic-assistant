from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...dependencies import get_mongo_db
from ...schemas import MapSuggestionRequest, MapSuggestionResponse
from ...services.map import get_map_suggestions

router = APIRouter()


@router.post("/suggestions", response_model=MapSuggestionResponse)
async def suggest_places(
    payload: MapSuggestionRequest,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> MapSuggestionResponse:
    data = await get_map_suggestions(
        db,
        latitude=payload.latitude,
        longitude=payload.longitude,
        emotion=payload.emotion,
        preferences=payload.preferences,
        location_text=payload.location_text,
        additional_context=payload.additional_context,
    )
    return MapSuggestionResponse(**data)
