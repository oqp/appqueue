# archivo: dni_service.py
import json
import requests
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# URL del servicio externo de DNI (Lab Muñoz)
URL = "https://labmunoz.server.ingenius.online/api/p/gpxdni"


def consultar_dni(dni: str, timeout: int = 15) -> Dict:
    """
    Consulta el DNI en el servicio externo de Lab Muñoz.

    La API retorna:
    {
        "errors": [],
        "data": {
            "apellidoPaterno": "QUINTANILLA",
            "apellidoMaterno": "PEREZ",
            "nombres": "OSCAR JAVIER",
            "nombre": "QUINTANILLA PEREZ OSCAR JAVIER",
            "documento": "29636795",
            "sexo": "HOMBRE",
            "fechaNacimiento": "1975-04-30T00:00:00",
            "edad": 50,
            "telefono1": null,
            "email": null,
            ...
        },
        "message": ""
    }

    Returns:
        Diccionario con formato estándar:
        {
            "status": "success" | "error",
            "data": {...} | None,
            "error": {...} | None,
            "meta": {...}
        }
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        url = f"{URL}/{dni}"
        logger.info(f"Consultando DNI en: {url}")

        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        payload = response.json()
        logger.info(f"Respuesta del servicio DNI: {payload}")

        # Verificar si hay errores en la respuesta
        if payload.get("errors") and len(payload["errors"]) > 0:
            return {
                "status": "error",
                "data": None,
                "error": {
                    "message": payload["errors"][0] if payload["errors"] else "Error desconocido",
                    "code": "API_ERROR"
                },
                "meta": {
                    "dni_consultado": dni,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }

        # Verificar si hay datos válidos
        data = payload.get("data")
        if not data:
            return {
                "status": "error",
                "data": None,
                "error": {
                    "message": "DNI no encontrado en el servicio externo",
                    "code": "DNI_NOT_FOUND"
                },
                "meta": {
                    "dni_consultado": dni,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }

        # Mapear la respuesta al formato interno
        # Determinar género basado en la respuesta
        gender = None
        if data.get("generoHombre"):
            gender = "M"
        elif data.get("generoMujer"):
            gender = "F"
        elif data.get("sexo"):
            gender = "M" if data["sexo"].upper() == "HOMBRE" else "F"

        # Parsear fecha de nacimiento
        birth_date = None
        if data.get("fechaNacimiento"):
            try:
                # El formato viene como "1975-04-30T00:00:00"
                birth_date = data["fechaNacimiento"].split("T")[0]
            except Exception:
                birth_date = None

        mapped_data = {
            "DNI": data.get("documento", dni),
            "Nombres": data.get("nombres", ""),
            "ApellidoPaterno": data.get("apellidoPaterno", ""),
            "ApellidoMaterno": data.get("apellidoMaterno", ""),
            "NombreCompleto": data.get("nombre", ""),
            "FechaNacimiento": birth_date,
            "Edad": data.get("edad"),
            "Genero": gender,
            "Telefono": data.get("telefono1"),
            "Email": data.get("email"),
            "Direccion": data.get("direccion")
        }

        return {
            "status": "success",
            "data": mapped_data,
            "meta": {
                "dni_consultado": dni,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

    except requests.exceptions.Timeout:
        logger.error(f"Timeout al consultar DNI: {dni}")
        return {
            "status": "error",
            "data": None,
            "error": {
                "message": "Tiempo de espera agotado al consultar el DNI",
                "code": "TIMEOUT"
            },
            "meta": {
                "dni_consultado": dni,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión al consultar DNI {dni}: {str(e)}")
        return {
            "status": "error",
            "data": None,
            "error": {
                "message": f"Error de conexión: {str(e)}",
                "code": "CONNECTION_ERROR"
            },
            "meta": {
                "dni_consultado": dni,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
    except Exception as e:
        logger.error(f"Error inesperado al consultar DNI {dni}: {str(e)}")
        return {
            "status": "error",
            "data": None,
            "error": {
                "message": f"Error inesperado: {str(e)}",
                "code": "UNKNOWN_ERROR"
            },
            "meta": {
                "dni_consultado": dni,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }


# Permite usarlo como script independiente para pruebas
if __name__ == "__main__":
    # Ejemplo válido
    print(json.dumps(consultar_dni("29636795"), ensure_ascii=False, indent=2))
    # Ejemplo inválido
    print(json.dumps(consultar_dni("123"), ensure_ascii=False, indent=2))
