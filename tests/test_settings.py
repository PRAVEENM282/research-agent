from src.config.settings import Settings


def test_database_urls_are_converted_for_async_and_sync_drivers() -> None:
    config = Settings(database_url="postgresql://u:p@db:5432/agent_db")
    assert config.async_database_url == "postgresql+asyncpg://u:p@db:5432/agent_db"
    assert config.sync_database_url == "postgresql+psycopg://u:p@db:5432/agent_db"


def test_placeholder_api_key_selects_offline_writer() -> None:
    assert Settings(llm_api_key="sk-your-provider-key").uses_offline_writer
    assert Settings(llm_api_key="").uses_offline_writer
    assert not Settings(llm_api_key="real-key").uses_offline_writer
    assert not Settings(llm_provider="ollama", llm_api_key="").uses_offline_writer


def test_provider_and_workflow_engine_are_validated() -> None:
    config = Settings(llm_provider="anthropic", workflow_engine="celery_langgraph")
    assert config.llm_provider == "anthropic"
    assert config.workflow_engine == "celery_langgraph"
