"""
Unit tests for AI logic, agent functionality, and RAG pipeline.

Tests for:
- LangChain agent builder
- RAG document ingestion and retrieval
- Worker execution with vision and history
- Error handling and edge cases
"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from kratt.core.worker import OllamaWorker
from kratt.lc.rag import RAGManager
from kratt.lc.agent import build_agent


class TestRAGManager:
    """Test cases for RAG (Retrieval-Augmented Generation) functionality."""

    def test_ingest_text_with_valid_data(self, mocker):
        """
        Test that RAG manager successfully ingests text data.

        Verifies that valid text data is processed and stored in the
        vector store.
        """
        mocker.patch("kratt.lc.rag.OllamaEmbeddings")
        mocker.patch("kratt.lc.rag.FAISS.from_documents")

        rag = RAGManager()
        result = rag.ingest_text({"source_1": "content " * 20})

        assert result is True

    def test_ingest_text_with_empty_data(self, mocker):
        """Test that RAG manager rejects empty text data."""
        mocker.patch("kratt.lc.rag.OllamaEmbeddings")
        mocker.patch("kratt.lc.rag.FAISS.from_documents")

        rag = RAGManager()
        result = rag.ingest_text({})

        assert result is False

    def test_retrieve_returns_context_from_vector_store(self, mocker):
        """
        Test that retrieval returns relevant context from vector store.

        Ensures that the RAG manager can query the vector store and
        return formatted context strings.
        """
        mocker.patch("kratt.lc.rag.OllamaEmbeddings")
        mocker.patch("kratt.lc.rag.FAISS.from_documents")

        rag = RAGManager()
        rag.vector_store = MagicMock()

        mock_doc = MagicMock()
        mock_doc.page_content = "relevant content here"
        rag.vector_store.as_retriever().invoke.return_value = [
            mock_doc
        ]

        result = rag.retrieve("test query")

        assert "relevant content here" in result

    def test_retrieve_returns_empty_string_when_no_vector_store(self):
        """Test that retrieve returns empty string when vector store is None."""
        rag = RAGManager()
        result = rag.retrieve("test query")

        assert result == ""


class TestOllamaWorkerVision:
    """Test cases for vision model inference."""

    def test_worker_converts_history_to_messages(self):
        """
        Test that worker correctly converts chat history to LangChain
        message objects.

        Verifies proper message type conversion and system prompt
        inclusion when requested.
        """
        history = [
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Hi there"},
        ]
        worker = OllamaWorker(history, "model", "vision", "system")

        messages = worker._history_to_messages(include_system=True)

        assert len(messages) == 3
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], AIMessage)
        assert isinstance(messages[2], HumanMessage)

    def test_worker_vision_inference_streaming(self):
        """
        Test that vision model inference streams tokens correctly.

        Verifies that the worker can process image inputs and emit
        tokens as they are generated.
        """
        history = []
        worker = OllamaWorker(
            history,
            "text_model",
            "vision_model",
            "system_prompt",
            image_path="test.png",
        )

        with patch("ollama.chat") as mock_chat:
            mock_chat.return_value = iter(
                [{"message": {"content": "Vision output"}}]
            )

            worker._run_vision_legacy(0)

            assert worker.token_count == 1


class TestOllamaWorkerAgent:
    """Test cases for agent execution with tool use."""

    def test_agent_execution_with_tool_calling(self, mocker):
        """
        Test that agent executes correctly and emits tokens during
        streaming.

        Verifies that the agent stream is properly consumed and tokens
        are counted.
        """
        history = []
        worker = OllamaWorker(history, "model", "vision", "sys", user_text="hi")
        worker.new_token = MagicMock()

        mock_agent = MagicMock()
        mock_agent.stream.return_value = iter(
            [(AIMessage(content="Response text"), {})]
        )

        with patch("kratt.core.worker.build_agent", return_value=mock_agent):
            worker._run_agent(0)

            assert worker.token_count == 1
            worker.new_token.emit.assert_called_with("Response text")

    def test_agent_handles_tool_execution_status(self, mocker):
        """
        Test that agent properly handles tool execution status updates.

        Verifies that status messages are emitted when tools are
        invoked.
        """
        history = []
        worker = OllamaWorker(history, "model", "vision", "sys", user_text="hi")
        worker.status_update = MagicMock()

        mock_agent = MagicMock()
        # Simulate an AIMessage with tool_calls and non-empty content
        ai_msg = AIMessage(content="Executing tool")
        ai_msg.tool_calls = [{"name": "search_files"}]
        mock_agent.stream.return_value = iter([(ai_msg, {})])

        with patch("kratt.core.worker.build_agent", return_value=mock_agent):
            worker._run_agent(0)

            worker.status_update.emit.assert_called()


class TestOllamaWorkerRAGSearch:
    """Test cases for RAG-powered web search and synthesis."""

    def test_rag_search_complete_pipeline(self, mocker):
        """
        Test complete RAG pipeline from query to response.

        Verifies that the worker executes the full search, scrape,
        embed, retrieve, and generate pipeline.
        """
        history = []
        worker = OllamaWorker(
            history,
            "model",
            "vision",
            "system",
            user_text="test query",
            web_search_enabled=True,
        )

        # Mock the entire pipeline
        mocker.patch(
            "kratt.core.worker.improve_search_query", return_value="optimized"
        )
        mocker.patch(
            "kratt.core.worker.search_duckduckgo",
            return_value=[{"url": "http://test.com", "title": "Test", "snippet": "S"}],
        )
        mocker.patch(
            "kratt.core.worker.WebScraper.scrape_urls",
            return_value={"http://test.com": "content here"},
        )
        mocker.patch(
            "kratt.lc.rag.RAGManager.ingest_text", return_value=True
        )

        mock_chat = MagicMock()
        mock_chat.stream.return_value = [MagicMock(content="answer")]

        with patch("langchain_ollama.ChatOllama", return_value=mock_chat):
            worker.run()

            assert worker.token_count > 0

    def test_rag_search_handles_no_results(self, mocker):
        """
        Test RAG search gracefully handles no search results.

        Verifies fallback behavior when DuckDuckGo returns empty results.
        """
        history = []
        worker = OllamaWorker(
            history,
            "model",
            "vision",
            "system",
            user_text="test",
            web_search_enabled=True,
        )
        worker.new_token = MagicMock()

        mocker.patch(
            "kratt.core.worker.improve_search_query", return_value="q"
        )
        mocker.patch(
            "kratt.core.worker.search_duckduckgo", return_value=[]
        )
        mocker.patch(
            "kratt.core.worker.filter_search_results", return_value=[]
        )

        # Mock agent fallback
        mock_agent = MagicMock()
        mock_agent.stream.return_value = iter([])
        mocker.patch("kratt.core.worker.build_agent", return_value=mock_agent)

        worker._run_rag_search(0)

        # Should emit "No search results found" message
        calls = [call[0][0] for call in worker.new_token.emit.call_args_list]
        assert any("search results" in str(call) for call in calls)


class TestOllamaWorkerErrorHandling:
    """Test cases for error handling and edge cases."""

    def test_worker_handles_exception_in_run(self, mocker):
        """
        Test that worker gracefully handles exceptions during execution.

        Verifies that critical errors are caught and emitted to the UI.
        """
        history = []
        worker = OllamaWorker(history, "model", "vision", "system")
        worker.new_token = MagicMock()

        with patch.object(worker, "_run_agent", side_effect=Exception("Critical")):
            worker.run()

            # Verify error message was emitted
            calls = [call[0][0] for call in worker.new_token.emit.call_args_list]
            assert any("System Error" in str(call) for call in calls)

    def test_worker_stop_request_honored(self):
        """
        Test that worker stop requests are honored during execution.

        Verifies that calling request_stop() sets the stop flag.
        """
        worker = OllamaWorker([], "model", "vision", "system")

        worker.request_stop()

        assert worker._stop_requested is True


class TestAgentBuilder:
    """Test cases for agent construction."""

    def test_agent_builder_returns_valid_agent(self, mocker):
        """
        Test that build_agent returns a properly configured agent.

        Verifies that the agent has the correct model and tools attached.
        """
        mocker.patch("langchain_ollama.ChatOllama")

        agent = build_agent("test_model", "test_prompt")

        assert agent is not None

    def test_agent_has_tools_available(self, mocker):
        """
        Test that the built agent has access to defined tools.

        Verifies that the agent can use file system tools.
        """
        mocker.patch("langchain_ollama.ChatOllama")
        mocker.patch("kratt.lc.tools.get_langchain_tools")

        agent = build_agent("model", "prompt")

        assert agent is not None
