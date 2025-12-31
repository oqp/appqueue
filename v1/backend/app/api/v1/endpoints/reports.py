"""
API endpoints para reportes y estadísticas
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, case, extract
from datetime import datetime, date, timedelta
from typing import Optional
import logging

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, require_supervisor_or_admin
from app.models.user import User
from app.models.ticket import Ticket
from app.models.station import Station
from app.models.service_type import ServiceType

router = APIRouter(prefix="/reports", tags=["reports"])
logger = logging.getLogger(__name__)


@router.get("/dashboard")
async def get_dashboard_stats(
    date_from: Optional[date] = Query(None, description="Fecha inicio"),
    date_to: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Obtiene estadísticas generales para el dashboard de reportes
    """
    try:
        # Fechas por defecto: hoy
        if not date_from:
            date_from = date.today()
        if not date_to:
            date_to = date.today()

        # Query base para el rango de fechas
        base_query = db.query(Ticket).filter(
            cast(Ticket.CreatedAt, Date) >= date_from,
            cast(Ticket.CreatedAt, Date) <= date_to
        )

        # Estadísticas generales
        total_tickets = base_query.count()

        completed_tickets = base_query.filter(Ticket.Status == 'Completed').count()
        cancelled_tickets = base_query.filter(Ticket.Status.in_(['Cancelled', 'NoShow'])).count()
        waiting_tickets = base_query.filter(Ticket.Status == 'Waiting').count()
        in_progress_tickets = base_query.filter(Ticket.Status.in_(['Called', 'InProgress'])).count()

        # Tiempos promedio (solo tickets completados)
        avg_stats = db.query(
            func.avg(Ticket.ActualWaitTime).label('avg_wait'),
            func.avg(Ticket.ServiceTime).label('avg_service'),
            func.max(Ticket.ActualWaitTime).label('max_wait'),
            func.min(Ticket.ActualWaitTime).label('min_wait')
        ).filter(
            cast(Ticket.CreatedAt, Date) >= date_from,
            cast(Ticket.CreatedAt, Date) <= date_to,
            Ticket.Status == 'Completed',
            Ticket.ActualWaitTime.isnot(None)
        ).first()

        return {
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            },
            "tickets": {
                "total": total_tickets,
                "completed": completed_tickets,
                "cancelled": cancelled_tickets,
                "waiting": waiting_tickets,
                "in_progress": in_progress_tickets,
                "completion_rate": round((completed_tickets / total_tickets * 100), 1) if total_tickets > 0 else 0
            },
            "times": {
                "avg_wait_minutes": round(float(avg_stats.avg_wait or 0), 1),
                "avg_service_minutes": round(float(avg_stats.avg_service or 0), 1),
                "max_wait_minutes": int(avg_stats.max_wait or 0),
                "min_wait_minutes": int(avg_stats.min_wait or 0)
            }
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas del dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas"
        )


@router.get("/tickets-by-day")
async def get_tickets_by_day(
    date_from: Optional[date] = Query(None, description="Fecha inicio"),
    date_to: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Obtiene tickets agrupados por día
    """
    try:
        if not date_from:
            date_from = date.today() - timedelta(days=7)
        if not date_to:
            date_to = date.today()

        results = db.query(
            cast(Ticket.CreatedAt, Date).label('date'),
            func.count(Ticket.Id).label('total'),
            func.sum(case((Ticket.Status == 'Completed', 1), else_=0)).label('completed'),
            func.sum(case((Ticket.Status.in_(['Cancelled', 'NoShow']), 1), else_=0)).label('cancelled')
        ).filter(
            cast(Ticket.CreatedAt, Date) >= date_from,
            cast(Ticket.CreatedAt, Date) <= date_to
        ).group_by(
            cast(Ticket.CreatedAt, Date)
        ).order_by(
            cast(Ticket.CreatedAt, Date)
        ).all()

        return {
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            },
            "data": [
                {
                    "date": r.date.isoformat(),
                    "total": r.total,
                    "completed": int(r.completed or 0),
                    "cancelled": int(r.cancelled or 0)
                }
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"Error obteniendo tickets por día: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener datos"
        )


@router.get("/tickets-by-hour")
async def get_tickets_by_hour(
    report_date: Optional[date] = Query(None, description="Fecha del reporte"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Obtiene tickets agrupados por hora del día (horas pico)
    """
    try:
        if not report_date:
            report_date = date.today()

        results = db.query(
            extract('hour', Ticket.CreatedAt).label('hour'),
            func.count(Ticket.Id).label('total')
        ).filter(
            cast(Ticket.CreatedAt, Date) == report_date
        ).group_by(
            extract('hour', Ticket.CreatedAt)
        ).order_by(
            extract('hour', Ticket.CreatedAt)
        ).all()

        # Crear array completo de 24 horas
        hours_data = {int(r.hour): r.total for r in results}
        full_data = [
            {"hour": h, "total": hours_data.get(h, 0)}
            for h in range(24)
        ]

        # Encontrar hora pico
        peak_hour = max(full_data, key=lambda x: x['total']) if full_data else {"hour": 0, "total": 0}

        return {
            "date": report_date.isoformat(),
            "data": full_data,
            "peak_hour": {
                "hour": f"{peak_hour['hour']:02d}:00",
                "tickets": peak_hour['total']
            }
        }

    except Exception as e:
        logger.error(f"Error obteniendo tickets por hora: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener datos"
        )


@router.get("/by-service")
async def get_stats_by_service(
    date_from: Optional[date] = Query(None, description="Fecha inicio"),
    date_to: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Obtiene estadísticas agrupadas por tipo de servicio
    """
    try:
        if not date_from:
            date_from = date.today()
        if not date_to:
            date_to = date.today()

        results = db.query(
            ServiceType.Id,
            ServiceType.Name,
            ServiceType.Code,
            ServiceType.Color,
            func.count(Ticket.Id).label('total'),
            func.sum(case((Ticket.Status == 'Completed', 1), else_=0)).label('completed'),
            func.avg(Ticket.ActualWaitTime).label('avg_wait'),
            func.avg(Ticket.ServiceTime).label('avg_service')
        ).join(
            Ticket, Ticket.ServiceTypeId == ServiceType.Id
        ).filter(
            cast(Ticket.CreatedAt, Date) >= date_from,
            cast(Ticket.CreatedAt, Date) <= date_to
        ).group_by(
            ServiceType.Id,
            ServiceType.Name,
            ServiceType.Code,
            ServiceType.Color
        ).order_by(
            func.count(Ticket.Id).desc()
        ).all()

        return {
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            },
            "data": [
                {
                    "service_id": r.Id,
                    "service_name": r.Name,
                    "service_code": r.Code,
                    "color": r.Color,
                    "total": r.total,
                    "completed": int(r.completed or 0),
                    "completion_rate": round((int(r.completed or 0) / r.total * 100), 1) if r.total > 0 else 0,
                    "avg_wait_minutes": round(float(r.avg_wait or 0), 1),
                    "avg_service_minutes": round(float(r.avg_service or 0), 1)
                }
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas por servicio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener datos"
        )


@router.get("/by-station")
async def get_stats_by_station(
    date_from: Optional[date] = Query(None, description="Fecha inicio"),
    date_to: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Obtiene estadísticas agrupadas por estación/ventanilla
    """
    try:
        if not date_from:
            date_from = date.today()
        if not date_to:
            date_to = date.today()

        results = db.query(
            Station.Id,
            Station.Name,
            Station.Code,
            func.count(Ticket.Id).label('total'),
            func.sum(case((Ticket.Status == 'Completed', 1), else_=0)).label('completed'),
            func.avg(Ticket.ServiceTime).label('avg_service')
        ).join(
            Ticket, Ticket.StationId == Station.Id
        ).filter(
            cast(Ticket.CreatedAt, Date) >= date_from,
            cast(Ticket.CreatedAt, Date) <= date_to,
            Ticket.StationId.isnot(None)
        ).group_by(
            Station.Id,
            Station.Name,
            Station.Code
        ).order_by(
            func.count(Ticket.Id).desc()
        ).all()

        return {
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            },
            "data": [
                {
                    "station_id": r.Id,
                    "station_name": r.Name,
                    "station_code": r.Code,
                    "total": r.total,
                    "completed": int(r.completed or 0),
                    "completion_rate": round((int(r.completed or 0) / r.total * 100), 1) if r.total > 0 else 0,
                    "avg_service_minutes": round(float(r.avg_service or 0), 1)
                }
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas por estación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener datos"
        )


@router.get("/wait-times")
async def get_wait_time_distribution(
    date_from: Optional[date] = Query(None, description="Fecha inicio"),
    date_to: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Obtiene distribución de tiempos de espera
    """
    try:
        if not date_from:
            date_from = date.today()
        if not date_to:
            date_to = date.today()

        # Rangos de tiempo de espera
        results = db.query(
            case(
                (Ticket.ActualWaitTime <= 5, '0-5 min'),
                (Ticket.ActualWaitTime <= 10, '6-10 min'),
                (Ticket.ActualWaitTime <= 15, '11-15 min'),
                (Ticket.ActualWaitTime <= 30, '16-30 min'),
                else_='+30 min'
            ).label('range'),
            func.count(Ticket.Id).label('count')
        ).filter(
            cast(Ticket.CreatedAt, Date) >= date_from,
            cast(Ticket.CreatedAt, Date) <= date_to,
            Ticket.Status == 'Completed',
            Ticket.ActualWaitTime.isnot(None)
        ).group_by(
            case(
                (Ticket.ActualWaitTime <= 5, '0-5 min'),
                (Ticket.ActualWaitTime <= 10, '6-10 min'),
                (Ticket.ActualWaitTime <= 15, '11-15 min'),
                (Ticket.ActualWaitTime <= 30, '16-30 min'),
                else_='+30 min'
            )
        ).all()

        # Ordenar rangos
        order = ['0-5 min', '6-10 min', '11-15 min', '16-30 min', '+30 min']
        data_dict = {r.range: r.count for r in results}
        ordered_data = [
            {"range": rng, "count": data_dict.get(rng, 0)}
            for rng in order
        ]

        return {
            "period": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            },
            "data": ordered_data
        }

    except Exception as e:
        logger.error(f"Error obteniendo distribución de tiempos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener datos"
        )


__all__ = ["router"]
