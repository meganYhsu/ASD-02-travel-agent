"""Coordinate evidence-based reviews for the ASD-02 Travel Agent project.

Collectors gather project evidence, pipelines turn it into model requests, and
AIRunner obtains an assessment followed by a review of that assessment. MCP
reviews concern travel tools, RAG reviews concern answers about saved itineraries,
and the multi-agent branch concerns coordination of travel workflows.

This module returns review text; it does not apply the AI's recommendations to
project files. Available modes depend on the COLLECTORS registry below.
"""

from pathlib import Path

from collectors import mcp_collector, rag_collector
from config.review_config import ModeConfig, build_mode_config
from core.ai_runner import AIRunner
from core.prompts import PromptRegistry
from pipelines import mcp_pipeline, rag_pipeline
from collectors import architecture_collector, db_collector, devops_collector, endpoints_collector, mcp_collector, multi_agent_collector, rag_collector
from pipelines import architecture_pipeline, db_pipeline, devops_pipeline, endpoints_pipeline, mcp_pipeline, multi_agent_pipeline, rag_pipeline


COLLECTORS = {
    "mcp": mcp_collector.collect,
    "rag": rag_collector.collect,
    "db": db_collector.collect,
    "endpoints": endpoints_collector.collect,
    "architecture": architecture_collector.collect,
    "devops": devops_collector.collect,
    "multi_agent": multi_agent_collector.collect,
}


def _stage(label: str, stage: str, message: str) -> None:
    """Print the review mode, current step, and progress message."""
    print(f"[{label}][{stage}] {message}")


def run_mode(mode: ModeConfig, app_dir: Path, repo_root: Path, prompts: PromptRegistry, ai: AIRunner) -> str:
    """Collect evidence, request an AI assessment, and review it for one mode.

    mode selects the collector and prompt files. app_dir identifies the app
    under review; repo_root identifies the shared travel project. Both paths
    are passed to the collector. prompts supplies instructions, and ai makes
    the implementation and review model calls.

    MCP uses one review prompt. RAG adds a reasoning prompt to its review.
    Collection or implementation-model failure stops the flow early. A review
    model failure is included in the final report alongside the assessment.
    Successful reports contain OBSERVE, IMPLEMENTATION, and REVIEW sections;
    IMPLEMENTATION is an assessment, not an applied code change.
    """
    _stage(mode.label, "START", "Starting review flow")
    _stage(mode.label, "OBSERVE", "Collecting evidence")
    collector = COLLECTORS[mode.key]
    ok, evidence = collector(app_dir, repo_root)
    if not ok:
        _stage(mode.label, "OBSERVE", "Failed")
        return f"OBSERVE: {evidence}"
    _stage(mode.label, "OBSERVE", "Complete")

    if mode.key == "mcp":
        _stage(mode.label, "PROMPTS", f"Loading prompt family: {mode.prompt_family}")
        task_prompt = prompts.read(mode.prompt_family, mode.implementation_prompts[0])
        system_prompt = (
            "You are a precise MCP integration validator for ASD-02 Travel Agent. "
            "Assess the supplied evidence about travel tools for itinerary activities, "
            "daily schedules, start times, and travel requirements. "
            "Use only supplied evidence and reply in at most 40 words."
        )
        implementation_user_prompt = mcp_pipeline.build_implementation_prompt(task_prompt, evidence)
        _stage(mode.label, "PROMPTS", "Loaded MCP implementation prompt")
        _stage(mode.label, "LLM", "Running MCP implementation model")
        implementation_output, err = ai.call(system_prompt, implementation_user_prompt, review=False)
        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"
        _stage(mode.label, "LLM", "MCP implementation model complete")

        review_prompt_text = prompts.read(mode.prompt_family, mode.review_prompts[0])
        review_user_prompt = mcp_pipeline.build_review_prompt(implementation_output, evidence)
        _stage(mode.label, "PROMPTS", "Loaded MCP review prompt")
        _stage(mode.label, "LLM", "Running MCP review model")
        review_output, review_err = ai.call(review_prompt_text, review_user_prompt, review=True)
        if review_err:
            review_output = review_err
            _stage(mode.label, "LLM", "Review model failed")
        else:
            _stage(mode.label, "LLM", "Review model complete")

        _stage(mode.label, "DONE", "Review complete")
        return f"OBSERVE: {evidence}\n\nIMPLEMENTATION: {implementation_output}\nREVIEW: {review_output}"

    if mode.key == "rag":
        _stage(mode.label, "PROMPTS", f"Loading prompt family: {mode.prompt_family}")
        task_prompt = prompts.read(mode.prompt_family, mode.implementation_prompts[0])
        system_prompt = (
            "You are a precise RAG pipeline validator for ASD-02 Travel Agent. "
            "Assess the supplied evidence about retrieval and answers grounded in "
            "saved itinerary data. "
            "Use only supplied evidence and reply in at most 40 words."
        )
        implementation_user_prompt = rag_pipeline.build_implementation_prompt(task_prompt, evidence)
        _stage(mode.label, "PROMPTS", "Loaded RAG implementation prompt")
        _stage(mode.label, "LLM", "Running RAG implementation model")
        implementation_output, err = ai.call(system_prompt, implementation_user_prompt, review=False)
        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"
        _stage(mode.label, "LLM", "RAG implementation model complete")

        review_prompt_text = prompts.read(mode.prompt_family, mode.review_prompts[0])
        reasoning_prompt_text = prompts.read(mode.prompt_family, mode.review_prompts[1])
        review_system_prompt = f"{review_prompt_text}\n\n{reasoning_prompt_text}"
        review_user_prompt = rag_pipeline.build_review_prompt(implementation_output, evidence)
        _stage(mode.label, "PROMPTS", "Loaded RAG review and reasoning prompts")
        _stage(mode.label, "LLM", "Running RAG review model")
        review_output, review_err = ai.call(review_system_prompt, review_user_prompt, review=True)
        if review_err:
            review_output = review_err
            _stage(mode.label, "LLM", "Review model failed")
        else:
            _stage(mode.label, "LLM", "Review model complete")

        _stage(mode.label, "DONE", "Review complete")
        return f"OBSERVE: {evidence}\n\nIMPLEMENTATION: {implementation_output}\nREVIEW: {review_output}"
    if mode.key == "multi_agent":
        _stage(mode.label, "PROMPTS", f"Loading prompt family: {mode.prompt_family}")
        task_prompt = prompts.read(mode.prompt_family, mode.implementation_prompts[0])
        system_prompt = (
            "You are a precise multi-agent workflow validator for ASD-02 Travel Agent. "
            "Assess the supplied evidence about Planner, Worker, Reviewer, and "
            "Coordinator collaboration on travel features. "
            "Use only supplied evidence and reply in at most 40 words."
        )
        implementation_user_prompt = multi_agent_pipeline.build_implementation_prompt(task_prompt, evidence)
        _stage(mode.label, "PROMPTS", "Loaded multi-agent implementation prompt")

        _stage(mode.label, "LLM", "Running multi-agent implementation model")
        implementation_output, err = ai.call(system_prompt, implementation_user_prompt, review=False)
        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"
        _stage(mode.label, "LLM", "Multi-agent implementation model complete")

        review_prompt_text = prompts.read(mode.prompt_family, mode.review_prompts[0])
        review_user_prompt = multi_agent_pipeline.build_review_prompt(implementation_output, evidence)
        _stage(mode.label, "PROMPTS", "Loaded multi-agent review prompt")
        _stage(mode.label, "LLM", "Running multi-agent review model")
        review_output, review_err = ai.call(review_prompt_text, review_user_prompt, review=True)
        if review_err:
            review_output = review_err
            _stage(mode.label, "LLM", "Review model failed")
        else:
            _stage(mode.label, "LLM", "Review model complete")

        _stage(mode.label, "DONE", "Review complete")

        return (
            f"OBSERVE: {evidence}\n\n"
            f"IMPLEMENTATION: {implementation_output}\n"
            f"REVIEW: {review_output}"
        )



    return f"Unsupported mode: {mode.key}"

REVIEW_MENU = (
    ("1", "db", "DB", "Travel data storage and relationships"),
    ("2", "endpoints", "Endpoints", "Travel API requests and responses"),
    ("3", "architecture", "Architecture", "Frontend, backend, and shared travel services"),
    ("4", "devops", "DevOps", "Docker, CI, and service configuration"),
    ("5", "mcp", "MCP", "Itinerary tools and travel requirements"),
    ("6", "rag", "RAG", "Answers grounded in saved itineraries"),
    ("7", "multi_agent", "Multi-Agent", "Planner, Worker, Reviewer, and Coordinator"),
)


def _print_mode_mapping(app_dir: Path) -> None:
    """Show configured review prompt folders and any missing prompt files.

    app_dir is the review application's root containing its prompts directory.
    Folder names come from ModeConfig rather than lab numbers or service prompts
    used by other parts of the travel application.
    """
    modes = build_mode_config()
    print()
    print("ASD-02 Travel Agent - Review Prompt Mapping")
    for _, mode_key, label, _ in REVIEW_MENU:
        mode = modes.get(mode_key)
        if mode is None:
            print(f"{label}: not configured in build_mode_config()")
            continue

        prompt_dir = app_dir / "prompts" / mode.prompt_family
        print(f"{label}: {prompt_dir}")
        if not prompt_dir.is_dir():
            print("  Missing prompt directory")
            continue

        for prompt_name in mode.implementation_prompts + mode.review_prompts:
            if not (prompt_dir / prompt_name).is_file():
                print(f"  Missing prompt file: {prompt_name}")


def print_menu() -> None:
    """Display review choices; the caller handles input and runs the chosen mode."""
    modes = build_mode_config()
    print()
    print("=" * 70)
    print("ASD-02 TRAVEL AGENT - AGENTIC REVIEW MENU")
    for choice, mode_key, label, description in REVIEW_MENU:
        status = "" if mode_key in modes else " [not configured]"
        print(f"{choice} - {label}: {description}{status}")
    print("0 - Exit")
    print("=" * 70)
