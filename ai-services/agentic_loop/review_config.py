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
    }
