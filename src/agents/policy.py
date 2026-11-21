from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_PROMPT_LENGTH = 4000
MAX_DRAFT_LENGTH = 12000
ALLOWED_TOOLS = frozenset({"web_search", "fetch_page"})
PROVIDER_TIMEOUT_SECONDS = 18
MAX_PROVIDER_ATTEMPTS = 3


class DraftOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=5, max_length=180)
    summary: str = Field(min_length=60, max_length=MAX_DRAFT_LENGTH)


def validate_draft(text: str) -> str:
    if len(text) > MAX_DRAFT_LENGTH:
        raise ValueError("Draft exceeded the configured output limit.")
    value = text.strip()
    if not value:
        raise ValueError("Draft was empty.")
    return value


def validate_tool_name(name: str) -> None:
    if name not in ALLOWED_TOOLS:
        raise PermissionError("The requested agent tool is not allowed.")


def validate_prompt(prompt: str) -> str:
    cleaned = prompt.strip()
    if not cleaned or len(cleaned) > MAX_PROMPT_LENGTH:
        raise ValueError("Prompt must contain 1 to 4000 characters.")
    return cleaned


__all__ = [
    "DraftOutput",
    "ValidationError",
    "validate_draft",
    "validate_prompt",
    "validate_tool_name",
]
