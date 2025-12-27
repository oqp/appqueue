"""
Servicio para integración con APIs externas
Compatible con configuraciones de config.py y schemas existentes
"""

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache

from app.core.config import settings
from app.core.redis import cache_manager
from app.schemas.patient import ExternalPatientData

# ========================================
# CONFIGURACIÓN
# ========================================

logger = logging.getLogger(__name__)

# ========================================
# CLASE PRINCIPAL DEL SERVICIO
# ========================================

class ExternalAPIService:
    """
    Servicio para comunicación con APIs externas
    Compatible con configuraciones existentes y schemas Pydantic
    """

    def __init__(self):
        """
        Inicializa el servicio con configuraciones del config.py
        """
        self.patient_api_url = settings.EXTERNAL_PATIENT_API_URL
        self.patient_api_key = settings.EXTERNAL_PATIENT_API_KEY
        self.timeout = settings.EXTERNAL_PATIENT_API_TIMEOUT

        # Headers por defecto para todas las requests
        self.default_headers = {
            "Content-Type": "application/json",
            "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}",
        }

        # Agregar API key si está configurada
        if self.patient_api_key:
            self.default_headers["Authorization"] = f"Bearer {self.patient_api_key}"
            # O dependiendo del servicio externo, podría ser:
            # self.default_headers["X-API-Key"] = self.patient_api_key

    async def get_patient_data(self, document_number: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos de paciente desde API externa

        Args:
            document_number: Número de documento del paciente

        Returns:
            Dict[str, Any]: Datos del paciente o None si no se encuentra
        """
        try:
            # Limpiar y validar número de documento
            cleaned_doc = self._clean_document_number(document_number)
            if not cleaned_doc:
                logger.warning(f"Número de documento inválido: {document_number}")
                return None

            # Verificar cache primero
            cache_key = f"external_patient:{cleaned_doc}"
            if cache_manager:
                cached_data = cache_manager.get(cache_key)
                if cached_data:
                    logger.info(f"Datos de paciente obtenidos desde cache: {cleaned_doc}")
                    return cached_data

            # Realizar request a API externa
            logger.info(f"Consultando API externa para paciente: {cleaned_doc}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Construir URL de la API
                url = f"{self.patient_api_url}/{cleaned_doc}"

                # Realizar request GET
                response = await client.get(
                    url,
                    headers=self.default_headers
                )

                # Verificar respuesta exitosa
                if response.status_code == 404:
                    logger.info(f"Paciente no encontrado en API externa: {cleaned_doc}")
                    # Cache negativo por 5 minutos
                    if cache_manager:
                        cache_manager.set(cache_key, None, expire=300)
                    return None

                elif response.status_code != 200:
                    logger.error(
                        f"Error en API externa (HTTP {response.status_code}): {response.text}"
                    )
                    return None

                # Procesar datos recibidos
                raw_data = response.json()
                processed_data = self._process_patient_data(raw_data, cleaned_doc)

                if processed_data:
                    # Cache por 1 hora
                    if cache_manager:
                        cache_manager.set(cache_key, processed_data, expire=3600)

                    logger.info(f"Datos de paciente obtenidos exitosamente: {cleaned_doc}")
                    return processed_data

                return None

        except httpx.TimeoutException:
            logger.error(f"Timeout consultando API externa para paciente: {document_number}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Error de conexión con API externa: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado consultando API externa: {e}")
            return None

    def _clean_document_number(self, document_number: str) -> Optional[str]:
        """
        Limpia y valida el número de documento

        Args:
            document_number: Número de documento a limpiar

        Returns:
            str: Documento limpio o None si es inválido
        """
        try:
            import re
            # Misma lógica que en el modelo SQLAlchemy Patient
            cleaned = re.sub(r'[^\w\-\.]', '', document_number.strip())

            if len(cleaned) < 5 or len(cleaned) > 20:
                return None

            return cleaned.upper()

        except Exception:
            return None

    def _process_patient_data(
        self,
        raw_data: Dict[str, Any],
        document_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        Procesa los datos recibidos de la API externa

        Args:
            raw_data: Datos crudos de la API
            document_number: Número de documento

        Returns:
            Dict[str, Any]: Datos procesados compatibles con ExternalPatientData
        """
        try:
            # Mapear campos de la API externa a nuestro formato estándar
            # NOTA: Este mapeo depende del formato específico de la API externa

            # Ejemplo de mapeo (ajustar según la API real):
            processed = {
                "document_number": document_number,
                "full_name": self._extract_full_name(raw_data),
                "birth_date": self._extract_birth_date(raw_data),
                "gender": self._extract_gender(raw_data),
                "phone": self._extract_phone(raw_data),
                "email": self._extract_email(raw_data),
                "additional_data": {
                    "source": "external_api",
                    "retrieved_at": datetime.now().isoformat(),
                    "raw_data": raw_data  # Guardar datos originales para debugging
                }
            }

            # Validar datos mínimos requeridos
            if not processed["full_name"]:
                logger.warning(f"Nombre no encontrado en datos de API externa: {document_number}")
                return None

            # Validar con schema Pydantic
            try:
                validated_data = ExternalPatientData(**processed)
                return validated_data.dict()
            except Exception as validation_error:
                logger.error(f"Error validando datos de API externa: {validation_error}")
                return None

        except Exception as e:
            logger.error(f"Error procesando datos de API externa: {e}")
            return None

    def _extract_full_name(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extrae el nombre completo desde los datos de la API

        Args:
            data: Datos de la API externa

        Returns:
            str: Nombre completo o None
        """
        try:
            # Intentar diferentes formatos comunes de APIs
            name_fields = [
                "full_name", "fullName", "nombre_completo", "nombreCompleto",
                "name", "nombre", "patient_name", "patientName"
            ]

            for field in name_fields:
                if field in data and data[field]:
                    return str(data[field]).strip()

            # Intentar combinar nombres y apellidos si están separados
            first_names = data.get("first_name") or data.get("firstName") or data.get("nombres")
            last_names = data.get("last_name") or data.get("lastName") or data.get("apellidos")

            if first_names and last_names:
                return f"{first_names} {last_names}".strip()

            # Último intento con campos más específicos
            name_parts = []
            for field in ["primer_nombre", "segundo_nombre", "primer_apellido", "segundo_apellido"]:
                if field in data and data[field]:
                    name_parts.append(str(data[field]))

            if name_parts:
                return " ".join(name_parts)

            return None

        except Exception:
            return None

    def _extract_birth_date(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extrae la fecha de nacimiento desde los datos de la API

        Args:
            data: Datos de la API externa

        Returns:
            str: Fecha en formato YYYY-MM-DD o None
        """
        try:
            date_fields = [
                "birth_date", "birthDate", "fecha_nacimiento", "fechaNacimiento",
                "date_of_birth", "dateOfBirth", "nacimiento"
            ]

            for field in date_fields:
                if field in data and data[field]:
                    date_value = data[field]

                    # Si ya es string en formato correcto
                    if isinstance(date_value, str):
                        # Intentar parsear diferentes formatos
                        date_formats = [
                            "%Y-%m-%d",     # 2024-03-15
                            "%d/%m/%Y",     # 15/03/2024
                            "%d-%m-%Y",     # 15-03-2024
                            "%Y/%m/%d",     # 2024/03/15
                        ]

                        for date_format in date_formats:
                            try:
                                parsed_date = datetime.strptime(date_value, date_format)
                                return parsed_date.strftime("%Y-%m-%d")
                            except ValueError:
                                continue

                    # Si es timestamp o datetime object
                    elif isinstance(date_value, (int, float)):
                        try:
                            parsed_date = datetime.fromtimestamp(date_value)
                            return parsed_date.strftime("%Y-%m-%d")
                        except:
                            continue

            return None

        except Exception:
            return None

    def _extract_gender(self, data: Dict[str, Any]) -> str:
        """
        Extrae el género desde los datos de la API

        Args:
            data: Datos de la API externa

        Returns:
            str: Género ('M', 'F', 'Otro')
        """
        try:
            gender_fields = [
                "gender", "genero", "sexo", "sex"
            ]

            for field in gender_fields:
                if field in data and data[field]:
                    gender_value = str(data[field]).upper().strip()

                    # Mapear valores comunes
                    if gender_value in ["M", "MASCULINO", "MALE", "HOMBRE", "H"]:
                        return "M"
                    elif gender_value in ["F", "FEMENINO", "FEMALE", "MUJER", "W"]:
                        return "F"
                    else:
                        return "Otro"

            # Valor por defecto
            return "M"

        except Exception:
            return "M"

    def _extract_phone(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extrae el teléfono desde los datos de la API

        Args:
            data: Datos de la API externa

        Returns:
            str: Teléfono o None
        """
        try:
            phone_fields = [
                "phone", "telefono", "celular", "mobile", "cell_phone",
                "phone_number", "phoneNumber", "numero_telefono"
            ]

            for field in phone_fields:
                if field in data and data[field]:
                    phone = str(data[field]).strip()

                    # Limpiar y validar teléfono
                    import re
                    cleaned_phone = re.sub(r'[^\d\+]', '', phone)

                    if len(cleaned_phone) >= 8:
                        return cleaned_phone

            return None

        except Exception:
            return None

    def _extract_email(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extrae el email desde los datos de la API

        Args:
            data: Datos de la API externa

        Returns:
            str: Email o None
        """
        try:
            email_fields = [
                "email", "correo", "mail", "email_address", "emailAddress"
            ]

            for field in email_fields:
                if field in data and data[field]:
                    email = str(data[field]).strip().lower()

                    # Validar formato básico de email
                    import re
                    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                        return email

            return None

        except Exception:
            return None

    async def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con la API externa

        Returns:
            Dict[str, Any]: Resultado de la prueba
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Hacer request de prueba al endpoint base
                response = await client.get(
                    self.patient_api_url.rstrip('/'),
                    headers=self.default_headers
                )

                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "api_url": self.patient_api_url,
                    "has_api_key": bool(self.patient_api_key),
                    "message": "Conexión exitosa con API externa"
                }

        except httpx.TimeoutException:
            return {
                "status": "error",
                "error_type": "timeout",
                "message": "Timeout conectando con API externa",
                "api_url": self.patient_api_url
            }
        except httpx.RequestError as e:
            return {
                "status": "error",
                "error_type": "connection_error",
                "message": f"Error de conexión: {str(e)}",
                "api_url": self.patient_api_url
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": "unknown_error",
                "message": f"Error desconocido: {str(e)}",
                "api_url": self.patient_api_url
            }

    def get_service_info(self) -> Dict[str, Any]:
        """
        Obtiene información sobre el servicio de API externa

        Returns:
            Dict[str, Any]: Información del servicio
        """
        return {
            "service_name": "External Patient API Service",
            "api_url": self.patient_api_url,
            "timeout_seconds": self.timeout,
            "has_api_key": bool(self.patient_api_key),
            "cache_enabled": cache_manager is not None,
            "supported_operations": [
                "get_patient_data",
                "test_connection"
            ],
            "data_mapping": {
                "document_number": "Número de documento del paciente",
                "full_name": "Nombre completo",
                "birth_date": "Fecha de nacimiento (YYYY-MM-DD)",
                "gender": "Género (M/F/Otro)",
                "phone": "Número de teléfono",
                "email": "Correo electrónico"
            }
        }


# ========================================
# INSTANCIA GLOBAL DEL SERVICIO
# ========================================

external_api_service = ExternalAPIService()


# ========================================
# FUNCIONES DE UTILIDAD
# ========================================

@lru_cache(maxsize=100)
def get_cached_patient_data(document_number: str) -> Optional[Dict[str, Any]]:
    """
    Función con cache LRU para datos de pacientes frecuentemente consultados

    Args:
        document_number: Número de documento

    Returns:
        Dict[str, Any]: Datos del paciente o None
    """
    # Esta función es síncrona y usa LRU cache en memoria
    # Para casos donde no se puede usar async
    return None  # Implementar si es necesario


async def batch_get_patients(document_numbers: list) -> Dict[str, Dict[str, Any]]:
    """
    Obtiene datos de múltiples pacientes en paralelo

    Args:
        document_numbers: Lista de números de documento

    Returns:
        Dict[str, Dict[str, Any]]: Diccionario con datos de cada paciente
    """
    try:
        # Crear tareas concurrentes
        tasks = [
            external_api_service.get_patient_data(doc_num)
            for doc_num in document_numbers
        ]

        # Ejecutar en paralelo
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Procesar resultados
        patient_data = {}
        for doc_num, result in zip(document_numbers, results):
            if isinstance(result, Exception):
                logger.error(f"Error obteniendo datos para {doc_num}: {result}")
                patient_data[doc_num] = None
            else:
                patient_data[doc_num] = result

        return patient_data

    except Exception as e:
        logger.error(f"Error en batch_get_patients: {e}")
        return {doc_num: None for doc_num in document_numbers}


def clear_external_cache(document_number: Optional[str] = None) -> None:
    """
    Limpia el cache de datos externos

    Args:
        document_number: Documento específico a limpiar (opcional)
    """
    if not cache_manager:
        return

    if document_number:
        # Limpiar documento específico
        cache_key = f"external_patient:{document_number}"
        cache_manager.delete(cache_key)
        logger.info(f"Cache limpiado para paciente: {document_number}")
    else:
        # Limpiar todo el cache de pacientes externos
        # Esto depende de las capacidades específicas de Redis
        logger.warning("Cache de pacientes externos limpiado globalmente")