from models import ContextMessage


class PromptBuilder:
    def build_system_prompt(
        self,
        base_prompt: str,
        *,
        context_summary: str,
        rag_context: str | None = None,
        route_label: str | None = None,
    ) -> str:
        sections = [base_prompt]

        if context_summary:
            sections.append(f"Recent context summary:\n{context_summary}")

        if rag_context:
            sections.append(rag_context)
            sections.append(self._build_rag_boundary(route_label))

        sections.append(
            "Follow the response-language instruction exactly. Treat Chinese "
            "knowledge-base text as internal reference material and never copy "
            "untranslated Chinese into the final reply."
        )

        return "\n\n".join(section for section in sections if section.strip())

    def build_reasoning_hint(self, context_messages: list[ContextMessage]) -> str | None:
        if not context_messages:
            return "fresh-session"

        roles = ",".join(message.role for message in context_messages[-4:])
        return f"context-roles:{roles}"

    def _build_rag_boundary(self, route_label: str | None) -> str:
        base_rules = [
            "Response boundaries:",
            "You are an emotional support companion, not a doctor or emergency service.",
            "Use the knowledge base for supportive and educational guidance, but do not diagnose, prescribe, or advise changing medication.",
            "If the knowledge base lacks relevant evidence, offer general support without inventing clinical claims or sources.",
        ]
        if route_label == "risk_escalation":
            base_rules.extend(
                [
                    "The current route indicates elevated risk. Keep the reply brief and calm, and check the user's immediate safety first.",
                    "Encourage the user to contact a trusted person, family member, professional, local emergency service, or crisis support service immediately.",
                    "Do not offer only reassurance or imply that you can replace in-person help.",
                ]
            )
        else:
            base_rules.append("Begin with empathy, then offer one or two manageable next steps.")
        return "\n".join(base_rules)


prompt_builder = PromptBuilder()
