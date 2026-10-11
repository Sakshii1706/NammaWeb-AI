"""
NammaWeb Reach - LLM Generator

Encapsulates local LLM generation.

Current implementation:
    Ollama + Llama 3.2 3B

The rest of the RAG pipeline should interact with this
class instead of directly creating ChatOllama instances.
"""

from __future__ import annotations

import time

from langchain_ollama import ChatOllama


class LLMGenerator:
    """
    Local LLM generation service.

    The model is initialized lazily on first generation request.
    """

    def __init__(
        self,
        model: str = "llama3.2:3b",
        temperature: float = 0.0,
        num_predict: int = 192,
        keep_alive: str = "24h",
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.num_predict = num_predict
        self.keep_alive = keep_alive

        self._llm: ChatOllama | None = None

    @property
    def llm(self) -> ChatOllama:
        """
        Return the underlying ChatOllama instance.

        The model client is created lazily.
        """

        if self._llm is None:
            start = time.perf_counter()

            self._llm = ChatOllama(
                model=self.model,
                temperature=self.temperature,
                num_predict=self.num_predict,
                keep_alive=self.keep_alive,
            )

            elapsed = time.perf_counter() - start

            print(
                f"[PERFORMANCE] LLM initialization: "
                f"{elapsed:.3f}s"
            )

        return self._llm

    def generate(self, prompt: str) -> str:
        """
        Generate an answer from a complete prompt.
        """

        if not prompt or not prompt.strip():
            raise ValueError(
                "Prompt cannot be empty."
            )

        start = time.perf_counter()

        response = self.llm.invoke(prompt)

        elapsed = time.perf_counter() - start

        print(
            f"[PERFORMANCE] Llama generation: "
            f"{elapsed:.3f}s"
        )

        content = response.content

        if content is None:
            return ""

        return str(content).strip()

    def get_model_name(self) -> str:
        """
        Return the configured model name.
        """

        return self.model
