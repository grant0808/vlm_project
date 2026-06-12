import json
import redis
from app.config import settings

# Setup redis client
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

class CAGController:
    """
    Cache-Augmented Generation (CAG) Controller.
    Manages semantic cache lookups, fixed system contexts, and large prompt templates
    cached in Redis to skip vector search latency and reduce LLM reasoning costs.
    """
    @staticmethod
    def check_cache(session_id: str, query: str) -> tuple[bool, str | None]:
        """
        Check if there is a cached response or active CAG context for the query.
        """
        # 1. Exact match check in Redis (Can be upgraded to Semantic search using Redis VL)
        cache_key = f"cag:session:{session_id}:query:{query.strip().lower()}"
        cached_val = redis_client.get(cache_key)
        if cached_val:
            print(f"[CAG] Cache hit for query: '{query}'")
            return True, cached_val

        # 2. Check for Session-wide static context cached (e.g. giant manuals, database catalogs)
        session_context_key = f"cag:session:{session_id}:static_context"
        static_context = redis_client.get(session_context_key)
        if static_context:
            print(f"[CAG] Retrieved session-wide static context from Redis cache.")
            # We return False for 'hit' (as in it's not a direct answer cache), but we provide the context
            return False, static_context

        return False, None

    @staticmethod
    def set_cache(session_id: str, query: str, answer: str, expire_seconds: int = 3600):
        """
        Cache the generated answer for future queries.
        """
        cache_key = f"cag:session:{session_id}:query:{query.strip().lower()}"
        redis_client.setex(cache_key, expire_seconds, answer)
        print(f"[CAG] Cached answer for query: '{query}'")

    @staticmethod
    def cache_static_context(session_id: str, context: str, expire_seconds: int = 86400):
        """
        Cache a massive multi-modal context or system guidelines to make it readily available
        without retrieving from Chroma DB vector search.
        """
        session_context_key = f"cag:session:{session_id}:static_context"
        redis_client.setex(session_context_key, expire_seconds, context)
        print(f"[CAG] Cached large context in Redis for Session: {session_id}")
