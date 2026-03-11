"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.exceptions import AppException, app_exception_handler, generic_exception_handler
from app.core.logging_config import configure_logging
from app.controllers.auth_controller import router as auth_router
from app.controllers.attendance_controller import router as attendance_router
from app.controllers.student_controller import router as student_router
from app.controllers.face_controller import router as face_router
from app.controllers.subject_controller import router as subject_router
from app.controllers.teacher_controller import router as teacher_router
from app.controllers.student_change_request_controller import router as change_request_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    configure_logging(get_settings().ENVIRONMENT)
    settings = get_settings()
    scheduler = None  # noqa: F841
    if settings.AUTO_LOW_ATTENDANCE_ALERTS:
        from app.core.scheduler import start_scheduler
        scheduler = start_scheduler(enabled=True)
        if scheduler:
            print("[Startup] Low attendance SMS alerts scheduled: 1st of every month at 9:00 AM")
    # Preload embedding cache; defer ML model load on 512MB (set PRELOAD_ML_ENGINES=true to preload)
    try:
        from app.services.face_recognition_service import refresh_embedding_cache, preload_engines
        await refresh_embedding_cache()
        if getattr(settings, "PRELOAD_ML_ENGINES", False):
            preload_engines()
            print("[Startup] Face embedding cache and ML models loaded")
        else:
            print("[Startup] Face embedding cache loaded; ML model will load on first request (saves RAM)")
    except Exception as e:
        print(f"[Startup] Face recognition preload skipped: {e}")
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Enterprise Attendance Tracking System with Facial Recognition",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS - allow Vercel (*.vercel.app) and configured origins
    allow_origins = settings.cors_origins_list
    allow_origin_regex = r"https://[^.]+\.vercel\.app$"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Response compression for faster data transfer
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # Exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Rate limiting (optional - add Limiter if needed)
    # limiter = Limiter(key_func=get_remote_address)
    # app.state.limiter = limiter
    # app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # API routes
    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(attendance_router, prefix=settings.API_V1_PREFIX)
    app.include_router(student_router, prefix=settings.API_V1_PREFIX)
    app.include_router(face_router, prefix=settings.API_V1_PREFIX)
    app.include_router(subject_router, prefix=settings.API_V1_PREFIX)
    app.include_router(teacher_router, prefix=settings.API_V1_PREFIX)
    app.include_router(change_request_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.APP_VERSION}

    @app.get("/health/db")
    async def health_db():
        """Check Supabase connection."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            return {"connected": False, "error": "Supabase credentials not configured"}
        try:
            from app.repositories.database import get_supabase_admin_client
            client = get_supabase_admin_client()
            # Simple query to verify connection (e.g. fetch one row from users)
            client.table("users").select("id").limit(1).execute()
            return {"connected": True, "message": "Supabase connected successfully"}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    return app


app = create_app()
