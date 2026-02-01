"""
Ollama background worker with tool calling support.

Handles inference for text, vision, and web-search augmented requests
on a separate thread to maintain UI responsiveness.
"""

import time
import ollama
from PySide6.QtCore import QThread, Signal

from kratt.core.web_search import (
    improve_search_query,
    search_duckduckgo,
    filter_search_results,
    WebScraper
)
from kratt.core.tools import get_tool_definitions, execute_tool


class OllamaWorker(QThread):
    """
    Executes Ollama inference tasks with tool calling support.

    Signals:
        new_token (str): Emitted for every generated token.
        status_update (str): Emitted to report background activity.
        finished (float, int): Emitted on completion with (duration, token_count).
        stopped (): Emitted if processing is manually halted.
    """

    new_token = Signal(str)
    status_update = Signal(str)
    finished = Signal(float, int)
    stopped = Signal()

    def __init__(
            self,
            history: list[dict],
            model_name: str,
            vision_model_name: str,
            system_prompt: str,
            image_path: str | None = None,
            user_text: str = "",
            web_search_enabled: bool = False,
    ) -> None:
        super().__init__()
        self.history = history
        self.model_name = model_name
        self.vision_model_name = vision_model_name
        self.system_prompt = system_prompt
        self.image_path = image_path
        self.user_text = user_text
        self.web_search_enabled = web_search_enabled
        self.token_count = 0
        self._stop_requested = False

    def request_stop(self) -> None:
        """Flags the worker to stop at the next available opportunity."""
        self._stop_requested = True

    def run(self) -> None:
        """Main execution logic."""
        start_time = time.time()
        try:
            if self.image_path:
                self._run_vision(start_time)
            elif self.web_search_enabled and self.user_text.strip():
                self._run_web_search(start_time)
            else:
                self._run_normal(start_time)
        except Exception as e:
            self.new_token.emit(f"Error: {str(e)}")
            self.finished.emit(0, 0)

    def _run_web_search(self, start_time: float) -> None:
        """Orchestrates query optimization, search, scraping, and RAG inference."""
        self.status_update.emit("*Optimizing search query...*")
        search_query = improve_search_query(self.user_text, self.model_name)

        if self._stop_requested:
            self.stopped.emit()
            return

        self.status_update.emit(f"*Searching...*")
        raw_results = search_duckduckgo(search_query, num_results=10)

        if not raw_results:
            self._run_normal(start_time)
            return

        self.status_update.emit("*Filtering results...*")
        filtered = filter_search_results(self.user_text, raw_results, self.model_name)
        if not filtered:
            filtered = raw_results[:3]

        urls = [r['url'] for r in filtered[:3]]

        if self._stop_requested:
            self.stopped.emit()
            return

        self.status_update.emit(f"*Reading {len(urls)} pages...*")
        scraper = WebScraper(max_pages_per_site=1, headless=True)
        scraped_data = scraper.scrape_urls(urls)

        context_text = ""
        for url, text in scraped_data.items():
            context_text += f"SOURCE: {url}\nCONTENT:\n{text[:4000]}\n\n"

        if not context_text:
            context_text = "No readable content found from search results."

        self.status_update.emit("")

        system_msg = (
            f"{self.system_prompt}\n\n"
            f"CONTEXT FROM WEB SEARCH:\n{context_text}\n\n"
            f"INSTRUCTION: Answer the user's question based on the context above. "
            f"Be direct and accurate. Do not cite sources unless asked."
        )

        messages = [{"role": "system", "content": system_msg}]
        for msg in self.history:
            if msg["role"] != "system":
                messages.append(msg)

        try:
            stream = ollama.chat(model=self.model_name, messages=messages, stream=True)
            self._consume_stream(stream, start_time)
        except Exception as e:
            self.new_token.emit(f"Model error: {e}")
            self.finished.emit(0, 0)

    def _run_normal(self, start_time: float) -> None:
        """Standard text chat inference with tool calling support."""
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in self.history:
            if msg["role"] != "system":
                messages.append(msg)

        tools = get_tool_definitions()

        try:
            self._run_with_tools(messages, tools, start_time)
        except Exception as e:
            self.new_token.emit(f"Model error: {e}")
            self.finished.emit(0, 0)

    def _run_with_tools(self, messages: list[dict], tools: list[dict], start_time: float, max_iterations: int = 5) -> None:
        """
        Agentic loop that handles tool calling.

        Continues until the model produces a final response (no tool calls).
        """
        iteration = 0
        while iteration < max_iterations and not self._stop_requested:
            iteration += 1

            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                tools=tools,
                stream=False
            )

            messages.append(response["message"])

            if response["message"].get("tool_calls"):
                for tool_call in response["message"]["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args = tool_call["function"]["arguments"]

                    self.status_update.emit(f"*Calling {tool_name}...*")

                    try:
                        result = execute_tool(tool_name, **tool_args)
                    except Exception as e:
                        result = f"Tool error: {str(e)}"

                    messages.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": result
                    })
            else:
                self.status_update.emit("")

                content = response["message"].get("content", "")
                self._emit_content_as_tokens(content, start_time)
                return

        if iteration >= max_iterations:
            self.new_token.emit("(Max tool iterations reached)")
            self._emit_completion(start_time)

    def _emit_content_as_tokens(self, content: str, start_time: float) -> None:
        """Emit text content as individual tokens for consistency with streaming."""
        for char in content:
            self.new_token.emit(char)
            self.token_count += 1

        self._emit_completion(start_time)

    def _emit_completion(self, start_time: float) -> None:
        """Emit the finished signal."""
        duration = time.time() - start_time
        self.finished.emit(duration, self.token_count)

    def _run_vision(self, start_time: float) -> None:
        """Vision model inference on attached image."""
        prompt = self.user_text if self.user_text.strip() else "Describe this image."
        try:
            stream = ollama.chat(
                model=self.vision_model_name,
                messages=[{"role": "user", "content": prompt, "images": [self.image_path]}],
                stream=True,
            )
            self._consume_stream(stream, start_time)
        except Exception as e:
            self.new_token.emit(f"Vision error: {e}")
            self.finished.emit(0, 0)

    def _consume_stream(self, stream, start_time: float) -> None:
        """Iterates over the Ollama stream and emits tokens."""
        for chunk in stream:
            if self._stop_requested:
                self.stopped.emit()
                return
            content = chunk["message"]["content"]
            self.token_count += 1
            self.new_token.emit(content)

        duration = time.time() - start_time
        self.finished.emit(duration, self.token_count)