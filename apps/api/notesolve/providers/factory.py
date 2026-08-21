from notesolve.config import Settings
from notesolve.domain.ports import WorksheetAnalyzer
from notesolve.providers.fake_analyzer import FakeWorksheetAnalyzer
from notesolve.providers.openai_analyzer import OpenAIWorksheetAnalyzer


def create_worksheet_analyzer(settings: Settings) -> WorksheetAnalyzer:
    if settings.ai_provider == "fake":
        return FakeWorksheetAnalyzer()
    if settings.ai_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("NOTESOLVE_OPENAI_API_KEY is required for the OpenAI provider")
        return OpenAIWorksheetAnalyzer(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        )
    raise ValueError(f"Unsupported AI provider: {settings.ai_provider}")
