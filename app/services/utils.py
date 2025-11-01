
import httpx
from contextlib import asynccontextmanager
from aiolimiter import AsyncLimiter
from tenacity import retry, stop_after_attempt, wait_exponential

# Simple global rate limiter (adjust as needed)
limiter = AsyncLimiter(8, 1)  # 8 req/sec

@asynccontextmanager
async def backoff_client():
    async with httpx.AsyncClient() as client:
        yield client

@retry(wait=wait_exponential(multiplier=0.5, min=1, max=8), stop=stop_after_attempt(4))
async def limited_get(client: httpx.AsyncClient, url: str, **kwargs):
    async with limiter:
        resp = await client.get(url, **kwargs)
        resp.raise_for_status()
        return resp
