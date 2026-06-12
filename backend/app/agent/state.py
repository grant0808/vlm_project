from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    """
    State representing the context passed through LangGraph nodes.
    """
    # User session and session settings
    session_id: str
    user_id: str
    rag_enabled: bool
    tag_enabled: bool
    cag_enabled: bool
    
    # Message history
    messages: List[Dict[str, Any]] # e.g. [{"role": "user", "content": "..."}, ...]
    
    # Multimodal support (base64 images or local image urls uploaded in the current request)
    images: List[str] # List of image URLs or base64 data
    
    # Latest query from the user
    latest_query: str
    
    # Orchestration intermediates
    cag_hit: bool
    cag_result: str | None
    
    rag_context: str | None
    
    tag_result: str | None
    tag_code: str | None # Generated code for pandas/SQL if any
    
    # Selected model (e.g. Qwen2-VL)
    model_name: str
    system_prompt: str | None
    
    # Final generated answer (accumulated or final step)
    final_answer: str
