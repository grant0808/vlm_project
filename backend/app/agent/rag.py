from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.config import settings

class RAGController:
    """
    Retrieval-Augmented Generation (RAG) Controller.
    Queries the Chroma DB vector store for context matching the user's query.
    """
    @staticmethod
    def get_embedding_model():
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_base=settings.VLLM_API_BASE,
            openai_api_key=settings.VLLM_API_KEY
        )

    @staticmethod
    def retrieve_context(session_id: str, query: str, top_k: int = 4) -> str:
        """
        Search for relevant chunks inside the Chroma collection dedicated to this session.
        """
        print(f"[RAG] Retrieving context for query: '{query}' in session: {session_id}")
        try:
            embeddings = RAGController.get_embedding_model()
            db = Chroma(
                persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
                embedding_function=embeddings,
                collection_name=f"session_{session_id}"
            )
            
            # Retrieve documents
            docs = db.similarity_search(query, k=top_k)
            if not docs:
                print("[RAG] No matching documents found in Chroma DB.")
                return ""
            
            # Combine retrieved segments
            context_pieces = []
            for doc in docs:
                source_info = doc.metadata.get("file_name", "Unknown Document")
                context_pieces.append(f"--- Document Source: {source_info} ---\n{doc.page_content}")
            
            retrieved_text = "\n\n".join(context_pieces)
            print(f"[RAG] Retreived {len(docs)} document chunks successfully.")
            return retrieved_text
            
        except Exception as e:
            print(f"[RAG] Error during vector database retrieval: {str(e)}")
            return ""
