"""
Modelo para videos de pantallas de display (TV)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .base import BaseModel, TimestampMixin, ActiveMixin


class DisplayVideo(BaseModel, TimestampMixin, ActiveMixin):
    """
    Modelo para gestionar videos de YouTube en pantallas de display
    """
    __tablename__ = 'DisplayVideos'

    Id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="ID único del video"
    )

    VideoId = Column(
        String(50),
        nullable=False,
        unique=True,
        comment="ID del video de YouTube"
    )

    Title = Column(
        String(200),
        nullable=True,
        comment="Título descriptivo del video"
    )

    Description = Column(
        String(500),
        nullable=True,
        comment="Descripción del video"
    )

    DisplayOrder = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Orden de reproducción"
    )

    def __repr__(self) -> str:
        return f"<DisplayVideo(Id={self.Id}, VideoId='{self.VideoId}', Title='{self.Title}')>"
