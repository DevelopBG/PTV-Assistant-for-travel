"""
Admin API Routes

Provides administrative endpoints for GTFS data management and service control.
Requires admin API key for authentication.
"""

import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel

from ...data.gtfs_scheduler import get_gtfs_scheduler, initialize_gtfs_scheduler
from ...data.service_manager import get_service_manager
from ...api.dependencies import reset_transit_service

router = APIRouter(prefix="/admin", tags=["admin"])


# Request/Response Models
class UpdateRequest(BaseModel):
    """Request model for manual GTFS update."""
    modes: Optional[list[str]] = None
    """List of modes to update (e.g., ["1", "2", "3"]). If None, updates all configured modes."""


class UpdateResponse(BaseModel):
    """Response model for GTFS update."""
    success: bool
    message: str
    results: Dict[str, Any]
    """Detailed results for each mode."""


class StatusResponse(BaseModel):
    """Response model for update status."""
    last_update: Optional[str]
    """ISO timestamp of last update or None."""
    next_update: Optional[str]
    """ISO timestamp of next scheduled update or None."""
    auto_update_enabled: bool
    update_interval: str
    modes_to_update: list[str]
    rate_limit_delay: float
    """Delay in seconds between downloads to respect rate limits."""
    max_retries: int
    data_versions: Dict[str, str]
    """Current data version for each mode."""


class ReloadResponse(BaseModel):
    """Response model for service reload."""
    success: bool
    message: str


# Helper function to verify admin API key
def verify_admin_key(authorization: str = Header(..., description="Admin API key")):
    """
    Verify admin API key from Authorization header.

    Args:
        authorization: Authorization header value

    Raises:
        HTTPException: If API key is invalid or missing
    """
    admin_key = os.environ.get("ADMIN_API_KEY")

    if not admin_key:
        raise HTTPException(
            status_code=500,
            detail="Admin API key not configured. Set ADMIN_API_KEY environment variable."
        )

    # Support both "Bearer <key>" and direct key formats
    provided_key = authorization
    if authorization.startswith("Bearer "):
        provided_key = authorization[7:]

    if provided_key != admin_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin API key"
        )


@router.post("/gtfs/update", response_model=UpdateResponse)
async def trigger_gtfs_update(
    request: UpdateRequest,
    _: str = Depends(verify_admin_key)
) -> UpdateResponse:
    """
    Manually trigger GTFS data update.

    This endpoint downloads the latest GTFS datasets from PTV, validates them,
    extracts to mode folders, and reloads all services.

    **Authentication**: Requires valid admin API key in Authorization header.

    **Rate Limiting**: Respects PTV's 20 calls/minute limit with configurable delays.

    Args:
        request: Update request with optional mode list
        _: Admin key verification (dependency)

    Returns:
        Update results with success status and details for each mode

    Example:
        ```bash
        curl -X POST "http://localhost:8000/admin/gtfs/update" \\
             -H "Authorization: Bearer your-admin-key" \\
             -H "Content-Type: application/json" \\
             -d '{"modes": ["1", "2", "3"]}'
        ```
    """
    try:
        # Initialize or get existing scheduler
        scheduler = get_gtfs_scheduler()
        if scheduler is None:
            scheduler = initialize_gtfs_scheduler()

        # Run update
        result = scheduler.run_update_now(modes=request.modes, retry_on_failure=True)

        # Check overall success
        success = any(r['success'] for r in result.values())
        successful_count = sum(1 for r in result.values() if r['success'])
        total_count = len(result)

        if success:
            message = f"Successfully updated {successful_count}/{total_count} modes"
        else:
            message = "All updates failed"

        return UpdateResponse(
            success=success,
            message=message,
            results=result
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Update failed: {str(e)}"
        )


@router.get("/gtfs/status", response_model=StatusResponse)
async def get_gtfs_status(
    _: str = Depends(verify_admin_key)
) -> StatusResponse:
    """
    Get GTFS update status and configuration.

    Returns information about the last update, next scheduled update,
    and current data versions.

    **Authentication**: Requires valid admin API key in Authorization header.

    Returns:
        Status information including update times, configuration, and data versions

    Example:
        ```bash
        curl "http://localhost:8000/admin/gtfs/status" \\
             -H "Authorization: Bearer your-admin-key"
        ```
    """
    try:
        # Initialize or get existing scheduler
        scheduler = get_gtfs_scheduler()
        if scheduler is None:
            scheduler = initialize_gtfs_scheduler()

        service_manager = get_service_manager()

        # Get timestamps
        last_update = scheduler.get_last_update_time()
        next_update = scheduler.get_next_update_time()

        # Get data versions
        data_versions = service_manager.get_data_version()

        return StatusResponse(
            last_update=last_update.isoformat() if last_update else None,
            next_update=next_update.isoformat() if next_update else None,
            auto_update_enabled=scheduler.auto_update_enabled,
            update_interval=scheduler.update_interval,
            modes_to_update=scheduler.modes_to_update,
            rate_limit_delay=scheduler.rate_limit_delay,
            max_retries=scheduler.max_retries,
            data_versions=data_versions
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/gtfs/history")
async def get_gtfs_history(
    limit: int = 10,
    _: str = Depends(verify_admin_key)
) -> Dict[str, Any]:
    """
    Get GTFS update history.

    Returns recent update attempts with their results.

    **Authentication**: Requires valid admin API key in Authorization header.

    Args:
        limit: Maximum number of history entries to return (default: 10)

    Returns:
        Update history entries

    Example:
        ```bash
        curl "http://localhost:8000/admin/gtfs/history?limit=20" \\
             -H "Authorization: Bearer your-admin-key"
        ```
    """
    try:
        # Initialize or get existing scheduler
        scheduler = get_gtfs_scheduler()
        if scheduler is None:
            scheduler = initialize_gtfs_scheduler()

        history = scheduler.get_update_history(limit=limit)

        return {
            "total": len(history),
            "limit": limit,
            "history": history
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get history: {str(e)}"
        )


@router.post("/reload", response_model=ReloadResponse)
async def reload_services(
    _: str = Depends(verify_admin_key)
) -> ReloadResponse:
    """
    Reload transit services without downloading new data.

    This endpoint reloads all GTFS parsers and planners from existing data files.
    Useful after manual data updates or to recover from errors.

    **Authentication**: Requires valid admin API key in Authorization header.

    Returns:
        Reload status

    Example:
        ```bash
        curl -X POST "http://localhost:8000/admin/reload" \\
             -H "Authorization: Bearer your-admin-key"
        ```
    """
    try:
        service_manager = get_service_manager()
        success, message = service_manager.reload_all_services()

        return ReloadResponse(
            success=success,
            message=message
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reload failed: {str(e)}"
        )
