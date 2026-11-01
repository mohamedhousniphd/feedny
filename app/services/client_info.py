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
        "network_type": _clean_str(payload.get("networkType"), 20),
        "pointer_type": _clean_str(payload.get("pointerType"), 20),
        "hover_capable": _clean_bool(payload.get("hoverCapable")),
        "dpr": _clean_number(payload.get("dpr")),
        "orientation": _clean_str(payload.get("orientation"), 20),
        "prefers_dark": _clean_bool(payload.get("prefersDark")),
        "reduced_motion": _clean_bool(payload.get("reducedMotion")),
        "high_contrast": _clean_bool(payload.get("highContrast")),
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
        # Page performance + abandonment
        "ttfb_ms": _clean_number(payload.get("ttfbMs")),
        "dom_ready_ms": _clean_number(payload.get("domReadyMs")),
        "load_ms": _clean_number(payload.get("loadMs")),
        "first_paint_ms": _clean_number(payload.get("firstPaintMs")),
        "lcp_ms": _clean_number(payload.get("lcpMs")),
        "page_seconds": _clean_number(payload.get("pageSeconds")),
        "left_without_submit": _clean_bool(payload.get("leftWithoutSubmit")),
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
        clean = [item for item in (items or []) if (item.get("label") or "").lower() not in {"inconnu", "unknown"}]
        return ", ".join(f"{item['label']} ({item['count']})" for item in clean[:limit])

    devices = insights.get("device_types") or []
    browsers = insights.get("browsers") or []
    systems = insights.get("os") or []
    connections = insights.get("connection_types") or []
    networks = insights.get("network_types") or []
    countries = insights.get("countries") or []

    total_submits = insights.get("submits") or 0
    lines: list[str] = []
    if insights.get("joins") is not None:
        lines.append(
            f"Participation : {total_submits} feedback(s) envoyé(s) sur {insights.get('joins')} session(s) ouverte(s) "
            f"({insights.get('conversion_rate', 0)} % de conversion)."
        )
    for label, items in (
        ("Appareils", devices),
        ("Navigateurs", browsers),
        ("Systèmes", systems),
    ):
        summary_value = top(items)
        if summary_value:
            lines.append(f"{label} : {summary_value}.")

    networks_value = top(networks)
    if networks_value:
        lines.append(f"Réseau : {networks_value} (wifi / cellulaire, tel que déclaré par l'appareil).")
    connections_value = top(connections)
    if connections_value:
        lines.append(f"Génération réseau estimée : {connections_value} (le navigateur plafonne à 4G).")
        if insights.get("avg_rtt_ms"):
            lines.append(f"Latence réseau moyenne : {insights['avg_rtt_ms']:.0f} ms.")
        if insights.get("avg_downlink_mbps"):
            lines.append(f"Débit descendant moyen : {insights['avg_downlink_mbps']:.1f} Mbps.")
        if insights.get("fast_network_share") is not None:
            lines.append(
                "Part de connexions très rapides (>= 10 Mbps et < 80 ms) : "
                f"{insights['fast_network_share']} %."
            )
        if insights.get("slow_network_share") is not None:
            lines.append(f"Part de connexions lentes (2G/3G) : {insights['slow_network_share']} %.")
    countries_value = top(countries, 5)
    if countries_value:
        lines.append(f"Pays (CDN, non nominatif) : {countries_value}.")
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
    if insights.get("avg_load_ms"):
        lines.append(
            "Chargement moyen de la page : "
            f"{insights['avg_load_ms'] / 1000:.1f} s (TTFB {insights.get('avg_ttfb_ms') or 0:.0f} ms"
            + (f", LCP {insights['avg_lcp_ms'] / 1000:.1f} s" if insights.get("avg_lcp_ms") else "")
            + ")."
        )
    if insights.get("abandons"):
        abandon = f"Abandons sans envoi : {insights['abandons']}"
        if insights.get("avg_abandon_seconds"):
            abandon += f" (après {_format_duration(insights['avg_abandon_seconds'])} en moyenne)"
        lines.append(abandon + ".")
    if insights.get("dark_share") is not None:
        lines.append(
            f"Préférences : mode sombre {insights['dark_share']} %, "
            f"mouvement réduit {insights.get('reduced_motion_share') or 0} %."
        )
    if insights.get("avg_emotion") is not None:
        lines.append(
            f"Humeur moyenne : {insights['avg_emotion']:.1f}/10 "
            f"sur {insights.get('emotion_responses') or 0} réponse(s)."
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
        "avg_downlink_mbps": insights.get("avg_downlink_mbps"),
        "fast_network_share": insights.get("fast_network_share"),
        "slow_network_share": insights.get("slow_network_share"),
        "paste_rate": insights.get("paste_rate"),
        "keystrokes": insights.get("avg_keystrokes"),
        "avg_load_ms": insights.get("avg_load_ms"),
        "avg_ttfb_ms": insights.get("avg_ttfb_ms"),
        "avg_lcp_ms": insights.get("avg_lcp_ms"),
        "abandons": insights.get("abandons"),
        "avg_abandon_seconds": insights.get("avg_abandon_seconds"),
        "dark_share": insights.get("dark_share"),
        "reduced_motion_share": insights.get("reduced_motion_share"),
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
