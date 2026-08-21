from notesolve.config import Settings
from notesolve.domain.ports import VaultNoteEditor, WorksheetAnalyzer, WorksheetVerifier
from notesolve.providers.fake_analyzer import FakeWorksheetAnalyzer, FakeWorksheetVerifier
from notesolve.providers.fake_note_editor import FakeVaultNoteEditor
from notesolve.providers.openai_analyzer import OpenAIWorksheetAnalyzer
from notesolve.providers.openai_note_editor import OpenAIVaultNoteEditor
from notesolve.providers.openai_verifier import OpenAIWorksheetVerifier


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


def create_worksheet_verifier(settings: Settings) -> WorksheetVerifier | None:
    if not settings.verification_enabled:
        return None
    if settings.ai_provider == "fake":
        return FakeWorksheetVerifier()
    if settings.ai_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("NOTESOLVE_OPENAI_API_KEY is required for the OpenAI provider")
        return OpenAIWorksheetVerifier(
            api_key=settings.openai_api_key,
            model=settings.openai_verification_model or settings.openai_model,
            base_url=settings.openai_base_url,
        )
    raise ValueError(f"Unsupported AI provider: {settings.ai_provider}")


def create_vault_note_editor(settings: Settings) -> VaultNoteEditor:
    if settings.ai_provider == "fake":
        return FakeVaultNoteEditor()
    if settings.ai_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("NOTESOLVE_OPENAI_API_KEY is required for the OpenAI provider")
        return OpenAIVaultNoteEditor(
            api_key=settings.openai_api_key,
            model=settings.openai_note_editor_model or settings.openai_model,
            base_url=settings.openai_base_url,
        )
    raise ValueError(f"Unsupported AI provider: {settings.ai_provider}")
