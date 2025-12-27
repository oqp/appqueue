# archivo: dni_peru.py
import json
import re
import requests
from typing import Dict, Optional
from datetime import datetime

URL = "https://dniperu.com/querySelector"

LABEL_VARIANTS = {
    "DNI": [r"N[uú]mero\s+de\s+DNI", r"N[uú]mero\s+DNI", r"Nro\.?\s*DNI", r"DNI", r"Num\.?\s*DNI"],
    "Nombres": [r"Nombres?", r"Nombre\(s\)", r"Nombre"],
    "ApellidoPaterno": [r"Apellido\s+Paterno", r"Ap\.?\s*Paterno", r"Apellid[oó]Paterno", r"Ap\s*Pater\.?"],
    "ApellidoMaterno": [r"Apellido\s+Materno", r"Ap\.?\s*Materno", r"Apellid[oó]Materno", r"Ap\s*Mater\.?"],
    "CodigoVerificacion": [r"C[oó]digo\s+(?:de\s+)?Verificaci[oó]n", r"Cod\.?\s*Verificaci[oó]n", r"C[oó]d\s*Verif\.?"],
}
ALL_LABELS_ALT = "|".join(f"(?:{v})" for vs in LABEL_VARIANTS.values() for v in vs)

def build_label_pattern(label_key: str) -> re.Pattern:
    variants_alt = "|".join(f"(?:{v})" for v in LABEL_VARIANTS[label_key])
    pat = rf"(?P<label>{variants_alt})\s*[:：]\s*(?P<value>.*?)(?=\s*(?:{ALL_LABELS_ALT})\s*[:：]|$)"
    return re.compile(pat, flags=re.IGNORECASE | re.DOTALL)

PATTERNS = {k: build_label_pattern(k) for k in LABEL_VARIANTS.keys()}

def clean_digits(s: Optional[str]) -> Optional[str]:
    if s is None: return None
    m = re.findall(r"\d+", s)
    return "".join(m) if m else None

def tidy_text(s: Optional[str]) -> Optional[str]:
    if s is None: return None
    s = re.sub(r"[ \t]+", " ", s.strip())
    s = re.sub(r"\s*(?:\r?\n|;)\s*", " ", s).strip()
    return s

# Mapeo de patrones de error a códigos de error
ERROR_PATTERNS = {
    r"\bel\s+dni\s+debe\s+ser\s+un\s+n[uú]mero\s+de\s*8\s+d[ií]gitos\b": "INVALID_DNI_LENGTH",
    r"\bdni\s+inv[aá]lido\b": "INVALID_DNI",
    r"\bno\s+existe\b": "DNI_NOT_FOUND",
    r"\bno\s+encontrado\b": "DNI_NOT_FOUND",
    r"\bno\s+se\s+encontr[oó]\b": "DNI_NOT_FOUND",
    r"\bformato\b": "INVALID_FORMAT",
    r"\berror\b": "GENERIC_ERROR",
}

def detect_error_code(msg: str) -> Optional[str]:
    for pattern, code in ERROR_PATTERNS.items():
        if re.search(pattern, msg, flags=re.IGNORECASE):
            return code
    return None

def parse_mensaje_api(mensaje: str, dni: str) -> Dict:
    data = {
        "DNI": None,
        "Nombres": None,
        "ApellidoPaterno": None,
        "ApellidoMaterno": None,
        "CodigoVerificacion": None,
    }

    found_any = False
    for key, pat in PATTERNS.items():
        m = pat.search(mensaje)
        if m:
            val = tidy_text(m.group("value"))
            if key in ("DNI", "CodigoVerificacion"):
                val = clean_digits(val)
            data[key] = val
            found_any = True

    if not found_any:
        msg_norm = mensaje.strip()
        code = detect_error_code(msg_norm) or "UNKNOWN_ERROR"
        return {
            "status": "error",
            "data": None,
            "error": {
                "message": msg_norm or "Respuesta vacía del servidor",
                "code": code
            },
            "meta": {
                "dni_consultado": dni,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

    return {
        "status": "success",
        "data": data,
        "meta": {
            "dni_consultado": dni,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }

def consultar_dni(dni: str, timeout: int = 15) -> Dict:
    """
    Consulta el DNI en el servicio y devuelve un diccionario en formato estándar:
    {
        "status": "success" | "error",
        "data": {...} | None,
        "error": {...} | None,
        "meta": {...}
    }
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://dniperu.com/",
        "Origin": "https://dniperu.com",
    }
    with requests.Session() as s:
        s.headers.update(headers)
        files = {"dni4": (None, dni)}
        r = s.post(URL, files=files, timeout=timeout)
        r.raise_for_status()
        payload = r.json()

    mensaje = payload.get("mensaje", "")
    return parse_mensaje_api(mensaje, dni)

# Permite usarlo como script independiente para pruebas
if __name__ == "__main__":
    # Ejemplo válido
    print(json.dumps(consultar_dni("29636795"), ensure_ascii=False, indent=2))
    # Ejemplo inválido
    print(json.dumps(consultar_dni("123"), ensure_ascii=False, indent=2))
