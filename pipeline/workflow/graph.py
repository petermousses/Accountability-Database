"""LangGraph workflow definition for the accountability pipeline.

Defines the state machine that orchestrates document processing,
normalization, analysis, and export.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, StateGraph

from workflow.nodes import (
    analyze_node,
    error_handler_node,
    export_node,
    intake_node,
    normalize_node,
    process_documents_node,
    report_node,
)
from workflow.state import PipelineState


def should_continue_after_intake(state: Dict[str, Any]) -> str:
    """Route after intake: proceed or error."""
    errors = state.get("errors", [])
    intake_errors = [e for e in errors if e.get("stage") == "intake"]
    if intake_errors:
        return "error_handler"
    return "process_documents"


def should_continue_after_processing(state: Dict[str, Any]) -> str:
    """Route after processing: wait for Ollama or proceed to normalize."""
    if state.get("requires_human_input"):
        return "wait_for_ollama"
    return "normalize"


def should_continue_after_analysis(state: Dict[str, Any]) -> str:
    """Route after analysis: export or handle errors."""
    errors = state.get("errors", [])
    critical_errors = [e for e in errors if "failed" in e.get("message", "").lower()]
    if len(critical_errors) > 3:
        return "error_handler"
    return "export"


def build_pipeline_graph() -> StateGraph:
    """Build and return the compiled LangGraph pipeline.

    Graph structure:
        intake → process_documents → (wait_for_ollama | normalize)
        normalize → analyze → export → report → END
        Any node → error_handler → END

    Returns:
        Compiled StateGraph ready for execution.
    """
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("intake", intake_node)
    graph.add_node("process_documents", process_documents_node)
    graph.add_node("normalize", normalize_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("export", export_node)
    graph.add_node("report", report_node)
    graph.add_node("error_handler", error_handler_node)

    # Set entry point
    graph.set_entry_point("intake")

    # Conditional edge: intake → process_documents or error
    graph.add_conditional_edges(
        "intake",
        should_continue_after_intake,
        {
            "process_documents": "process_documents",
            "error_handler": "error_handler",
        },
    )

    # Conditional edge: process_documents → wait or normalize
    graph.add_conditional_edges(
        "process_documents",
        should_continue_after_processing,
        {
            "wait_for_ollama": END,  # Pause for human input; resume at normalize
            "normalize": "normalize",
        },
    )

    # Linear edges: normalize → analyze → export → report → END
    graph.add_edge("normalize", "analyze")

    graph.add_conditional_edges(
        "analyze",
        should_continue_after_analysis,
        {
            "export": "export",
            "error_handler": "error_handler",
        },
    )

    graph.add_edge("export", "report")
    graph.add_edge("report", END)
    graph.add_edge("error_handler", END)

    return graph


def compile_pipeline():
    """Compile the pipeline graph for execution.

    Returns:
        Compiled graph that can be invoked with initial state.
    """
    graph = build_pipeline_graph()
    return graph.compile()


def run_pipeline(initial_state: Dict[str, Any]) -> Dict[str, Any]:
    """Run the pipeline with initial state.

    Args:
        initial_state: Dictionary with at minimum 'documents' key.

    Returns:
        Final pipeline state after execution.
    """
    app = compile_pipeline()
    result = app.invoke(initial_state)
    return result


def resume_pipeline_after_ollama(
    state: Dict[str, Any],
    ollama_responses: list,
) -> Dict[str, Any]:
    """Resume pipeline after Ollama responses are provided.

    When the pipeline pauses at wait_for_ollama, the orchestrator
    fulfills the requests and calls this to continue processing.

    Args:
        state: Pipeline state from the paused run.
        ollama_responses: List of OllamaResponse dicts.

    Returns:
        Final pipeline state after completion.
    """
    state["ollama_responses"] = ollama_responses
    state["requires_human_input"] = False

    # Build a mini-graph for the remaining stages
    resume_graph = StateGraph(PipelineState)
    resume_graph.add_node("normalize", normalize_node)
    resume_graph.add_node("analyze", analyze_node)
    resume_graph.add_node("export", export_node)
    resume_graph.add_node("report", report_node)
    resume_graph.add_node("error_handler", error_handler_node)

    resume_graph.set_entry_point("normalize")
    resume_graph.add_edge("normalize", "analyze")
    resume_graph.add_conditional_edges(
        "analyze",
        should_continue_after_analysis,
        {
            "export": "export",
            "error_handler": "error_handler",
        },
    )
    resume_graph.add_edge("export", "report")
    resume_graph.add_edge("report", END)
    resume_graph.add_edge("error_handler", END)

    app = resume_graph.compile()
    return app.invoke(state)
