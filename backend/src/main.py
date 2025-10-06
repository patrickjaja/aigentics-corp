"""
AI Offer Agent - Main FastAPI Application

Entry point for the API Gateway that combines all services.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import os
import logging

from .api import api_router, health_api_router
from .api.health import initialize_health_checks
from .infrastructure.middleware.rate_limit import shutdown_rate_limiter
from .monitoring.metrics import MetricsCollector


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Create FastAPI application
app = FastAPI(
    title="AI Offer Agent API",
    description="AI-powered offer generation system with conversation management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
)


# GZip Middleware for response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.

    Logs error and returns generic 500 response.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {
                "type": type(exc).__name__
            }
        }
    )


# Include API routes
app.include_router(api_router)
app.include_router(health_api_router)


# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.

    Returns system status and service availability.
    """
    return {
        "status": "healthy",
        "service": "ai-offer-agent",
        "version": "1.0.0",
        "services": {
            "conversations": "ok",
            "offers": "ok",
            "customers": "ok",
            "admin": "ok"
        }
    }


# Readiness probe
@app.get("/ready", tags=["system"])
async def readiness_check():
    """
    Readiness probe for Kubernetes.

    Checks if application is ready to serve traffic.
    """
    # TODO: Add actual dependency checks
    # - Database connection
    # - Redis connection
    # - External service health
    return {
        "status": "ready",
        "dependencies": {
            "database": "connected",
            "redis": "connected",
            "llm_service": "available"
        }
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup tasks.

    Initializes connections and loads configuration.
    """
    logger.info("Starting AI Offer Agent API...")

    # Initialize health check system
    initialize_health_checks()

    # TODO: Initialize connections
    # - Database connection pool
    # - Redis connection
    # - LLM service client
    # - Event bus

    logger.info("API startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown tasks.

    Closes connections and cleans up resources.
    """
    logger.info("Shutting down AI Offer Agent API...")

    # Close rate limiter Redis connection
    await shutdown_rate_limiter()

    # TODO: Close other connections
    # - Database connections
    # - Event bus

    logger.info("API shutdown complete")


# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """
    API root endpoint with service information.
    """
    return {
        "service": "AI Offer Agent API",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "conversations": "/v1/conversations",
            "offers": "/v1/offers",
            "customers": "/v1/customers",
            "approvals": "/v1/approvals"
        }
    }


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
