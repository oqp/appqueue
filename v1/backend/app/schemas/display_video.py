"""
Schemas Pydantic para DisplayVideo
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DisplayVideoBase(BaseModel):
    """Schema base para DisplayVideo"""

    VideoId: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="ID del video de YouTube"
    )

    Title: Optional[str] = Field(
        None,
        max_length=200,
        description="Título descriptivo del video"
    )

    Description: Optional[str] = Field(
        None,
        max_length=500,
        description="Descripción del video"
    )

    DisplayOrder: int = Field(
        0,
        ge=0,
        description="Orden de reproducción"
    )


class DisplayVideoCreate(DisplayVideoBase):
    """Schema para crear un nuevo video"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "VideoId": "dQw4w9WgXcQ",
                "Title": "Video promocional",
                "Description": "Video para sala de espera",
                "DisplayOrder": 1
            }
        }
    }


class DisplayVideoUpdate(BaseModel):
    """Schema para actualizar un video"""

    VideoId: Optional[str] = Field(None, min_length=1, max_length=50)
    Title: Optional[str] = Field(None, max_length=200)
    Description: Optional[str] = Field(None, max_length=500)
    DisplayOrder: Optional[int] = Field(None, ge=0)
    IsActive: Optional[bool] = Field(None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "Title": "Nuevo título",
                "DisplayOrder": 2,
                "IsActive": True
            }
        }
    }


class DisplayVideoResponse(DisplayVideoBase):
    """Schema para respuestas"""

    Id: int = Field(..., description="ID único del video")
    IsActive: bool = Field(True, description="Estado activo/inactivo")
    CreatedAt: datetime = Field(..., description="Fecha de creación")
    UpdatedAt: Optional[datetime] = Field(None, description="Fecha de última actualización")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "Id": 1,
                "VideoId": "dQw4w9WgXcQ",
                "Title": "Video promocional",
                "Description": "Video para sala de espera",
                "DisplayOrder": 1,
                "IsActive": True,
                "CreatedAt": "2025-01-01T10:00:00",
                "UpdatedAt": None
            }
        }
    }


class DisplayVideoPublicResponse(BaseModel):
    """Schema para respuesta pública (sin autenticación)"""

    VideoId: str = Field(..., description="ID del video de YouTube")
    Title: Optional[str] = Field(None, description="Título del video")
    DisplayOrder: int = Field(..., description="Orden de reproducción")

    model_config = {
        "from_attributes": True
    }


class DisplayVideoListResponse(BaseModel):
    """Schema para lista de videos"""

    videos: List[DisplayVideoResponse] = Field(..., description="Lista de videos")
    total: int = Field(..., description="Total de videos")
    active_count: int = Field(..., description="Videos activos")
