from __future__ import annotations

import html
import struct
import zlib
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _model_svg(model: dict[str, Any], result: dict[str, Any]) -> str:
    nodes = model["nodes"]
    positions = model.get("canvas", {}).get("positions", {})
    fallback = {node["id"]: {"x": 80 + index * 210, "y": 140} for index, node in enumerate(nodes)}
    points = {node["id"]: positions.get(node["id"], fallback[node["id"]]) for node in nodes}
    estimates = {effect["id"]: effect.get("estimate") for effect in result.get("effects", [])}
    shapes: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="520" viewBox="0 0 1000 520">',
        '<rect width="1000" height="520" fill="#f7f5ef"/>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#314c46"/></marker></defs>',
    ]
    for edge in model["edges"]:
        start, end = points[edge["from"]], points[edge["to"]]
        x1, y1 = start["x"] + 75, start["y"] + 35
        x2, y2 = end["x"] + 75, end["y"] + 35
        value = estimates.get(edge["id"])
        label = edge.get("label", edge["id"])
        if value is not None:
            label += f" = {value:.3f}"
        shapes.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#314c46" stroke-width="3" marker-end="url(#arrow)"/>'
        )
        shapes.append(
            f'<text x="{(x1 + x2) / 2:.0f}" y="{(y1 + y2) / 2 - 10:.0f}" font-family="sans-serif" font-size="16" text-anchor="middle">{html.escape(label)}</text>'
        )
    for node in nodes:
        point = points[node["id"]]
        shapes.append(
            f'<rect x="{point["x"]}" y="{point["y"]}" width="150" height="70" rx="12" fill="#ffffff" stroke="#9b5d35" stroke-width="3"/>'
        )
        shapes.append(
            f'<text x="{point["x"] + 75}" y="{point["y"] + 42}" font-family="sans-serif" font-size="20" text-anchor="middle">{html.escape(node["label"])}</text>'
        )
    shapes.append("</svg>")
    return "".join(shapes)


def _simple_png(path: Path, model: dict[str, Any], width: int = 1000, height: int = 520) -> None:
    pixels = bytearray((247, 245, 239) * (width * height))

    def paint(x: int, y: int, color: tuple[int, int, int], radius: int = 1) -> None:
        for py in range(max(0, y - radius), min(height, y + radius + 1)):
            for px in range(max(0, x - radius), min(width, x + radius + 1)):
                offset = (py * width + px) * 3
                pixels[offset : offset + 3] = bytes(color)

    def line(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for step in range(steps + 1):
            paint(
                round(x1 + (x2 - x1) * step / steps), round(y1 + (y2 - y1) * step / steps), color, 2
            )

    nodes = model["nodes"]
    positions = model.get("canvas", {}).get("positions", {})
    fallback = {node["id"]: {"x": 80 + index * 210, "y": 140} for index, node in enumerate(nodes)}
    points = {node["id"]: positions.get(node["id"], fallback[node["id"]]) for node in nodes}
    for edge in model["edges"]:
        start, end = points[edge["from"]], points[edge["to"]]
        line(
            int(start["x"] + 75),
            int(start["y"] + 35),
            int(end["x"] + 75),
            int(end["y"] + 35),
            (49, 76, 70),
        )
    for node in nodes:
        point = points[node["id"]]
        left, top = int(point["x"]), int(point["y"])
        for x in range(left, left + 151):
            paint(x, top, (155, 93, 53), 2)
            paint(x, top + 70, (155, 93, 53), 2)
        for y in range(top, top + 71):
            paint(left, y, (155, 93, 53), 2)
            paint(left + 150, y, (155, 93, 53), 2)
    rows = [b"\x00" + bytes(pixels[y * width * 3 : (y + 1) * width * 3]) for y in range(height)]
    raw = b"".join(rows)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def _slope_coordinates(
    plot: dict[str, Any], width: int, height: int
) -> tuple[list[dict[str, Any]], Callable[[float], float], Callable[[float], float]]:
    left, right, top, bottom = 70, 30, 35, 60
    lines = plot.get("lines", [])
    x_values = [value for line in lines for value in line["xValues"]]
    y_values = [
        value
        for line in lines
        for key in ("predictedValues", "confidenceLower", "confidenceUpper")
        for value in line.get(key, [])
    ]
    x_min, x_max = (min(x_values), max(x_values)) if x_values else (0.0, 1.0)
    y_min, y_max = (min(y_values), max(y_values)) if y_values else (0.0, 1.0)
    if x_max == x_min:
        x_max = x_min + 1
    if y_max == y_min:
        y_max = y_min + 1
    y_pad = (y_max - y_min) * 0.08
    y_min -= y_pad
    y_max += y_pad

    def x_map(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * (width - left - right)

    def y_map(value: float) -> float:
        return height - bottom - (value - y_min) / (y_max - y_min) * (height - top - bottom)

    return lines, x_map, y_map


def _simple_slope_svg(plot: dict[str, Any], width: int = 800, height: int = 500) -> str:
    lines, x_map, y_map = _slope_coordinates(plot, width, height)
    colors = ("#dc2626", "#475569", "#2563eb", "#7c3aed")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        '<line x1="70" y1="440" x2="770" y2="440" stroke="#64748b" stroke-width="2"/>',
        '<line x1="70" y1="35" x2="70" y2="440" stroke="#64748b" stroke-width="2"/>',
        f'<text x="400" y="486" text-anchor="middle" font-family="sans-serif" font-size="16">{html.escape(plot["predictorLabel"])}</text>',
        f'<text x="18" y="240" text-anchor="middle" transform="rotate(-90 18 240)" font-family="sans-serif" font-size="16">{html.escape(plot["outcomeLabel"])}</text>',
    ]
    for index, line in enumerate(lines):
        color = colors[index % len(colors)]
        x1, x2 = (x_map(value) for value in line["xValues"])
        y1, y2 = (y_map(value) for value in line["predictedValues"])
        lower = line.get("confidenceLower")
        upper = line.get("confidenceUpper")
        if lower and upper:
            polygon = " ".join(
                f"{x:.2f},{y:.2f}"
                for x, y in (
                    (x1, y_map(lower[0])),
                    (x2, y_map(lower[1])),
                    (x2, y_map(upper[1])),
                    (x1, y_map(upper[0])),
                )
            )
            parts.append(f'<polygon points="{polygon}" fill="{color}" opacity="0.12"/>')
        parts.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="4"/>'
        )
        parts.append(
            f'<text x="{x2 - 4:.2f}" y="{y2 - 10:.2f}" text-anchor="end" font-family="sans-serif" font-size="13" fill="{color}">{html.escape(line["label"])} (W={line["moderatorValue"]:.3f})</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _simple_slope_png(
    path: Path, plot: dict[str, Any], width: int = 800, height: int = 500
) -> None:
    pixels = bytearray((255, 255, 255) * (width * height))

    def paint(x: int, y: int, color: tuple[int, int, int], radius: int = 1) -> None:
        for py in range(max(0, y - radius), min(height, y + radius + 1)):
            for px in range(max(0, x - radius), min(width, x + radius + 1)):
                offset = (py * width + px) * 3
                pixels[offset : offset + 3] = bytes(color)

    def line(
        x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int], radius: int = 2
    ) -> None:
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for step in range(steps + 1):
            paint(
                round(x1 + (x2 - x1) * step / steps),
                round(y1 + (y2 - y1) * step / steps),
                color,
                radius,
            )

    lines, x_map, y_map = _slope_coordinates(plot, width, height)
    line(70, 440, 770, 440, (100, 116, 139), 1)
    line(70, 35, 70, 440, (100, 116, 139), 1)
    colors = ((220, 38, 38), (71, 85, 105), (37, 99, 235), (124, 58, 237))
    for index, item in enumerate(lines):
        line(
            round(x_map(item["xValues"][0])),
            round(y_map(item["predictedValues"][0])),
            round(x_map(item["xValues"][1])),
            round(y_map(item["predictedValues"][1])),
            colors[index % len(colors)],
            2,
        )
    rows = [b"\x00" + bytes(pixels[y * width * 3 : (y + 1) * width * 3]) for y in range(height)]
    raw = b"".join(rows)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
