import asyncio
import time

from backend.app.llm import ModelGateway
from backend.app.models import CodeMode
from backend.app.rag import KnowledgeBase
from backend.app.workflow import build_workflow


def test_langgraph_workflow_fans_out_and_joins():
    events = []

    async def emit(name, data):
        events.append((name, data, time.perf_counter()))

    graph = build_workflow(KnowledgeBase(), ModelGateway(), emit)
    result = asyncio.run(
        graph.ainvoke(
            {
                "prompt": "A polished launch site for a robotics studio",
                "mode": CodeMode.single_html,
                "assets": [],
                "rounds": 0,
            }
        )
    )
    assert result["review"].approved
    assert len(result["assets"]) == 4
    pipelines = {data["pipeline"] for name, data, _ in events if name == "asset.completed"}
    assert pipelines == {"stock", "illustration", "diagram", "branding"}
    assert any(name == "artifact.patch" for name, _, _ in events)
