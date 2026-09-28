from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.errors import register_error_handlers
from app.routers import employees, me, org_units
from app.settings import get_settings
from app.store import store

settings = get_settings()
api = FastAPI(title="Elevate Employee API", version="0.1.0")
api.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Dev-User-Resolved", "X-Dev-User-Source"],
)
register_error_handlers(api)
api.include_router(me.router)
api.include_router(employees.router)
api.include_router(org_units.router)


@api.get("/health", tags=["health"])
def health() -> dict[str, int | str]:
    return {
        "status": "ok",
        "employees": len(store.employees),
        "organisations": len(store.organisations),
    }
