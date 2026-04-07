from models import ContextMessage


class PromptBuilder:
    def build_system_prompt(self, base_prompt: str, *, context_summary: str) -> str:
        if not context_summary:
            return base_prompt

        return f"{base_prompt}\n\nRecent context summary:\n{context_summary}"

    def build_reasoning_hint(self, context_messages: list[ContextMessage]) -> str | None:
        if not context_messages:
            return "fresh-session"

        roles = ",".join(message.role for message in context_messages[-4:])
        return f"context-roles:{roles}"


prompt_builder = PromptBuilder()
