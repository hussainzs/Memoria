from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .db.session import engine
from .db import models


def create_app() -> FastAPI:
    app = FastAPI(title="Memoria API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .routers.health import router as health_router
    from .routers.memories import router as memories_router
    from .routers.retrieve import router as retrieve_router
    from .routers.ask import router as ask_router
    from .routers.feedback import router as feedback_router
    from .routers.temporal import router as temporal_router
    from .routers.verification import router as verification_router

    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(memories_router, prefix="/memories", tags=["memories"])
    app.include_router(retrieve_router, prefix="/retrieve", tags=["retrieve"])
    app.include_router(ask_router, prefix="/ask", tags=["ask"])
    app.include_router(feedback_router, prefix="/feedback", tags=["feedback"])
    app.include_router(temporal_router, prefix="/temporal", tags=["temporal"])
    app.include_router(verification_router, prefix="/verification", tags=["verification"])

    @app.on_event("startup")
    def on_startup() -> None:
        pass

    return app


app = create_app()


