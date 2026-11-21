from fastapi import APIRouter, Depends

from src.api.dependencies import require_user
from src.api.schemas import RuntimeSettingsResponse
from src.config.settings import settings
from src.db.models import User

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/settings", response_model=RuntimeSettingsResponse)
async def get_runtime_settings(_: User = Depends(require_user)) -> RuntimeSettingsResponse:
    if settings.llm_provider == "ollama":
        llm_configured = bool(settings.llm_model)
    else:
        key = settings.xai_api_key if settings.llm_provider == "xai" else settings.llm_api_key
        llm_configured = bool(key and not settings.uses_offline_writer)
    return RuntimeSettingsResponse(
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        llm_configured=llm_configured,
        search_provider="searxng",
        search_configured=bool(settings.searxng_url),
    )
