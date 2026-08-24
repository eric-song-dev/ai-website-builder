import re

from langchain_openai import ChatOpenAI

from .config import Settings, get_settings
from .schemas import SitePlan


class ModelGateway:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.is_fake = self.settings.model_provider == "fake" or not self.settings.openai_api_key

    async def rewrite(self, prompt: str) -> list[str]:
        normalized = " ".join(re.findall(r"[\w-]+", prompt.lower()))[:240]
        if self.is_fake:
            return [
                normalized,
                f"responsive accessible {normalized}",
                f"conversion focused {normalized}",
            ]
        model = ChatOpenAI(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            temperature=0,
        )
        response = await model.ainvoke(
            "Rewrite this website request into exactly three short retrieval queries, one per line:\n"
            + prompt
        )
        return [line.strip(" -") for line in str(response.content).splitlines() if line.strip()][:3]

    async def plan(self, prompt: str, context: list[str]) -> SitePlan:
        if self.is_fake:
            words = [word.capitalize() for word in re.findall(r"[A-Za-z0-9]+", prompt)[:5]]
            title = " ".join(words) or "Launch Something Remarkable"
            return SitePlan(
                title=title,
                audience="people looking for a clear, credible solution",
                pages=["index", "about", "contact"],
                sections=["hero", "features", "process", "proof", "cta"],
                tone="confident, warm, editorial",
                palette=["#6d5dfc", "#20c997", "#0d1526", "#f7f7fb"],
            )
        model = ChatOpenAI(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            temperature=0.2,
        ).with_structured_output(SitePlan)
        return await model.ainvoke(
            f"Plan a production-quality website. Request: {prompt}\nRelevant guidance: {context}"
        )
