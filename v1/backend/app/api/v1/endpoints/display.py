"""
API endpoints para gestión de pantallas de display (videos)
Incluye endpoints públicos y administrativos
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, require_supervisor_or_admin
from app.models.user import User
from app.models.display_video import DisplayVideo
from app.crud.display_video import display_video_crud
from app.schemas.display_video import (
    DisplayVideoCreate,
    DisplayVideoUpdate,
    DisplayVideoResponse,
    DisplayVideoPublicResponse,
    DisplayVideoListResponse
)

router = APIRouter(prefix="/display", tags=["display"])
logger = logging.getLogger(__name__)


# ========================================
# ENDPOINTS PÚBLICOS (sin autenticación)
# ========================================

@router.get("/public/videos", response_model=List[DisplayVideoPublicResponse])
async def get_public_videos(
    db: Session = Depends(get_db)
):
    """
    Obtiene lista de videos activos para pantallas de display - PÚBLICO

    Sin autenticación, para uso en tv01.html, tv02.html, etc.
    Solo retorna videos activos ordenados por DisplayOrder.
    """
    try:
        videos = display_video_crud.get_active_videos(db, limit=50)
        return videos
    except Exception as e:
        logger.error(f"Error obteniendo videos públicos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener videos"
        )


# ========================================
# ENDPOINTS ADMINISTRATIVOS
# ========================================

@router.get("/videos", response_model=DisplayVideoListResponse)
async def get_all_videos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los videos (activos e inactivos)

    Permisos: Usuario autenticado
    """
    try:
        videos = display_video_crud.get_all_ordered(db, skip=skip, limit=limit)
        total = len(videos)
        active_count = len([v for v in videos if v.IsActive])

        return DisplayVideoListResponse(
            videos=videos,
            total=total,
            active_count=active_count
        )
    except Exception as e:
        logger.error(f"Error obteniendo videos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener videos"
        )


@router.get("/videos/{video_id}", response_model=DisplayVideoResponse)
async def get_video(
    video_id: int = Path(..., description="ID del video"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene un video específico por ID

    Permisos: Usuario autenticado
    """
    video = display_video_crud.get(db, id=video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video no encontrado"
        )
    return video


@router.post("/videos", response_model=DisplayVideoResponse)
async def create_video(
    video_data: DisplayVideoCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Crea un nuevo video

    Permisos: Supervisor o Admin
    """
    try:
        # Verificar si ya existe un video con ese VideoId
        existing = display_video_crud.get_by_video_id(db, video_id=video_data.VideoId)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un video con el ID de YouTube: {video_data.VideoId}"
            )

        video = display_video_crud.create(db, obj_in=video_data)
        logger.info(f"Video creado: {video.VideoId} por {current_user.Username}")
        return video

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando video: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear video"
        )


@router.patch("/videos/{video_id}", response_model=DisplayVideoResponse)
async def update_video(
    video_id: int = Path(..., description="ID del video"),
    video_data: DisplayVideoUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Actualiza un video existente

    Permisos: Supervisor o Admin
    """
    try:
        video = display_video_crud.get(db, id=video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video no encontrado"
            )

        # Si se está cambiando el VideoId, verificar que no exista
        if video_data.VideoId and video_data.VideoId != video.VideoId:
            existing = display_video_crud.get_by_video_id(db, video_id=video_data.VideoId)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ya existe un video con el ID de YouTube: {video_data.VideoId}"
                )

        video = display_video_crud.update(db, db_obj=video, obj_in=video_data)
        logger.info(f"Video {video_id} actualizado por {current_user.Username}")
        return video

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar video"
        )


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int = Path(..., description="ID del video"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Elimina un video

    Permisos: Supervisor o Admin
    """
    try:
        video = display_video_crud.get(db, id=video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video no encontrado"
            )

        display_video_crud.remove(db, id=video_id)
        logger.info(f"Video {video_id} eliminado por {current_user.Username}")

        return {"message": "Video eliminado correctamente", "id": video_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar video"
        )


@router.post("/videos/{video_id}/toggle-active", response_model=DisplayVideoResponse)
async def toggle_video_active(
    video_id: int = Path(..., description="ID del video"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Activa/desactiva un video

    Permisos: Supervisor o Admin
    """
    try:
        video = display_video_crud.toggle_active(db, video_id=video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video no encontrado"
            )

        status_text = "activado" if video.IsActive else "desactivado"
        logger.info(f"Video {video_id} {status_text} por {current_user.Username}")
        return video

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error alternando estado del video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar estado del video"
        )


@router.patch("/videos/{video_id}/order", response_model=DisplayVideoResponse)
async def update_video_order(
    video_id: int = Path(..., description="ID del video"),
    new_order: int = Body(..., embed=True, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Actualiza el orden de un video

    Permisos: Supervisor o Admin
    """
    try:
        video = display_video_crud.update_order(db, video_id=video_id, new_order=new_order)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video no encontrado"
            )

        logger.info(f"Orden del video {video_id} actualizado a {new_order} por {current_user.Username}")
        return video

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando orden del video {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar orden del video"
        )


__all__ = ["router"]
