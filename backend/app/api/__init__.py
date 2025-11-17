from fastapi import APIRouter

from .routes import (
    auth,
    bookmarks,
    challenges,
    config,
    couples,
    health,
    map as map_routes,
    planner,
    recommendations,
    reports,
    visits,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(map_routes.router, prefix="/map", tags=["map"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(planner.router, prefix="/planner", tags=["planner"])
api_router.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"])
api_router.include_router(visits.router, prefix="/visits", tags=["visits"])
api_router.include_router(challenges.router, prefix="/challenges", tags=["challenges"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(couples.router, prefix="/couples", tags=["couples"])
