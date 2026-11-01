"""Slide-ready charts for the anonymous technical context.

Server-side matplotlib rendering (same dependency as the wordcloud), so the
dashboard stays dependency-free and every chart can be downloaded as a PNG
for slides. All functions fail soft: a broken dataset never breaks the page.
"""

import base64
import io
from typing import Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

PALETTE = ["#4f46e5", "#06b6d4", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"]
TEXT = "#1f2937"
MUTED = "#6b7280"
GRID = "#e5e7eb"
SIZE = (8.0, 4.5)  # 16:9, 800x450 @100dpi


def _finish(fig) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=100, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _bar(labels, values, title, ylabel="", horizontal=False, color=None):
    if not labels or not any(v for v in values):
        return None
    fig, ax = plt.subplots(figsize=SIZE)
    if isinstance(color, (list, tuple)):
        colors = list(color)
    elif color:
        colors = [color] * len(labels)
    else:
        colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]

    if horizontal:
        bars = ax.barh(labels, values, color=colors, height=0.6)
        ax.invert_yaxis()
        ax.set_xlabel(ylabel, color=MUTED, fontsize=10)
        ax.bar_label(bars, padding=4, color=TEXT, fontsize=10)
    else:
        bars = ax.bar(labels, values, color=colors, width=0.55)
        ax.set_ylabel(ylabel, color=MUTED, fontsize=10)
        ax.bar_label(bars, padding=4, color=TEXT, fontsize=10)

    ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", loc="left", pad=14)
    ax.grid(axis="y" if not horizontal else "x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)
    fig.tight_layout()
    return _finish(fig)


def _donut(items, title):
    clean = [(str(item.get("label")), item.get("count", 0)) for item in (items or []) if item.get("count")]
    if not clean:
        return None
    labels = [c[0] for c in clean]
    values = [c[1] for c in clean]
    total = sum(values)

    fig, ax = plt.subplots(figsize=SIZE)
    wedges, _ = ax.pie(
        values,
        colors=[PALETTE[i % len(PALETTE)] for i in range(len(values))],
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2},
    )
    ax.text(0, 0.08, str(total), ha="center", va="center", fontsize=26, fontweight="bold", color=TEXT)
    ax.text(0, -0.2, "total", ha="center", va="center", fontsize=10, color=MUTED)
    ax.legend(
        wedges,
        [f"{label} — {value} ({value / total * 100:.0f}%)" for label, value in clean],
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        frameon=False,
        fontsize=10,
        labelcolor=TEXT,
    )
    ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", loc="left", pad=14)
    fig.tight_layout()
    return _finish(fig)


def _grouped_bars(labels, series, title, ylabel, colors=None, suffix="", bar_colors=None):
    """series: list of (name, values)"""
    if not labels or not series:
        return None
    fig, ax = plt.subplots(figsize=SIZE)
    width = 0.7 / max(1, len(series))
    positions = range(len(labels))
    colors = colors or PALETTE

    for index, (name, values) in enumerate(series):
        offsets = [p + (index - (len(series) - 1) / 2) * width for p in positions]
        bar_color = bar_colors if bar_colors else colors[index % len(colors)]
        bars = ax.bar(offsets, values, width=width, label=name, color=bar_color)
        ax.bar_label(
            bars,
            labels=[f"{v:.0f}{suffix}" if v is not None else "" for v in values],
            padding=3,
            fontsize=9,
            color=TEXT,
        )

    ax.set_xticks(list(positions))
    ax.set_xticklabels(labels, color=MUTED, fontsize=10)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=10)
    ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", loc="left", pad=14)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=9, labelcolor=TEXT, loc="upper right")
    fig.tight_layout()
    return _finish(fig)


def build_charts(insights: Optional[dict]) -> dict:
    """Return {key: {"title": ..., "image": data-uri}} for every available chart."""
    if not insights:
        return {}

    charts: dict[str, dict] = {}

    def add(key: str, title: str, image: Optional[str]):
        if image:
            charts[key] = {"title": title, "image": image}

    # Participation funnel
    add(
        "funnel",
        "Participation",
        _bar(
            ["Sessions", "Feedbacks", "Abandons"],
            [
                insights.get("joins") or 0,
                insights.get("submits") or 0,
                insights.get("abandons") or 0,
            ],
            "Participation des étudiants",
            "Nombre",
            color=["#4f46e5", "#22c55e", "#f59e0b"],
        ),
    )

    # Devices
    add("devices", "Appareils", _donut(insights.get("device_types"), "Répartition par appareil"))

    # Browsers
    add(
        "browsers",
        "Navigateurs",
        _bar(
            [item["label"] for item in (insights.get("browsers") or [])][:6],
            [item["count"] for item in (insights.get("browsers") or [])][:6],
            "Navigateurs utilisés",
            "Feedbacks",
            horizontal=True,
        ),
    )

    # Network generation
    add(
        "connection",
        "Connexion",
        _donut(insights.get("connection_types"), "Génération réseau estimée (max 4G)"),
    )

    # Network kind (wifi / cellular)
    add("network_kind", "Type de réseau", _donut(insights.get("network_types"), "Wifi / cellulaire"))

    # Timing (seconds)
    timing_labels = ["1re frappe", "Rédaction", "Total page"]
    timing_values = [
        insights.get("avg_first_input_seconds"),
        insights.get("avg_typing_seconds"),
        insights.get("avg_total_seconds"),
    ]
    if any(v is not None for v in timing_values):
        add(
            "timing",
            "Temps de réponse",
            _grouped_bars(
                timing_labels,
                [("secondes", [v or 0 for v in timing_values])],
                "Temps moyen des étudiants (secondes)",
                "Secondes",
                suffix=" s",
                bar_colors=["#4f46e5", "#06b6d4", "#22c55e"],
            ),
        )

    # Page performance (ms)
    perf_labels = ["TTFB", "1er affichage", "LCP"]
    perf_values = [
        insights.get("avg_ttfb_ms"),
        insights.get("avg_first_paint_ms"),
        insights.get("avg_lcp_ms"),
    ]
    if any(v is not None for v in perf_values):
        add(
            "performance",
            "Performance",
            _grouped_bars(
                perf_labels,
                [("millisecondes", [v or 0 for v in perf_values])],
                "Chargement de la page (ms)",
                "Millisecondes",
                suffix=" ms",
                bar_colors=["#06b6d4", "#8b5cf6", "#4f46e5"],
            ),
        )

    # Preferences
    prefs = []
    if insights.get("dark_share") is not None:
        prefs.append({"label": "mode sombre", "count": insights["dark_share"]})
    if insights.get("reduced_motion_share") is not None:
        prefs.append({"label": "mouvement réduit", "count": insights["reduced_motion_share"]})
    if any(p["count"] for p in prefs):
        add(
            "preferences",
            "Préférences",
            _bar(
                [p["label"] for p in prefs],
                [p["count"] for p in prefs],
                "Préférences d'affichage (% des sessions)",
                "%",
                horizontal=True,
                color="#f59e0b",
            ),
        )

    return charts
