from typing import Any, Dict, List
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from app.config import settings
from app.agent.state import AgentState
from app.agent.cag import CAGController
from app.agent.rag import RAGController
from app.agent.tag import TAGController

# Initialize VLM Client (Qwen2-VL via OpenAI compatible API in vLLM)
def get_vlm_client(streaming: bool = True):
    return ChatOpenAI(
        model=settings.VLM_MODEL_NAME,
        openai_api_base=settings.VLLM_API_BASE,
        openai_api_key=settings.VLLM_API_KEY,
        temperature=0.1,
        streaming=streaming
    )

# --- LANGGRAPH NODES ---

def check_cag_cache(state: AgentState) -> Dict[str, Any]:
    """
    CAG Node: Check if query exists in semantic or session cache in Redis.
    """
    if not state.get("cag_enabled", True):
        return {"cag_hit": False, "cag_result": None}
        
    session_id = state["session_id"]
    query = state["latest_query"]
    
    hit, result = CAGController.check_cache(session_id, query)
    if hit:
        return {"cag_hit": True, "cag_result": result, "final_answer": result}
    
    # If not direct answer hit, but retrieved session wide static context
    return {"cag_hit": False, "cag_result": result}

def retrieve_rag_context(state: AgentState) -> Dict[str, Any]:
    """
    RAG Node: Retrieve context from Chroma DB if enabled.
    """
    if not state.get("rag_enabled", True):
        return {"rag_context": None}
        
    session_id = state["session_id"]
    query = state["latest_query"]
    
    context = RAGController.retrieve_context(session_id, query)
    return {"rag_context": context}

def execute_tag_operations(state: AgentState) -> Dict[str, Any]:
    """
    TAG Node: Extract and execute table/database operations or external tools.
    """
    if not state.get("tag_enabled", False):
        return {"tag_result": None, "tag_code": None}
        
    query = state["latest_query"]
    
    # Detect if we need to call external API or compute code
    if "weather" in query.lower():
        # Tag api call
        # Mock parameter extraction, in production use LLM Function calling
        import asyncio
        tool_result = asyncio.run(TAGController.call_external_api("get_weather", {"location": "Seoul"}))
        return {"tag_result": tool_result}
        
    elif "stock" in query.lower() or "price" in query.lower():
        import asyncio
        tool_result = asyncio.run(TAGController.call_external_api("get_stock_price", {"ticker": "AAPL"}))
        return {"tag_result": tool_result}
        
    elif TAGController.identify_tabular_query(query):
        # Generate pandas code and run it
        # For simulation, we create a mock DataFrame and run simulated code.
        import pandas as pd
        df = pd.DataFrame({
            "Item": ["A", "B", "C"],
            "Price": [100, 200, 300]
        })
        
        simulated_pandas_code = "print(df.groupby('Item').sum())"
        result = TAGController.execute_pandas_code(simulated_pandas_code, {"df": df})
        return {"tag_result": result, "tag_code": simulated_pandas_code}
        
    return {"tag_result": None}

def build_multimodal_prompt(state: AgentState) -> List[Any]:
    """
    Combine System prompt, Context (RAG/TAG/CAG), Images (Base64/URL), and Query
    into a structured LangChain prompt.
    """
    messages = []
    
    # System Instruction
    sys_prompt = state.get("system_prompt") or "You are Qwen2-VL, a helpful assistant with multi-modal capabilities."
    messages.append(SystemMessage(content=sys_prompt))
    
    # Assemble context block
    context_str = ""
    if state.get("cag_result"):
        context_str += f"\n[Static Cached Context (CAG)]:\n{state['cag_result']}\n"
    if state.get("rag_context"):
        context_str += f"\n[Retrieved Context (RAG)]:\n{state['rag_context']}\n"
    if state.get("tag_result"):
        context_str += f"\n[Tabular/Tool Operations Result (TAG)]:\n{state['tag_result']}\n"
        if state.get("tag_code"):
            context_str += f"Executed Code:\n{state['tag_code']}\n"

    # User Input Content
    content_list = []
    if context_str:
        content_list.append({"type": "text", "text": f"Context for answering the query:\n{context_str}\n"})
        
    content_list.append({"type": "text", "text": f"User Query: {state['latest_query']}"})
    
    # Multimodal image support
    for image_data in state.get("images", []):
        # Qwen2-VL expects standard OpenAI schema for images (url or base64 format)
        if image_data.startswith("data:image"):
            content_list.append({
                "type": "image_url",
                "image_url": {"url": image_data}
            })
        else:
            content_list.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"} # Fallback base64
            })
            
    messages.append(HumanMessage(content=content_list))
    return messages

# --- ROUTING LOGIC ---

def route_after_cag(state: AgentState) -> str:
    """
    If CAG hits, we bypass RAG and TAG and go straight to END.
    Otherwise, run Retrieval (RAG/TAG).
    """
    if state.get("cag_hit", False):
        return "end"
    return "retrieve"

# --- AGENT WORKFLOW COMPILATION ---

def build_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    # Define Nodes
    workflow.add_node("check_cag", check_cag_cache)
    workflow.add_node("retrieve_rag", retrieve_rag_context)
    workflow.add_node("execute_tag", execute_tag_operations)
    
    # Define Flow
    workflow.set_entry_point("check_cag")
    
    # Conditional Routing from CAG
    workflow.add_conditional_edges(
        "check_cag",
        route_after_cag,
        {
            "end": END,
            "retrieve": "retrieve_rag"
        }
    )
    
    # Sequential retrieval flow
    workflow.add_edge("retrieve_rag", "execute_tag")
    workflow.add_edge("execute_tag", END)
    
    return workflow.compile()

# Compilation instance
agent_workflow = build_workflow()

async def run_vlm_agent_stream(state: AgentState):
    """
    Execute the workflow states, build final multimodal prompt, 
    and stream response chunk by chunk.
    """
    # 1. Run LangGraph to gather context
    final_state = await agent_workflow.ainvoke(state)
    
    # If CAG hit directly, stream the cached result immediately
    if final_state.get("cag_hit"):
        yield final_state["final_answer"]
        return
        
    # 2. Build Chat Messages for Qwen2-VL
    messages = build_multimodal_prompt(final_state)
    
    # 3. Stream from VLM Client
    vlm = get_vlm_client(streaming=True)
    accumulated_content = ""
    
    # Call async stream on LangChain ChatOpenAI
    async for chunk in vlm.astream(messages):
        content_chunk = chunk.content
        accumulated_content += content_chunk
        yield content_chunk
        
    # 4. Optional: Save final answer to Redis Cache for future CAG optimization
    if final_state.get("cag_enabled") and not final_state.get("images"):
        # We only cache text queries without images to keep cache key simple
        CAGController.set_cache(
            session_id=final_state["session_id"],
            query=final_state["latest_query"],
            answer=accumulated_content
        )
