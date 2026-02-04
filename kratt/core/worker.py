"""
Ollama background worker with LangChain integration.

Manages inference tasks asynchronously via QThread, supporting:
- Standard chat with tool use
- Vision model inference
- RAG-powered web search and synthesis
"""

import time
import ollama
from PySide6.QtCore import QThread, Signal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from kratt.lc.agent import build_agent
from kratt.lc.rag import RAGManager
from kratt.core.web_search import (
    improve_search_query,
    search_duckduckgo,
    filter_search_results,
    WebScraper
)


class OllamaWorker(QThread):
    """
    Executes LLM inference tasks in a background thread.

    Emits signals for streaming tokens, status updates, and completion.
    Supports cancellation via request_stop().
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
        """
        Initialize the worker thread.

        Args:
            history: Chat history as list of {"role": ..., "content": ...} dicts.
            model_name: Name of the main text model (Ollama).
            vision_model_name: Name of the vision model (Ollama).
            system_prompt: System instructions for the LLM.
            image_path: Optional path to an image for vision processing.
            user_text: The user's current message.
            web_search_enabled: Whether to perform web search and RAG.
        """
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
        """Signal the worker to stop generation gracefully."""
        self._stop_requested = True

    def run(self) -> None:
        """
        Main execution method (called by QThread.start()).

        Routes to appropriate handler based on input type:
        - Vision model if image is attached.
        - RAG search if web search is enabled.
        - Standard agent for regular chat.
        """
        start_time = time.time()
        try:
            if self.image_path:
                self._run_vision_legacy(start_time)
            elif self.web_search_enabled and self.user_text.strip():
                self._run_rag_search(start_time)
            else:
                self._run_agent(start_time)
        except Exception as e:
            self.new_token.emit(f"\n\n**System Error:** {str(e)}")
            self.finished.emit(0, 0)

    def _history_to_messages(self, include_system: bool = False):
        """
        Convert chat history to LangChain message objects.

        Args:
            include_system: Whether to prepend the system prompt.

        Returns:
            List of LangChain message objects (SystemMessage, HumanMessage, AIMessage).
        """
        msgs = []
        if include_system:
            msgs.append(SystemMessage(content=self.system_prompt))

        for h in self.history:
            if h["role"] == "user":
                msgs.append(HumanMessage(content=h["content"]))
            elif h["role"] == "assistant":
                msgs.append(AIMessage(content=h["content"]))
        return msgs

    def _run_agent(self, start_time: float) -> None:
        """
        Execute the LangChain agent with tool use.

        Streams token-by-token output and emits status updates during tool execution.

        Args:
            start_time: Timestamp when generation began.
        """
        agent = build_agent(self.model_name, self.system_prompt)

        # Prepare inputs: History + New User Message
        messages = self._history_to_messages(include_system=False)
        messages.append(HumanMessage(content=self.user_text))

        try:
            for chunk in agent.stream({"messages": messages}, stream_mode="messages"):
                if self._stop_requested:
                    self.stopped.emit()
                    return

                msg_chunk, metadata = chunk

                if isinstance(msg_chunk, AIMessage) and msg_chunk.content:
                    if hasattr(msg_chunk, 'tool_calls') and msg_chunk.tool_calls:
                        tool_name = msg_chunk.tool_calls[0]['name']
                        self.status_update.emit(f"*Executing {tool_name}...*")
                    else:
                        self.status_update.emit("")
                        self.new_token.emit(msg_chunk.content)
                        self.token_count += 1

                if chunk[0].type == "tool":
                    self.status_update.emit("*Thinking...*")

            self._emit_completion(start_time)

        except Exception as e:
            self.new_token.emit(f"Agent Error: {e}")
            self.finished.emit(0, 0)

    def _run_rag_search(self, start_time: float) -> None:
        """
        Execute RAG pipeline: search → scrape → vector store → generation.

        Performs web search, extracts content, embeds it, retrieves relevant context,
        and generates a response grounded in the retrieved documents.

        Args:
            start_time: Timestamp when generation began.
        """
        rag = RAGManager()

        self.status_update.emit("*Optimizing query...*")
        search_query = improve_search_query(self.user_text, self.model_name)

        if self._stop_requested:
            self.stopped.emit()
            return

        self.status_update.emit(f"*Searching...*")
        raw_results = search_duckduckgo(search_query, num_results=10)

        if not raw_results:
            self.new_token.emit("No search results found.")
            self._run_agent(start_time)
            return

        filtered = filter_search_results(self.user_text, raw_results, self.model_name)
        urls = [r['url'] for r in (filtered if filtered else raw_results)[:3]]

        if self._stop_requested:
            self.stopped.emit()
            return

        self.status_update.emit("*Reading content...*")
        scraper = WebScraper(max_pages_per_site=1, headless=True)
        scraped_data = scraper.scrape_urls(urls)

        self.status_update.emit("*Analyzing content...*")
        if scraped_data:
            success = rag.ingest_text(scraped_data)
            context = rag.retrieve(self.user_text) if success else ""
        else:
            context = ""

        if not context:
            context = "No readable content could be extracted from the search results."

        self.status_update.emit("*Generating response...*")

        rag_prompt = (
            f"{self.system_prompt}\n\n"
            f"CONTEXT FROM WEB SEARCH:\n{context}\n\n"
            f"INSTRUCTION: Answer based on the context above. "
            f"Do not provide citations or URLs."
        )

        # Direct ChatOllama usage for the final RAG answer generation
        from langchain_ollama import ChatOllama
        chat = ChatOllama(model=self.model_name, temperature=0.1)

        messages = self._history_to_messages(include_system=False)
        messages = [SystemMessage(content=rag_prompt)] + messages
        messages.append(HumanMessage(content=self.user_text))

        try:
            for chunk in chat.stream(messages):
                if self._stop_requested:
                    self.stopped.emit()
                    return
                self.new_token.emit(chunk.content)
                self.token_count += 1

            self._emit_completion(start_time)
        except Exception as e:
            self.new_token.emit(f"RAG Generation Error: {e}")
            self.finished.emit(0, 0)

    def _run_vision_legacy(self, start_time: float) -> None:
        """
        Execute vision model inference on an attached image.

        Uses direct Ollama library call (legacy approach) to process images
        and stream the model's response.

        Args:
            start_time: Timestamp when inference began.
        """
        prompt = self.user_text if self.user_text.strip() else "Describe this image."
        try:
            stream = ollama.chat(
                model=self.vision_model_name,
                messages=[{"role": "user", "content": prompt, "images": [self.image_path]}],
                stream=True,
            )
            for chunk in stream:
                if self._stop_requested:
                    self.stopped.emit()
                    return
                content = chunk["message"]["content"]
                self.token_count += 1
                self.new_token.emit(content)

            self._emit_completion(start_time)
        except Exception as e:
            self.new_token.emit(f"Vision error: {e}")
            self.finished.emit(0, 0)

    def _emit_completion(self, start_time: float) -> None:
        """
        Emit the finished signal with duration and token count.

        Args:
            start_time: Timestamp when generation began.
        """
        duration = time.time() - start_time
        self.finished.emit(duration, self.token_count)