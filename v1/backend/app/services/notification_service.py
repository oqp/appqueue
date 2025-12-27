"""
Servicio de notificaciones para el sistema de gestión de colas
Compatible con la estructura existente del proyecto
Maneja SMS, emails y notificaciones push
"""

import httpx
import smtplib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import asyncio
from enum import Enum

from app.core.config import settings
from app.core.redis import cache_manager

# ========================================
# CONFIGURACIÓN Y ENUMS
# ========================================

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Tipos de notificaciones"""
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WEBSOCKET = "websocket"


class NotificationPriority(str, Enum):
    """Prioridades de notificación"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# ========================================
# CLASE PRINCIPAL DEL SERVICIO
# ========================================

class NotificationService:
    """
    Servicio principal de notificaciones
    Maneja SMS, emails y notificaciones en tiempo real
    """

    def __init__(self):
        """Inicializa el servicio de notificaciones"""
        self.sms_enabled = settings.SMS_ENABLED
        # self.email_enabled = settings.EMAIL_ENABLED

        # Configuración SMS
        self.sms_api_url = getattr(settings, 'SMS_API_URL', 'https://api.sms-provider.com/send')
        self.sms_api_key = getattr(settings, 'SMS_API_KEY', '')
        self.sms_from_number = getattr(settings, 'SMS_FROM_NUMBER', '+51999999999')

        # Configuración Email
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USERNAME', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.email_from = getattr(settings, 'EMAIL_FROM', 'noreply@laboratorio.com')

        # Rate limiting y cache
        self.max_sms_per_hour = 100
        self.max_emails_per_hour = 500

    async def send_sms(
            self,
            phone_number: str,
            message: str,
            priority: NotificationPriority = NotificationPriority.NORMAL,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Envía mensaje SMS usando API personalizada

        Args:
            phone_number: Número de teléfono (+51987654321)
            message: Mensaje a enviar
            priority: Prioridad del mensaje
            **kwargs: Parámetros adicionales (ticket_id, service_type, etc.)

        Returns:
            Dict: Resultado del envío
        """
        try:
            if not self.sms_enabled or not self.sms_api_key:
                logger.warning("SMS no configurado o deshabilitado")
                return {
                    "success": False,
                    "message": "SMS no configurado",
                    "provider": "disabled"
                }

            # Validar número de teléfono
            if not self._validate_phone_number(phone_number):
                return {
                    "success": False,
                    "message": "Número de teléfono inválido",
                    "phone_number": phone_number
                }

            # Verificar rate limiting
            if not await self._check_sms_rate_limit(phone_number):
                return {
                    "success": False,
                    "message": "Rate limit excedido para este número",
                    "phone_number": phone_number
                }

            # Preparar payload para API personalizada
            payload = {
                "phone_number": phone_number,
                "message": message,
                "priority": priority.value,
                "from_number": self.sms_from_number,
                "timestamp": datetime.now().isoformat()
            }

            # Agregar parámetros adicionales si se proporcionan
            if kwargs:
                payload.update({
                    "ticket_id": kwargs.get("ticket_id"),
                    "service_type": kwargs.get("service_type"),
                    "station_id": kwargs.get("station_id"),
                    "metadata": kwargs
                })

            # Enviar SMS via API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.sms_api_key}",
                "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.sms_api_url,
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    result = response.json()

                    # Registrar envío exitoso
                    await self._log_notification(
                        NotificationType.SMS,
                        phone_number,
                        message,
                        True,
                        result.get("message_id"),
                        **kwargs
                    )

                    logger.info(f"SMS enviado exitosamente a {phone_number}")

                    return {
                        "success": True,
                        "message": "SMS enviado correctamente",
                        "message_id": result.get("message_id"),
                        "provider": "custom_api",
                        "phone_number": phone_number
                    }
                else:
                    error_msg = f"Error del proveedor SMS: {response.status_code}"
                    logger.error(f"Error enviando SMS: {error_msg}")

                    await self._log_notification(
                        NotificationType.SMS,
                        phone_number,
                        message,
                        False,
                        error_msg,
                        **kwargs
                    )

                    return {
                        "success": False,
                        "message": error_msg,
                        "status_code": response.status_code,
                        "provider": "custom_api"
                    }

        except httpx.TimeoutException:
            error_msg = "Timeout enviando SMS"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

        except Exception as e:
            error_msg = f"Error interno enviando SMS: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

    async def send_email(
            self,
            to_email: str,
            subject: str,
            message: str,
            html_message: Optional[str] = None,
            priority: NotificationPriority = NotificationPriority.NORMAL,
            attachments: Optional[List[str]] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Envía email usando SMTP

        Args:
            to_email: Email destinatario
            subject: Asunto del email
            message: Mensaje en texto plano
            html_message: Mensaje en HTML (opcional)
            priority: Prioridad del email
            attachments: Lista de rutas de archivos adjuntos
            **kwargs: Parámetros adicionales

        Returns:
            Dict: Resultado del envío
        """
        try:
            if not self.email_enabled or not self.smtp_username:
                logger.warning("Email no configurado o deshabilitado")
                return {
                    "success": False,
                    "message": "Email no configurado",
                    "provider": "disabled"
                }

            # Validar email
            if not self._validate_email(to_email):
                return {
                    "success": False,
                    "message": "Email inválido",
                    "email": to_email
                }

            # Verificar rate limiting
            if not await self._check_email_rate_limit(to_email):
                return {
                    "success": False,
                    "message": "Rate limit excedido para este email",
                    "email": to_email
                }

            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = to_email
            msg['Subject'] = subject

            # Agregar headers de prioridad
            if priority == NotificationPriority.HIGH:
                msg['X-Priority'] = '2'
            elif priority == NotificationPriority.URGENT:
                msg['X-Priority'] = '1'

            # Agregar contenido texto plano
            part1 = MIMEText(message, 'plain', 'utf-8')
            msg.attach(part1)

            # Agregar contenido HTML si se proporciona
            if html_message:
                part2 = MIMEText(html_message, 'html', 'utf-8')
                msg.attach(part2)

            # Agregar archivos adjuntos si se proporcionan
            if attachments:
                for file_path in attachments:
                    try:
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {file_path.split("/")[-1]}'
                            )
                            msg.attach(part)
                    except Exception as e:
                        logger.warning(f"No se pudo adjuntar archivo {file_path}: {e}")

            # Enviar email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.email_from, to_email, text)

            # Registrar envío exitoso
            await self._log_notification(
                NotificationType.EMAIL,
                to_email,
                f"Subject: {subject}\n{message}",
                True,
                None,
                **kwargs
            )

            logger.info(f"Email enviado exitosamente a {to_email}")

            return {
                "success": True,
                "message": "Email enviado correctamente",
                "email": to_email,
                "subject": subject,
                "provider": "smtp"
            }

        except smtplib.SMTPException as e:
            error_msg = f"Error SMTP: {str(e)}"
            logger.error(f"Error enviando email: {error_msg}")

            await self._log_notification(
                NotificationType.EMAIL,
                to_email,
                f"Subject: {subject}\n{message}",
                False,
                error_msg,
                **kwargs
            )

            return {
                "success": False,
                "message": error_msg,
                "provider": "smtp"
            }

        except Exception as e:
            error_msg = f"Error interno enviando email: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

    async def send_ticket_notification(
            self,
            phone_number: Optional[str],
            email: Optional[str],
            ticket_number: str,
            station_name: str,
            notification_type: str,
            patient_name: Optional[str] = None,
            estimated_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Envía notificación específica para tickets

        Args:
            phone_number: Teléfono del paciente
            email: Email del paciente
            ticket_number: Número de ticket
            station_name: Nombre de la estación
            notification_type: Tipo de notificación (called, next, reminder)
            patient_name: Nombre del paciente
            estimated_time: Tiempo estimado en minutos

        Returns:
            Dict: Resultado de las notificaciones enviadas
        """
        try:
            results = {
                "sms": None,
                "email": None,
                "success": False,
                "messages_sent": 0
            }

            # Generar mensajes según el tipo
            messages = self._generate_ticket_messages(
                ticket_number,
                station_name,
                notification_type,
                patient_name,
                estimated_time
            )

            # Enviar SMS si hay número de teléfono
            if phone_number and self.sms_enabled:
                sms_result = await self.send_sms(
                    phone_number,
                    messages["sms"],
                    priority=NotificationPriority.HIGH,
                    ticket_id=ticket_number,
                    station_name=station_name,
                    notification_type=notification_type
                )
                results["sms"] = sms_result
                if sms_result["success"]:
                    results["messages_sent"] += 1

            # Enviar Email si hay email
            if email and self.email_enabled:
                email_result = await self.send_email(
                    email,
                    messages["email_subject"],
                    messages["email_body"],
                    messages.get("email_html"),
                    priority=NotificationPriority.HIGH,
                    ticket_id=ticket_number,
                    station_name=station_name,
                    notification_type=notification_type
                )
                results["email"] = email_result
                if email_result["success"]:
                    results["messages_sent"] += 1

            results["success"] = results["messages_sent"] > 0

            logger.info(f"Notificación de ticket {ticket_number}: {results['messages_sent']} mensajes enviados")

            return results

        except Exception as e:
            logger.error(f"Error enviando notificación de ticket: {e}")
            return {
                "sms": None,
                "email": None,
                "success": False,
                "messages_sent": 0,
                "error": str(e)
            }

    async def send_bulk_notifications(
            self,
            notifications: List[Dict[str, Any]],
            batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Envía notificaciones en lote

        Args:
            notifications: Lista de notificaciones a enviar
            batch_size: Tamaño del lote

        Returns:
            Dict: Resumen de envíos
        """
        try:
            total = len(notifications)
            success_count = 0
            failed_count = 0
            results = []

            # Procesar en lotes
            for i in range(0, total, batch_size):
                batch = notifications[i:i + batch_size]
                batch_results = await asyncio.gather(
                    *[self._send_single_notification(notif) for notif in batch],
                    return_exceptions=True
                )

                for result in batch_results:
                    if isinstance(result, Exception):
                        failed_count += 1
                        results.append({"success": False, "error": str(result)})
                    else:
                        if result.get("success"):
                            success_count += 1
                        else:
                            failed_count += 1
                        results.append(result)

                # Pausa entre lotes para no saturar
                if i + batch_size < total:
                    await asyncio.sleep(1)

            logger.info(f"Envío masivo completado: {success_count} exitosos, {failed_count} fallidos")

            return {
                "total": total,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": (success_count / total * 100) if total > 0 else 0,
                "results": results
            }

        except Exception as e:
            logger.error(f"Error en envío masivo: {e}")
            return {
                "total": len(notifications),
                "success_count": 0,
                "failed_count": len(notifications),
                "success_rate": 0,
                "error": str(e)
            }

    # ========================================
    # MÉTODOS PRIVADOS/AUXILIARES
    # ========================================

    def _validate_phone_number(self, phone_number: str) -> bool:
        """Valida formato de número de teléfono"""
        try:
            # Formato: +51987654321 (Perú)
            import re
            pattern = r'^\+51[0-9]{9}$'
            return bool(re.match(pattern, phone_number))
        except Exception:
            return False

    def _validate_email(self, email: str) -> bool:
        """Valida formato de email"""
        try:
            import re
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, email))
        except Exception:
            return False

    async def _check_sms_rate_limit(self, phone_number: str) -> bool:
        """Verifica rate limiting para SMS"""
        try:
            if not cache_manager:
                return True  # Sin cache, no hay rate limiting

            cache_key = f"sms_rate_limit:{phone_number}"
            count = cache_manager.get(cache_key) or 0

            if count >= self.max_sms_per_hour:
                return False

            # Incrementar contador
            cache_manager.set(cache_key, count + 1, expire=3600)  # 1 hora
            return True

        except Exception as e:
            logger.error(f"Error verificando rate limit SMS: {e}")
            return True  # En caso de error, permitir envío

    async def _check_email_rate_limit(self, email: str) -> bool:
        """Verifica rate limiting para emails"""
        try:
            if not cache_manager:
                return True

            cache_key = f"email_rate_limit:{email}"
            count = cache_manager.get(cache_key) or 0

            if count >= self.max_emails_per_hour:
                return False

            cache_manager.set(cache_key, count + 1, expire=3600)
            return True

        except Exception as e:
            logger.error(f"Error verificando rate limit email: {e}")
            return True

    async def _log_notification(
            self,
            notification_type: NotificationType,
            recipient: str,
            message: str,
            success: bool,
            message_id: Optional[str] = None,
            **kwargs
    ) -> None:
        """Registra el envío de notificación para auditoría"""
        try:
            log_data = {
                "type": notification_type.value,
                "recipient": recipient,
                "message": message[:100] + "..." if len(message) > 100 else message,
                "success": success,
                "message_id": message_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": kwargs
            }

            # Guardar en cache para consultas recientes
            if cache_manager:
                cache_key = f"notification_log:{datetime.now().strftime('%Y%m%d')}"
                existing_logs = cache_manager.get(cache_key) or []
                existing_logs.append(log_data)

                # Mantener solo los últimos 1000 logs del día
                if len(existing_logs) > 1000:
                    existing_logs = existing_logs[-1000:]

                cache_manager.set(cache_key, existing_logs, expire=86400)  # 24 horas

            # Log adicional para debugging
            if success:
                logger.debug(f"Notificación {notification_type.value} enviada a {recipient}")
            else:
                logger.warning(f"Falló notificación {notification_type.value} a {recipient}: {message_id}")

        except Exception as e:
            logger.error(f"Error registrando notificación: {e}")

    def _generate_ticket_messages(
            self,
            ticket_number: str,
            station_name: str,
            notification_type: str,
            patient_name: Optional[str] = None,
            estimated_time: Optional[int] = None
    ) -> Dict[str, str]:
        """Genera mensajes personalizados para notificaciones de tickets"""

        greeting = f"Hola {patient_name}, " if patient_name else "Estimado paciente, "

        if notification_type == "called":
            sms_msg = f"Ticket {ticket_number}: Diríjase a {station_name} para su atención."
            email_subject = f"Llamada para atención - Ticket {ticket_number}"
            email_body = f"{greeting}su ticket {ticket_number} está siendo llamado. Por favor diríjase a {station_name}."

        elif notification_type == "next":
            time_msg = f" en aproximadamente {estimated_time} minutos" if estimated_time else ""
            sms_msg = f"Ticket {ticket_number}: Será atendido pronto{time_msg}. Esté atento."
            email_subject = f"Próximo en atención - Ticket {ticket_number}"
            email_body = f"{greeting}su ticket {ticket_number} será atendido pronto{time_msg}. Manténgase cerca de {station_name}."

        elif notification_type == "reminder":
            sms_msg = f"Recordatorio: Ticket {ticket_number} pendiente de atención en {station_name}."
            email_subject = f"Recordatorio de atención - Ticket {ticket_number}"
            email_body = f"{greeting}le recordamos que su ticket {ticket_number} está pendiente de atención en {station_name}."

        else:
            sms_msg = f"Ticket {ticket_number}: Actualización de estado."
            email_subject = f"Actualización - Ticket {ticket_number}"
            email_body = f"{greeting}hay una actualización sobre su ticket {ticket_number}."

        # HTML version del email
        email_html = f"""
        <html>
            <body>
                <h2>Laboratorio Clínico - Sistema de Colas</h2>
                <p>{email_body}</p>
                <p><strong>Ticket:</strong> {ticket_number}<br>
                <strong>Estación:</strong> {station_name}</p>
                <hr>
                <p><small>Este es un mensaje automatizado. No responda a este email.</small></p>
            </body>
        </html>
        """

        return {
            "sms": sms_msg,
            "email_subject": email_subject,
            "email_body": email_body,
            "email_html": email_html
        }

    async def _send_single_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Envía una notificación individual para procesamiento en lote"""
        try:
            notif_type = notification.get("type", "sms")

            if notif_type == "sms":
                return await self.send_sms(
                    notification["phone_number"],
                    notification["message"],
                    notification.get("priority", NotificationPriority.NORMAL),
                    **notification.get("kwargs", {})
                )
            elif notif_type == "email":
                return await self.send_email(
                    notification["email"],
                    notification["subject"],
                    notification["message"],
                    notification.get("html_message"),
                    notification.get("priority", NotificationPriority.NORMAL),
                    notification.get("attachments"),
                    **notification.get("kwargs", {})
                )
            else:
                return {"success": False, "message": f"Tipo de notificación no soportado: {notif_type}"}

        except Exception as e:
            return {"success": False, "message": str(e)}


# ========================================
# INSTANCIA GLOBAL
# ========================================

notification_service = NotificationService()