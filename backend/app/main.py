from contextlib import asynccontextmanager
import os
import shutil
import uuid
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr

from app.config import settings
from app.database import engine, Base, get_db, User, ChatSession, ChatMessage, async_session_maker
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.worker import embedding_queue, process_document_embedding
from app.agent.graph import run_vlm_agent_stream
from app.agent.state import AgentState

# Async DB Setup during application start
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # Create database tables if they do not exist
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SessionCreate(BaseModel):
    title: str = "New Conversation"

class SessionSettingsUpdate(BaseModel):
    rag_enabled: bool
    tag_enabled: bool
    cag_enabled: bool
    system_prompt: str | None = None

class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    rag_enabled: bool
    tag_enabled: bool
    cag_enabled: bool
    system_prompt: str | None
    
    class Config:
        from_attributes = True

# --- API Endpoints ---

# 1. Authentication
@app.post(f"{settings.API_V1_STR}/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    query = select(User).where(User.email == user_in.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, hashed_password=hashed_pwd)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    access_token = create_access_token(subject=new_user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post(f"{settings.API_V1_STR}/auth/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.email == user_in.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

# 2. Chat Sessions Management
@app.post(f"{settings.API_V1_STR}/chat/sessions", response_model=SessionResponse)
async def create_chat_session(
    session_in: SessionCreate, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    new_session = ChatSession(user_id=current_user.id, title=session_in.title)
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session

@app.get(f"{settings.API_V1_STR}/chat/sessions", response_model=List[SessionResponse])
async def list_chat_sessions(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    query = select(ChatSession).where(ChatSession.user_id == current_user.id).order_by(ChatSession.updated_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

@app.patch(f"{settings.API_V1_STR}/chat/sessions/{{session_id}}", response_model=SessionResponse)
async def update_session_settings(
    session_id: uuid.UUID,
    settings_in: SessionSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    session.rag_enabled = settings_in.rag_enabled
    session.tag_enabled = settings_in.tag_enabled
    session.cag_enabled = settings_in.cag_enabled
    session.system_prompt = settings_in.system_prompt
    
    await db.commit()
    await db.refresh(session)
    return session

# 3. Document / Image upload (RAG Background Task enqueue)
@app.post(f"{settings.API_V1_STR}/chat/upload")
async def upload_document(
    session_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify session ownership
    query = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    # Save uploaded file temporarily for worker to process
    temp_dir = "./temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    temp_file_path = os.path.join(temp_dir, f"{file_id}_{file.filename}")
    
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Enqueue background index task into Redis Queue (RQ)
    job = embedding_queue.enqueue(
        process_document_embedding,
        args=(temp_file_path, file.filename, str(session_id), file.content_type),
        job_timeout="10m"
    )
    
    return {"message": "File upload successful. Processing embeddings in the background.", "job_id": job.id}

# 4. SSE (Server-Sent Events) Stream for real-time chatbot response
@app.get(f"{settings.API_V1_STR}/chat/stream")
async def chat_stream(
    session_id: uuid.UUID,
    query: str,
    image_base64: str | None = None,  # Optional image input (VLM)
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify session ownership
    session_query = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    session_res = await db.execute(session_query)
    session = session_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Get previous chat history for agent context
    msg_query = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
    msg_res = await db.execute(msg_query)
    messages_history = msg_res.scalars().all()
    
    history_list = [{"role": msg.role, "content": msg.content} for msg in messages_history]
    
    # Save the User's message first
    user_metadata = {"image_uploaded": True} if image_base64 else None
    user_msg = ChatMessage(session_id=session_id, role="user", content=query, meta_data=user_metadata)
    db.add(user_msg)
    await db.commit()

    # Prep the Agent State
    state = AgentState(
        session_id=str(session_id),
        user_id=str(current_user.id),
        rag_enabled=session.rag_enabled,
        tag_enabled=session.tag_enabled,
        cag_enabled=session.cag_enabled,
        messages=history_list,
        images=[image_base64] if image_base64 else [],
        latest_query=query,
        cag_hit=False,
        cag_result=None,
        rag_context=None,
        tag_result=None,
        tag_code=None,
        model_name=settings.VLM_MODEL_NAME,
        system_prompt=session.system_prompt,
        final_answer=""
    )

    async def event_generator():
        bot_response_accumulator = []
        try:
            # Consume stream generator from compiled agent graph
            async for chunk in run_vlm_agent_stream(state):
                bot_response_accumulator.append(chunk)
                # SSE Format
                yield f"data: {chunk}\n\n"
                
            # Stream end delimiter
            yield "data: [DONE]\n\n"
            
            # Save complete bot message back to DB
            full_response = "".join(bot_response_accumulator)
            bot_msg = ChatMessage(session_id=session_id, role="assistant", content=full_response)
            
            # Open a new session since streaming connection block can close the main session context
            async with async_session_maker() as new_db_session:
                new_db_session.add(bot_msg)
                await new_db_session.commit()
                
        except Exception as e:
            # Yield error token
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
