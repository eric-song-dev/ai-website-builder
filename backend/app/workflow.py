import operator
from collections.abc import Awaitable, Callable
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from .assets import branding_pipeline, diagram_pipeline, illustration_pipeline, stock_pipeline
from .generator import generate_bundle, repair_bundle, review_bundle
from .llm import ModelGateway
from .models import CodeMode
from .rag import KnowledgeBase
from .schemas import GeneratedBundle, ReviewResult, SitePlan

Emitter = Callable[[str, dict], Awaitable[None]]


class WorkflowState(TypedDict, total=False):
    prompt: str
    mode: CodeMode
    queries: list[str]
    context: list[str]
    plan: SitePlan
    assets: Annotated[list[dict], operator.add]
    bundle: GeneratedBundle
    review: ReviewResult
    rounds: int


def build_workflow(kb: KnowledgeBase, gateway: ModelGateway, emit: Emitter):
    async def rewrite(state: WorkflowState):
        await emit("agent.started", {"agent": "QueryRewriter"})
        queries = await gateway.rewrite(state["prompt"])
        await emit("agent.completed", {"agent": "QueryRewriter", "queries": queries})
        return {"queries": queries}

    async def retrieve(state: WorkflowState):
        await emit("agent.started", {"agent": "Retriever"})
        context = kb.retrieve(state["queries"])
        await emit("agent.completed", {"agent": "Retriever", "chunks": len(context)})
        return {"context": context}

    async def planner(state: WorkflowState):
        await emit("agent.started", {"agent": "Planner"})
        plan = await gateway.plan(state["prompt"], state["context"])
        await emit("agent.completed", {"agent": "Planner", "pages": plan.pages})
        return {"plan": plan}

    def asset_node(name: str, pipeline):
        async def run(state: WorkflowState):
            asset = await pipeline(state["prompt"])
            await emit("asset.completed", {"pipeline": name, "name": asset["name"]})
            return {"assets": [asset]}

        return run

    async def generator(state: WorkflowState):
        await emit("agent.started", {"agent": "Generator"})
        bundle = generate_bundle(state["mode"], state["prompt"], state["plan"], state["assets"])
        await emit("artifact.patch", {"files": [file.path for file in bundle.files]})
        await emit("agent.completed", {"agent": "Generator", "file_count": len(bundle.files)})
        return {"bundle": bundle, "rounds": 0}

    async def reviewer(state: WorkflowState):
        await emit("agent.started", {"agent": "Reviewer", "round": state.get("rounds", 0)})
        review = review_bundle(state["bundle"], state["mode"])
        await emit("agent.completed", {"agent": "Reviewer", **review.model_dump()})
        return {"review": review}

    async def repair(state: WorkflowState):
        bundle = repair_bundle(state["bundle"], state["review"].issues)
        return {"bundle": bundle, "rounds": state.get("rounds", 0) + 1}

    def review_route(state: WorkflowState):
        return "persist" if state["review"].approved or state.get("rounds", 0) >= 2 else "repair"

    async def persist(state: WorkflowState):
        return {}

    graph = StateGraph(WorkflowState)
    graph.add_node("rewrite", rewrite)
    graph.add_node("retrieve", retrieve)
    graph.add_node("planner", planner)
    graph.add_node("stock", asset_node("stock", stock_pipeline))
    graph.add_node("illustration", asset_node("illustration", illustration_pipeline))
    graph.add_node("diagram", asset_node("diagram", diagram_pipeline))
    graph.add_node("branding", asset_node("branding", branding_pipeline))
    graph.add_node("generator", generator)
    graph.add_node("reviewer", reviewer)
    graph.add_node("repair", repair)
    graph.add_node("persist", persist)
    graph.add_edge(START, "rewrite")
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("retrieve", "planner")
    for target in ("stock", "illustration", "diagram", "branding"):
        graph.add_edge("planner", target)
    graph.add_edge(["stock", "illustration", "diagram", "branding"], "generator")
    graph.add_edge("generator", "reviewer")
    graph.add_conditional_edges(
        "reviewer", review_route, {"repair": "repair", "persist": "persist"}
    )
    graph.add_edge("repair", "reviewer")
    graph.add_edge("persist", END)
    return graph.compile()
