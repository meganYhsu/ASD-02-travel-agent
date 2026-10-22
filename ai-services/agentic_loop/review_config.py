from dataclasses import dataclass

@dataclass(frozen=True)
class ModeConfig:
    key: str
    label: str
    prompt_family: str
    implementation_prompts: tuple[str, ...]
    review_prompts: tuple[str, ...] = ()


def build_mode_config() -> dict[str, ModeConfig]:
    return {
        "mcp": ModeConfig(
            key="mcp",
            label="MCP",
            prompt_family="mcp",
            implementation_prompts=("implementation/tool_selection_prompt.txt",),
            review_prompts=("review/integration_review_prompt.txt",),
        ),
        "multi_agent": ModeConfig(
            key="multi_agent",
            label="Multi-Agent",
            prompt_family="multi_agent_services",
            implementation_prompts=("implementation/multi_agent_implementation_prompt.txt",),
            review_prompts=("review/multi_agent_review_prompt.txt",),
        ),
    }


