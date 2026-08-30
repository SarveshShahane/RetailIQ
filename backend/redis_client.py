import redis
import os
from dotenv import load_dotenv
import asyncio
load_dotenv()

redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_ssl = os.getenv("REDIS_SSL", "false").lower() in ("true", "1", "yes") or redis_port == 6380

redisClient = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=redis_port,
    decode_responses=bool(os.getenv("REDIS_DECODE_RESPONSES", "true")),
    username=os.getenv("REDIS_USERNAME") or None,
    password=os.getenv("REDIS_PASSWORD") or None,
    ssl=redis_ssl,
    socket_timeout=5,
    socket_connect_timeout=5,
)

