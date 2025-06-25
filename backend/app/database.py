# app/database.py
import asyncpg
import asyncio

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self, url):
        self.pool = await asyncpg.create_pool(dsn=url)

    async def disconnect(self):
        await self.pool.close()

    async def fetch_one(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

db = Database()
