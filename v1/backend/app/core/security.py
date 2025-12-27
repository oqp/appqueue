from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import hashlib
import logging
from .config import settings

# ========================================
# CONFIGURACIÓN DE LOGGING
# ========================================
logger = logging.getLogger(__name__)

# ========================================
# CONFIGURACIÓN DE PASSWORDS
# ========================================

# Context para hashing de passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_password_hash(password: str) -> str:
    """
    Crea un hash seguro de una contraseña
    """
    try:
        hashed = pwd_context.hash(password)
        logger.debug("Password hash creado correctamente")
        return hashed
    except Exception as e:
        logger.error(f" Error creando hash de password: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña coincide con su hash
    """
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.debug(f"Verificación de password: {' válida' if is_valid else ' inválida'}")
        return is_valid
    except Exception as e:
        logger.error(f" Error verificando password: {e}")
        return False


def generate_password(length: int = 12) -> str:
    """
    Genera una contraseña aleatoria segura
    """
    try:
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        logger.debug(f"Password generada de {length} caracteres")
        return password
    except Exception as e:
        logger.error(f" Error generando password: {e}")
        raise


def check_password_strength(password: str) -> dict:
    """
    Verifica la fortaleza de una contraseña
    """
    checks = {
        "length": len(password) >= 8,
        "uppercase": any(c.isupper() for c in password),
        "lowercase": any(c.islower() for c in password),
        "digit": any(c.isdigit() for c in password),
        "special": any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    }

    score = sum(checks.values())
    strength = "débil" if score < 3 else "media" if score < 5 else "fuerte"

    return {
        "score": score,
        "max_score": 5,
        "strength": strength,
        "checks": checks,
        "is_strong": score >= 4
    }


# ========================================
# CONFIGURACIÓN DE JWT
# ========================================

def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token JWT de acceso
    """
    try:
        to_encode = data.copy()

        # Configurar tiempo de expiración
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        # Agregar claims estándar
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })

        # Crear token
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        logger.debug(f"Token de acceso creado para usuario: {data.get('sub', 'unknown')}")
        return encoded_jwt

    except Exception as e:
        logger.error(f" Error creando token de acceso: {e}")
        raise


def create_refresh_token(data: dict) -> str:
    """
    Crea un token JWT de refresh
    """
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })

        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        logger.debug(f"Token de refresh creado para usuario: {data.get('sub', 'unknown')}")
        return encoded_jwt

    except Exception as e:
        logger.error(f" Error creando token de refresh: {e}")
        raise


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """
    Verifica y decodifica un token JWT
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Verificar tipo de token
        if payload.get("type") != token_type:
            logger.warning(f"Tipo de token incorrecto: esperado {token_type}, recibido {payload.get('type')}")
            return None

        # Verificar expiración
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            logger.warning("Token expirado")
            return None

        logger.debug(f"Token {token_type} verificado correctamente")
        return payload

    except JWTError as e:
        logger.warning(f"Error JWT: {e}")
        return None
    except Exception as e:
        logger.error(f" Error verificando token: {e}")
        return None


def decode_token(token: str) -> Optional[dict]:
    """
    Decodifica un token sin verificar la firma (para inspección)
    """
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        return payload
    except Exception as e:
        logger.error(f" Error decodificando token: {e}")
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Obtiene la fecha de expiración de un token
    """
    try:
        payload = decode_token(token)
        if payload and "exp" in payload:
            return datetime.utcfromtimestamp(payload["exp"])
        return None
    except Exception as e:
        logger.error(f"Error obteniendo expiración de token: {e}")
        return None


def is_token_expired(token: str) -> bool:
    """
    Verifica si un token está expirado
    """
    try:
        expiry = get_token_expiry(token)
        if expiry:
            return expiry < datetime.utcnow()
        return True  # Si no se puede obtener la expiración, asumir expirado
    except Exception as e:
        logger.error(f"Error verificando expiración de token: {e}")
        return True


# ========================================
# UTILIDADES DE SEGURIDAD
# ========================================

def generate_secret_key(length: int = 32) -> str:
    """
    Genera una clave secreta segura
    """
    try:
        secret = secrets.token_urlsafe(length)
        logger.info(f"Clave secreta generada de {length} bytes")
        return secret
    except Exception as e:
        logger.error(f" Error generando clave secreta: {e}")
        raise


def create_api_key() -> str:
    """
    Crea una API key única
    """
    try:
        timestamp = str(int(datetime.utcnow().timestamp()))
        random_part = secrets.token_hex(16)
        api_key = f"qms_{timestamp}_{random_part}"
        logger.debug("API key creada")
        return api_key
    except Exception as e:
        logger.error(f" Error creando API key: {e}")
        raise


def hash_api_key(api_key: str) -> str:
    """
    Crea un hash de una API key para almacenamiento seguro
    """
    try:
        hashed = hashlib.sha256(api_key.encode()).hexdigest()
        return hashed
    except Exception as e:
        logger.error(f" Error hasheando API key: {e}")
        raise


def verify_api_key(api_key: str, hashed_api_key: str) -> bool:
    """
    Verifica una API key contra su hash
    """
    try:
        return hash_api_key(api_key) == hashed_api_key
    except Exception as e:
        logger.error(f" Error verificando API key: {e}")
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo para evitar path traversal
    """
    try:
        import re
        import os.path

        # Obtener solo el nombre del archivo (no path)
        filename = os.path.basename(filename)

        # Remover caracteres peligrosos
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)

        # Limitar longitud
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255 - len(ext)] + ext

        # Evitar nombres reservados en Windows
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                          'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                          'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']

        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            filename = f"file_{filename}"

        logger.debug(f"🧹 Nombre de archivo sanitizado: {filename}")
        return filename

    except Exception as e:
        logger.error(f" Error sanitizando filename: {e}")
        return "sanitized_file"


def generate_csrf_token() -> str:
    """
    Genera un token CSRF
    """
    try:
        token = secrets.token_urlsafe(32)
        logger.debug("🛡️ Token CSRF generado")
        return token
    except Exception as e:
        logger.error(f" Error generando token CSRF: {e}")
        raise


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Enmascara datos sensibles para logs
    """
    try:
        if not data or len(data) <= visible_chars:
            return "*" * len(data) if data else ""

        visible_part = data[:visible_chars]
        masked_part = "*" * (len(data) - visible_chars)
        return visible_part + masked_part

    except Exception as e:
        logger.error(f" Error enmascarando datos: {e}")
        return "***"


# ========================================
# VALIDADORES DE SEGURIDAD
# ========================================

def validate_email(email: str) -> bool:
    """
    Valida formato de email
    """
    try:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    except Exception as e:
        logger.error(f" Error validando email: {e}")
        return False


def validate_phone(phone: str) -> bool:
    """
    Valida formato de teléfono
    """
    try:
        import re
        # Permitir números con +, espacios, guiones y paréntesis
        pattern = r'^[\+]?[1-9][\d\s\-\(\)]{7,15}$'
        cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)
        return bool(re.match(pattern, cleaned_phone)) and len(cleaned_phone) >= 8
    except Exception as e:
        logger.error(f" Error validando teléfono: {e}")
        return False


def validate_document_number(document: str) -> bool:
    """
    Valida número de documento
    """
    try:
        import re
        # Permitir números, letras y algunos caracteres especiales
        pattern = r'^[A-Za-z0-9\-\.]{5,20}$'
        return bool(re.match(pattern, document))
    except Exception as e:
        logger.error(f" Error validando documento: {e}")
        return False


# ========================================
# INFORMACIÓN DEL SISTEMA DE SEGURIDAD
# ========================================

def get_security_info() -> dict:
    """
    Obtiene información sobre la configuración de seguridad
    """
    try:
        return {
            "algorithm": settings.ALGORITHM,
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
            "password_hash_schemes": pwd_context.schemes(),
            "secret_key_length": len(settings.SECRET_KEY),
            "secret_key_masked": mask_sensitive_data(settings.SECRET_KEY, 8)
        }
    except Exception as e:
        logger.error(f" Error obteniendo info de seguridad: {e}")
        return {"error": str(e)}


# ========================================
# INICIALIZACIÓN
# ========================================

def init_security():
    """
    Inicializa el sistema de seguridad
    """
    logger.info("Inicializando sistema de seguridad...")

    # Verificar configuración
    if len(settings.SECRET_KEY) < 32:
        logger.warning("La clave secreta es muy corta - recomendado mínimo 32 caracteres")

    if settings.is_development:
        logger.warning("Modo desarrollo - algunas validaciones de seguridad relajadas")

    # Verificar algoritmo
    if settings.ALGORITHM not in ["HS256", "HS384", "HS512"]:
        logger.warning(f"Algoritmo JWT no recomendado: {settings.ALGORITHM}")

    logger.info("Sistema de seguridad inicializado")


# Inicializar automáticamente
init_security()