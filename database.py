import asyncpg
from config import DATABASE_URL


class Db:
    def __init__(self):
        self.conn = None

    async def connect(self):
        self.conn = await asyncpg.connect(DATABASE_URL)

    async def close(self):
        await self.conn.close()

    async def init_db(self):
        await self.connect()
        await self.conn.execute("""
            CREATE EXTENSION IF NOT EXISTS "pgcrypto";
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(60) NOT NULL
            )
        """)
        await self.close()
