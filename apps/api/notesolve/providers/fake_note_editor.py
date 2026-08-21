from notesolve.domain.models import NoteEditProposal


class FakeVaultNoteEditor:
    provider_name = "fake"
    model_name = "fake-note-editor-v1"
    prompt_version = "note-edit-v1"

    async def edit(self, *, current_content: str, instruction: str) -> NoteEditProposal:
        updated = f"{current_content.rstrip()}\n\n## 사용자 수정 요청\n\n{instruction.strip()}\n"
        return NoteEditProposal(
            content=updated,
            summary=f"요청 반영: {instruction.strip()[:100]}",
        )
