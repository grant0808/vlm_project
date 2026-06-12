# 프로젝트 아키텍처 개요

이 문서는 VLM (Vision-Language Model) 프로젝트의 시스템 아키텍처와 주요 데이터 흐름을 설명합니다. 본 시스템은 Vite 기반의 React 프론트엔드, FastAPI 백엔드, Redis Queue를 활용한 비동기 백그라운드 워커, 그리고 LangGraph 기반의 VLM 에이전트 파이프라인으로 구성되어 있습니다.

---

## 1. 하이레벨 시스템 아키텍처

아래 다이어그램은 각 레이어 간의 컴포넌트가 어떻게 상호작용하는지 보여줍니다.

```mermaid
graph TD
    %% 클래스 스타일 정의
    classDef frontend fill:#3b82f6,stroke:#1d4ed8,color:#fff;
    classDef backend fill:#10b981,stroke:#047857,color:#fff;
    classDef background fill:#f59e0b,stroke:#b45309,color:#fff;
    classDef database fill:#6366f1,stroke:#4338ca,color:#fff;
    classDef agent fill:#8b5cf6,stroke:#6d28d9,color:#fff;

    %% 프론트엔드 레이어
    subgraph Frontend ["React 프론트엔드 레이어"]
        App["App.tsx"]
        Store["useChatStore.ts (Zustand)"]
        Components["Sidebar / Chat / Settings"]
    end

    %% 백엔드 레이어
    subgraph Backend ["FastAPI 백엔드 레이어"]
        API["main.py (FastAPI App)"]
        Auth["auth.py (JWT & 인증관리)"]
        DBSession["database.py (SQLAlchemy Async)"]
    end

    %% 데이터베이스 및 캐시 레이어
    subgraph Storage ["저장소 및 데이터베이스 레이어"]
        PostgreSQL[("PostgreSQL (사용자 및 채팅 데이터)")]
        Redis[("Redis (RQ 브로커)")]
        Chroma[("Chroma DB (벡터 임베딩)")]
    end

    %% 백그라운드 처리 레이어
    subgraph Background ["백그라운드 처리 레이어"]
        RQ["Redis Queue"]
        Worker["worker.py (RQ 워커)"]
    end

    %% AI 에이전트 레이어
    subgraph Agent ["VLM 에이전트 레이어"]
        Graph["LangGraph VLM Agent"]
        RAG["RAG 파이프라인"]
        CAG["CAG 파이프라인"]
        TAG["TAG 파이프라인"]
    end

    %% 스타일 클래스 할당
    class App,Store,Components frontend;
    class API,Auth,DBSession backend;
    class RQ,Worker background;
    class PostgreSQL,Redis,Chroma database;
    class Graph,RAG,CAG,TAG agent;

    %% 흐름 연결
    App --> Store
    Components --> Store
    Store -->|HTTP 요청 / SSE| API
    
    API --> Auth
    API --> DBSession
    DBSession --> PostgreSQL
    
    %% 파일 업로드 흐름
    API -->|1. 작업 등록 Enqueue| RQ
    RQ <-->|2. 작업 큐 브로커| Redis
    Redis -->|3. 작업 가져오기 Fetch| Worker
    Worker -->|4. 임베딩 생성 및 저장| Chroma

    %% 채팅 SSE 스트림 흐름
    API -->|VLM 스트림 실행| Graph
    Graph --> RAG
    Graph --> CAG
    Graph --> TAG
    RAG -->|벡터 쿼리| Chroma
```

---

## 2. 주요 데이터 흐름

### A. 사용자 인증 흐름 (회원가입 및 로그인)
사용자 인증은 JWT 토큰 방식으로 처리됩니다. 비밀번호 암호화 로직은 로컬 및 배포 환경의 호환성 이슈 해결을 위해 임시로 평문(Plaintext) 비교 및 저장 방식으로 수정되었습니다.

```mermaid
sequenceDiagram
    autonumber
    actor User as 클라이언트 (App.tsx)
    participant Store as useChatStore.ts
    participant API as main.py (FastAPI)
    participant Auth as auth.py
    participant DB as PostgreSQL

    User->>Store: 이메일 및 비밀번호 제출
    Store->>API: POST /api/v1/auth/register (JSON)
    API->>DB: 사용자 중복 여부 확인
    DB-->>API: 가입되지 않은 이메일
    API->>Auth: get_password_hash(password)
    Note over Auth: 평문 비밀번호 반환<br/>(Bcrypt 해싱 비활성화)
    API->>DB: 사용자 정보 추가 (평문 패스워드)
    DB-->>API: 추가 완료
    API->>Auth: create_access_token(user_id)
    Auth-->>API: JWT 토큰 생성 (access_token)
    API-->>Store: 201 Created (토큰 및 타입 반환)
    Store->>Store: LocalStorage에 토큰 저장
    Store-->>User: 로그인 완료 및 워크스페이스 뷰 렌더링
```

---

### B. 채팅 SSE (Server-Sent Events) 스트리밍 흐름
VLM(Vision-Language Model)의 실시간 답변 출력을 위해 시스템은 LangGraph와 SSE 스트림을 구현하여 실시간 통신을 수행합니다.

```mermaid
sequenceDiagram
    autonumber
    actor User as 클라이언트 (Chat UI)
    participant Store as useChatStore.ts
    participant API as main.py (FastAPI)
    participant Graph as LangGraph VLM Agent
    participant DB as PostgreSQL

    User->>Store: 질문 입력 ("안녕하세요")
    Store->>Store: 답변 대기용 placeholder 메시지 추가
    Store->>API: GET /api/v1/chat/stream?session_id=...&query=...
    API->>DB: 사용자 입력 메시지 저장
    API->>Graph: AgentState 초기화 및 run_vlm_agent_stream() 실행
    
    loop 답변 스트리밍
        Graph-->>API: 답변 텍스트 청크(chunk) 반환
        API-->>Store: SSE 청크 전송 (data: text)
        Store->>User: UI에 실시간 텍스트 누적 업데이트
    end
    
    Graph-->>API: 스트림 종료 표시 전송 (data: [DONE])
    API->>DB: 최종 누적된 답변 메시지를 DB에 저장
    API-->>Store: 연결 종료 (Connection Close)
```

---

### C. 파일 업로드 및 비동기 문서 임베딩 흐름
RAG(검색 증강 생성) 처리를 위해 업로드된 대용량 파일이나 문서는 메인 스레드를 블로킹하지 않도록 Redis Queue를 사용하여 비동기로 처리됩니다.

```mermaid
sequenceDiagram
    autonumber
    actor User as 클라이언트
    participant Store as useChatStore.ts
    participant API as main.py (FastAPI)
    participant RQ as Redis Queue
    participant Worker as RQ 워커
    participant Chroma as Chroma Vector DB

    User->>Store: 파일 업로드
    Store->>API: POST /api/v1/chat/upload (FormData)
    API->>API: ./temp_uploads 폴더에 임시 파일 저장
    API->>RQ: 비동기 작업 등록 (process_document_embedding)
    API-->>Store: 200 OK (등록된 Job ID 반환)
    Store-->>User: 업로드 완료 메시지 표시 (백그라운드 처리 중)
    
    Note over Worker: 워커 대기 상태...
    Worker->>RQ: 작업 가져오기 (Dequeue)
    Worker->>Worker: 문서 텍스트/이미지 파싱
    Worker->>Worker: 텍스트 분할 및 벡터 임베딩 생성
    Worker->>Chroma: ChromaDB에 벡터 인덱싱
    Worker->>Worker: 임시 생성된 파일 삭제
```

---

## 3. 기술 스택 및 컴포넌트 디렉토리

### 프론트엔드 (Frontend)
- **프레임워크**: React 18, TypeScript, Vite
- **스타일링**: Tailwind CSS
- **상태 관리**: Zustand
- **디렉토리**: `frontend/`
  - `src/App.tsx`: 인증 화면(로그인/회원가입) 및 메인 레이아웃 뷰 렌더링.
  - `src/store/useChatStore.ts`: 상태 저장 및 API 요청 처리.
  - `src/components/`: 레이아웃 서브 컴포넌트(Chat panel, Settings modal, Sidebar).

### 백엔드 (Backend)
- **프레임워크**: FastAPI (Python >= 3.11)
- **데이터베이스 ORM**: SQLAlchemy (Async)
- **작업 큐**: RQ (Redis Queue)
- **에이전트 오케스트레이션**: LangGraph & LangChain
- **디렉토리**: `backend/`
  - `app/main.py`: REST API 엔드포인트 및 SSE 컨트롤러 정의.
  - `app/auth.py`: JWT 토큰 발급 및 평문 패스워드 인증 로직 구현.
  - `app/database.py`: SQLAlchemy 기반 DB 세션 관리 및 모델(User, ChatSession, ChatMessage) 정의.
  - `app/worker.py`: 비동기 문서 파싱 및 벡터 임베딩 등록 백그라운드 워커.
  - `app/agent/`: LangGraph 기반의 AI VLM 에이전트 인텔리전트 파이프라인.
