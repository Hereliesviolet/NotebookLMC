"""Model router - mirrored from apps/api/app/langdock/model_router.py (architecture doc §30)."""


class ModelRouter:
    def select_model(self, task: str, risk: str = "normal") -> str:
        sonnet_tasks = {
            "final_answer",
            "complex_summary",
            "source_comparison",
            "contradiction_check",
            "legal_reasoning",
            "technical_reasoning",
            "briefing",
        }

        haiku_tasks = {
            "intent_detection",
            "query_rewrite",
            "title_generation",
            "followup_questions",
            "simple_summary",
            "classification",
            "reranking",
        }

        embedding_tasks = {
            "document_embedding",
            "query_embedding",
        }

        if task in embedding_tasks:
            return "langdock_embedding"

        if task in sonnet_tasks:
            return "sonnet"

        if task in haiku_tasks:
            return "haiku"

        if risk == "high":
            return "sonnet"

        return "haiku"
