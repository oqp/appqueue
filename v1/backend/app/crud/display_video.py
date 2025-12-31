"""
Operaciones CRUD para DisplayVideo
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.crud.base import CRUDBase
from app.models.display_video import DisplayVideo
from app.schemas.display_video import DisplayVideoCreate, DisplayVideoUpdate

logger = logging.getLogger(__name__)


class CRUDDisplayVideo(CRUDBase[DisplayVideo, DisplayVideoCreate, DisplayVideoUpdate]):
    """
    Operaciones CRUD para videos de display
    """

    def get_by_video_id(self, db: Session, *, video_id: str) -> Optional[DisplayVideo]:
        """
        Busca un video por su ID de YouTube
        """
        try:
            return db.query(DisplayVideo).filter(
                DisplayVideo.VideoId == video_id
            ).first()
        except Exception as e:
            logger.error(f"Error buscando video por VideoId {video_id}: {e}")
            return None

    def get_active_videos(self, db: Session, *, limit: int = 50) -> List[DisplayVideo]:
        """
        Obtiene todos los videos activos ordenados por DisplayOrder
        """
        try:
            return db.query(DisplayVideo).filter(
                DisplayVideo.IsActive == True
            ).order_by(DisplayVideo.DisplayOrder.asc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error obteniendo videos activos: {e}")
            return []

    def get_all_ordered(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[DisplayVideo]:
        """
        Obtiene todos los videos ordenados por DisplayOrder
        """
        try:
            return db.query(DisplayVideo).order_by(
                DisplayVideo.DisplayOrder.asc()
            ).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error obteniendo videos ordenados: {e}")
            return []

    def update_order(self, db: Session, *, video_id: int, new_order: int) -> Optional[DisplayVideo]:
        """
        Actualiza el orden de un video
        """
        try:
            video = self.get(db, id=video_id)
            if video:
                video.DisplayOrder = new_order
                db.commit()
                db.refresh(video)
            return video
        except Exception as e:
            logger.error(f"Error actualizando orden del video {video_id}: {e}")
            db.rollback()
            return None

    def toggle_active(self, db: Session, *, video_id: int) -> Optional[DisplayVideo]:
        """
        Alterna el estado activo de un video
        """
        try:
            video = self.get(db, id=video_id)
            if video:
                video.IsActive = not video.IsActive
                db.commit()
                db.refresh(video)
            return video
        except Exception as e:
            logger.error(f"Error alternando estado del video {video_id}: {e}")
            db.rollback()
            return None


# Instancia singleton del CRUD
display_video_crud = CRUDDisplayVideo(DisplayVideo)
