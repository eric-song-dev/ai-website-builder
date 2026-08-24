import asyncio
import time

from backend.app.assets import (
    branding_pipeline,
    diagram_pipeline,
    illustration_pipeline,
    stock_pipeline,
)
from backend.app.generator import generate_bundle, review_bundle, revise_bundle
from backend.app.models import CodeMode
from backend.app.schemas import SitePlan


async def assets():
    return await asyncio.gather(
        stock_pipeline("studio"),
        illustration_pipeline("studio"),
        diagram_pipeline("studio"),
        branding_pipeline("studio"),
    )


def plan():
    return SitePlan(
        title="Northstar Studio",
        audience="teams",
        pages=["index", "about", "contact"],
        sections=["hero", "proof"],
        tone="clear",
        palette=["#6d5dfc", "#20c997", "#0d1526", "#f7f7fb"],
    )


def test_all_three_code_modes_generate_reviewable_bundles():
    generated_assets = asyncio.run(assets())
    expected = {CodeMode.single_html: 1, CodeMode.multi_page: 5, CodeMode.react: 2}
    for mode, count in expected.items():
        bundle = generate_bundle(mode, "A website for a design studio", plan(), generated_assets)
        assert len(bundle.files) == count
        assert review_bundle(bundle, mode).approved


def test_parallel_assets_are_materially_faster_than_serial():
    async def serial():
        return [
            await fn("benchmark")
            for fn in (stock_pipeline, illustration_pipeline, diagram_pipeline, branding_pipeline)
        ]

    started = time.perf_counter()
    asyncio.run(serial())
    serial_time = time.perf_counter() - started
    started = time.perf_counter()
    asyncio.run(assets())
    parallel_time = time.perf_counter() - started
    assert parallel_time < serial_time * 0.6


def test_revision_creates_effective_patch():
    bundle = generate_bundle(
        CodeMode.single_html, "A website for a design studio", plan(), asyncio.run(assets())
    )
    revised = revise_bundle(
        bundle, CodeMode.single_html, "Use a darker visual theme", {"selector": "section.hero"}
    )
    assert revised.files[0].content != bundle.files[0].content
    assert "--paper:#0b1020" in revised.files[0].content
