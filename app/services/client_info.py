"""Passive, anonymous technical context collection.

Goal: understand *how* students reach the form (device, browser, network,
country) without collecting personal data. No IP address, no precise
location, no identifiers beyond the existing random device cookie.

The browser sends what `navigator` already exposes (no permission prompt is
required for any of these fields), and we derive the rest from the
User-Agent header and Cloudflare's country hint.
"""

import re
from typing import Any, Optional

_UA_MAX = 400

_BROWSER_PATTERNS = [
    ("Samsung Internet", r"SamsungBrowser/([\d.]+)"),
    ("Edge", r"Edg(?:iOS|A)?/([\d.]+)"),
    ("Opera", r"(?:OPR|Opera)/([\d.]+)"),
    ("Firefox", r"(?:Firefox|FxiOS)/([\d.]+)"),
    ("Chrome", r"(?:Chrome|CriOS|Chromium)/([\d.]+)"),
    ("Safari", r"Version/([\d.]+).*Safari"),
]

_OS_PATTERNS = [
    ("Android", r"Android\s?([\d.]+)?"),
    ("iOS", r"(?:iPhone|iPad|iPod).*?OS\s([\d_]+)"),
    ("Windows", r"Windows NT\s?([\d.]+)?"),
    ("macOS", r"Mac OS X\s?([\d_.]+)?"),
    ("Linux", r"(Linux)"),
    ("ChromeOS", r"CrOS"),
]


def parse_user_agent(user_agent: str) -> tuple[str, str, str]:
    """Return (device_type, browser, os) inferred from the User-Agent."""
    ua = user_agent or ""
    device_type = "desktop"
    if re.search(r"iPad|Tablet|PlayBook|Silk", ua, re.I):
        device_type = "tablet"
    elif re.search(r"Mobi|iPhone|iPod|Android.*Mobile|Windows Phone", ua, re.I):
        device_type = "mobile"

    browser = "Autre"
    for name, pattern in _BROWSER_PATTERNS:
        match = re.search(pattern, ua, re.I)
        if match:
            browser = name
            break

    os_name = "Autre"
    for name, pattern in _OS_PATTERNS:
        if re.search(pattern, ua, re.I):
            os_name = name
            break

    return device_type, browser, os_name


def _clean_str(value: Any, max_length: int) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_length]


def _clean_number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return round(number, 2)


def _clean_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return None


def _clean_int(value: Any, maximum: int = 100000) -> Optional[int]:
    number = _clean_number(value)
    if number is None or number < 0:
        return None
    return int(min(number, maximum))


def collect_client_context(
    payload: Optional[dict],
    user_agent: str = "",
    country_hint: Optional[str] = None,
    referrer: Optional[str] = None,
    fill_seconds: Optional[float] = None,
) -> dict:
    """Normalise the browser payload into a storable, anonymous record."""
    payload = payload if isinstance(payload, dict) else {}

    # Prefer what the page reports (same value as the header for real browsers)
    ua = _clean_str(payload.get("userAgent") or user_agent, _UA_MAX) or ""
    device_type, browser, os_name = parse_user_agent(ua)

    screen = payload.get("screen")
    viewport = payload.get("viewport")
    if isinstance(screen, (list, tuple)) and len(screen) == 2:
        screen = f"{screen[0]}x{screen[1]}"
    if isinstance(viewport, (list, tuple)) and len(viewport) == 2:
        viewport = f"{viewport[0]}x{viewport[1]}"

    return {
        "device_type": _clean_str(payload.get("deviceType"), 20) or device_type,
        "browser": _clean_str(payload.get("browser"), 40) or browser,
        "os": _clean_str(payload.get("os"), 30) or os_name,
        "user_agent": ua or None,
        "platform": _clean_str(payload.get("platform"), 40),
        "language": _clean_str(payload.get("language"), 20),
        "timezone": _clean_str(payload.get("timezone"), 60),
        "screen": _clean_str(screen, 20),
        "viewport": _clean_str(viewport, 20),
        "connection_type": _clean_str(payload.get("connectionType"), 20),
        "downlink": _clean_number(payload.get("downlink")),
        "rtt": _clean_number(payload.get("rtt")),
        "save_data": _clean_bool(payload.get("saveData")),
        "touch": _clean_bool(payload.get("touch")),
        "memory_gb": _clean_number(payload.get("memory")),
        "cores": _clean_number(payload.get("cores")),
        "country": _clean_str(country_hint, 8),
        "referrer": _clean_str(referrer, 300),
        # Timing signals (seconds / counters), all anonymous
        "fill_seconds": _clean_number(payload.get("fillSeconds", fill_seconds)),
        "first_input_seconds": _clean_number(payload.get("firstInputSeconds")),
        "typing_seconds": _clean_number(payload.get("typingSeconds")),
        "total_seconds": _clean_number(payload.get("totalSeconds")),
        "keystrokes": _clean_int(payload.get("keystrokes")),
        "backspaces": _clean_int(payload.get("backspaces")),
        "pasted": _clean_bool(payload.get("pasted")),
        "paste_chars": _clean_int(payload.get("pasteChars")),
        "idle_seconds": _clean_number(payload.get("idleSeconds")),
    }


def _format_duration(seconds: Optional[float]) -> Optional[str]:
    if seconds is None:
        return None
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.0f} s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} min"
    return f"{minutes / 60:.1f} h"


def summarize_technical(insights: Optional[dict]) -> dict:
    """Build a readable technical summary (prompt + report + dashboard)."""
    if not insights:
        return {"lines": [], "devices": [], "connections": [], "timing": {}, "countries": []}

    def top(items, limit=3):
        return ", ".join(f"{item['label']} ({item['count']})" for item in (items or [])[:limit])

    devices = insights.get("device_types") or []
    browsers = insights.get("browsers") or []
    systems = insights.get("os") or []
    connections = insights.get("connection_types") or []
    countries = insights.get("countries") or []

    total_submits = insights.get("submits") or 0
    lines: list[str] = []
    if insights.get("joins") is not None:
        lines.append(
            f"Participation : {total_submits} feedback(s) envoyé(s) sur {insights.get('joins')} session(s) ouverte(s) "
            f"({insights.get('conversion_rate', 0)} % de conversion)."
        )
    if devices:
        lines.append(f"Appareils : {top(devices)}.")
    if browsers:
        lines.append(f"Navigateurs : {top(browsers)}." )
    if systems:
        lines.append(f"Systèmes : {top(systems)}.")
    if connections:
        lines.append(f"Connexions : {top(connections)}.")
        if insights.get("avg_rtt_ms"):
            lines.append(f"Latence réseau moyenne : {insights['avg_rtt_ms']:.0f} ms.")
        if insights.get("slow_network_share") is not None:
            lines.append(f"Part de connexions lentes (2G/3G) : {insights['slow_network_share']} %.")
    if countries:
        lines.append(f"Pays (CDN, non nominatif) : {top(countries, 5)}.")
    if insights.get("avg_first_input_seconds") is not None:
        lines.append(
            "Temps avant la première frappe : "
            f"{_format_duration(insights['avg_first_input_seconds'])}."
        )
    if insights.get("avg_typing_seconds") is not None:
        lines.append(
            "Temps de rédaction moyen (1re frappe → envoi) : "
            f"{_format_duration(insights['avg_typing_seconds'])}."
        )
    if insights.get("avg_total_seconds") is not None:
        lines.append(
            "Temps total moyen sur la page : "
            f"{_format_duration(insights['avg_total_seconds'])}."
        )
    if insights.get("avg_idle_seconds") is not None:
        lines.append(f"Pause d'inactivité la plus longue (moyenne) : {_format_duration(insights['avg_idle_seconds'])}.")
    if insights.get("avg_keystrokes"):
        lines.append(
            f"Frappes moyennes : {insights['avg_keystrokes']:.0f} "
            f"(retours arrière : {insights.get('avg_backspaces') or 0:.0f})."
        )
    if insights.get("paste_rate") is not None:
        lines.append(f"Feedbacks collés (copier-coller) : {insights['paste_rate']} %.")

    timing = {
        "conversion_rate": insights.get("conversion_rate"),
        "avg_first_input": _format_duration(insights.get("avg_first_input_seconds")),
        "avg_typing": _format_duration(insights.get("avg_typing_seconds")),
        "avg_total": _format_duration(insights.get("avg_total_seconds")),
        "avg_idle": _format_duration(insights.get("avg_idle_seconds")),
        "avg_rtt_ms": insights.get("avg_rtt_ms"),
        "slow_network_share": insights.get("slow_network_share"),
        "paste_rate": insights.get("paste_rate"),
        "keystrokes": insights.get("avg_keystrokes"),
    }

    return {
        "lines": lines,
        "devices": devices,
        "connections": connections,
        "countries": countries,
        "timing": timing,
    }


def request_country(request) -> Optional[str]:
    for header in ("cf-ipcountry", "x-vercel-ip-country", "x-country-code"):
        value = request.headers.get(header)
        if value and value.upper() not in {"XX", "T1"}:
            return value.upper()
    return None
