"""
RAG Pipeline: Text splitting, embedding, and retrieval.

Provides the RAGManager class for ingesting documents and
performing similarity-based retrieval using FAISS and Ollama embeddings.
"""

from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from kratt.config import RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_TOP_K, DEFAULT_EMBED_MODEL


class RAGManager:
    """Manages document ingestion and vector-based retrieval."""

    def __init__(self, embed_model_name: str = DEFAULT_EMBED_MODEL):
        """
        Initialize the RAG manager.

        Args:
            embed_model_name: Name of the embedding model (Ollama).
        """
        self.embed_model_name = embed_model_name
        self.vector_store = None

    def ingest_text(self, text_data: dict[str, str]) -> bool:
        """
        Ingest scraped text into a temporary FAISS vector store.

        Args:
            text_data: Dict mapping URL/source to text content.

        Returns:
            True if ingestion succeeded, False otherwise.
        """
        if not text_data:
            return False

        documents = []
        for source, text in text_data.items():
            documents.append(Document(page_content=text, metadata={"source": source}))

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=RAG_CHUNK_SIZE,
            chunk_overlap=RAG_CHUNK_OVERLAP
        )
        splits = text_splitter.split_documents(documents)

        if not splits:
            return False

        try:
            embeddings = OllamaEmbeddings(model=self.embed_model_name)
            self.vector_store = FAISS.from_documents(splits, embeddings)
            return True
        except Exception as e:
            print(f"RAG Ingestion failed: {e}")
            return False

    def retrieve(self, query: str) -> str:
        """
        Retrieve relevant context for a query using similarity search.

        Args:
            query: The search query.

        Returns:
            Formatted string of relevant documents with source attribution.
        """
        if not self.vector_store:
            return ""

        try:
            retriever = self.vector_store.as_retriever(search_kwargs={"k": RAG_TOP_K})
            docs = retriever.invoke(query)

            context_str = ""
            for i, doc in enumerate(docs):
                source = doc.metadata.get("source", "unknown")
                content = doc.page_content.replace("\n", " ")
                context_str += f"[Source {i + 1}: {source}]\n{content}\n\n"

            return context_str
        except Exception as e:
            print(f"Retrieval failed: {e}")
            return ""