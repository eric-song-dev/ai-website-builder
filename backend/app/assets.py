import asyncio
import hashlib
import html
from typing import Any


def _color(seed: str, offset: int) -> str:
    digest = hashlib.sha256(f"{seed}:{offset}".encode()).hexdigest()
    return f"#{digest[:6]}"


def _svg(body: str, width: int = 1200, height: int = 700) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img">{body}</svg>'
    )


async def stock_pipeline(prompt: str) -> dict[str, Any]:
    await asyncio.sleep(0.08)
    a, b = _color(prompt, 1), _color(prompt, 2)
    art = _svg(
        f'<defs><linearGradient id="g"><stop stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>'
        '<rect width="1200" height="700" rx="48" fill="url(#g)"/>'
        '<circle cx="930" cy="170" r="210" fill="white" opacity=".16"/>'
        '<path d="M0 560 C260 420 400 720 720 520 S1040 420 1200 510 V700 H0Z" fill="white" opacity=".22"/>'
    )
    return {"kind": "stock", "name": "hero.svg", "content": art}


async def illustration_pipeline(prompt: str) -> dict[str, Any]:
    await asyncio.sleep(0.08)
    label = html.escape(prompt[:34])
    art = _svg(
        '<rect x="80" y="80" width="1040" height="540" rx="40" fill="#0f172a"/>'
        '<rect x="145" y="150" width="410" height="54" rx="16" fill="#a78bfa"/>'
        '<rect x="145" y="235" width="690" height="24" rx="12" fill="#334155"/>'
        '<rect x="145" y="282" width="540" height="24" rx="12" fill="#334155"/>'
        f'<text x="145" y="405" fill="white" font-size="38" font-family="system-ui">{label}</text>'
    )
    return {"kind": "illustration", "name": "illustration.svg", "content": art}


async def diagram_pipeline(prompt: str) -> dict[str, Any]:
    await asyncio.sleep(0.08)
    art = _svg(
        '<g fill="none" stroke="#94a3b8" stroke-width="8"><path d="M250 350H520"/><path d="M680 350H950"/></g>'
        '<g fill="#f8fafc" stroke="#6366f1" stroke-width="7">'
        '<rect x="70" y="260" width="180" height="180" rx="36"/>'
        '<rect x="520" y="260" width="160" height="180" rx="36"/>'
        '<rect x="950" y="260" width="180" height="180" rx="36"/></g>'
        '<g fill="#0f172a" font-size="28" text-anchor="middle" font-family="system-ui">'
        '<text x="160" y="360">Idea</text><text x="600" y="360">AI</text><text x="1040" y="360">Site</text></g>'
    )
    return {"kind": "diagram", "name": "diagram.svg", "content": art}


async def branding_pipeline(prompt: str) -> dict[str, Any]:
    await asyncio.sleep(0.08)
    palette = [_color(prompt, index) for index in range(3, 7)]
    logo = _svg(
        f'<rect width="700" height="700" rx="180" fill="{palette[0]}"/>'
        f'<path d="M180 470 350 150l170 320-170 80Z" fill="{palette[1]}"/>',
        700,
        700,
    )
    return {"kind": "branding", "name": "logo.svg", "content": logo, "palette": palette}
