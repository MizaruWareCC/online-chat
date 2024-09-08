import asyncpg
from typing import (
    TypeVar,
    Optional,
)
from .snowflake import SnowflakeGenerator
import jwt
import asyncio
import datetime

SECRET_KEY = 'ZjW892KWFkwFHZlwp93127wdfA'

T = TypeVar('T')
TableShema = str

class DatabaseManager:
    def __init__(self, *args, **kwargs):
        self._pool: asyncpg.Pool | None = None
        self._a = args
        self._kw = kwargs

    async def start(self, table_schema: Optional[list[TableShema]] = None) -> None:
        self._pool: asyncpg.Pool = await asyncpg.create_pool(*self._a, **self._kw)
        if table_schema:
            for query in table_schema:
                await self.execute('CREATE TABLE IF NOT EXISTS '+query)
    
    @property
    def pool(self):
        return self._pool
    
    async def fetch(self, query: str, *args):
        async with self._pool.acquire() as con:
            con: asyncpg.Connection
            return await con.fetch(query, *args)
        
    async def fetchval(self, query: str, *args):
        async with self._pool.acquire() as con:
            con: asyncpg.Connection
            return await con.fetchval(query, *args)
        
    async def fetchrow(self, query: str, *args):
        async with self._pool.acquire() as con:
            con: asyncpg.Connection
            return await con.fetchrow(query, *args)
    
    async def execute(self, query: str, *args):
        async with self._pool.acquire() as con:
            con: asyncpg.Connection
            await con.execute(query, *args)
    
    async def close(self):
        await self._pool.close()
            

class User:
    def __init__(self, manager: DatabaseManager, id: int, name: str, password: str):
        self._db = manager
        self._name = name
        self._id = id
        self._password = password

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def password(self) -> str:
        return self._password

    async def change_name(self, new_name: str) -> None:
        await self._db.execute('UPDATE users SET username = $1 WHERE id = $2', new_name, self._id)
        self._name = new_name

    async def change_password(self, new_password: str) -> None:
        await self._db.execute('UPDATE users SET password = $1 WHERE id = $2', new_password, self._id)
        self._password = new_password

    async def delete(self) -> None:
        await self._db.execute('DELETE FROM users WHERE id = $1 AND username = $2', self._id, self._name)

    async def get_token(self) -> str:
        payload = {
            'user_id': str(self._id),
        }
        token = await asyncio.to_thread(jwt.encode, payload, SECRET_KEY, algorithm='HS256')
        return token

    @classmethod
    async def from_token(cls, dbmanager: DatabaseManager, token: str) -> Optional['User']:
        try:
            payload = await asyncio.to_thread(jwt.decode, token, SECRET_KEY, algorithms=['HS256'])
            user_id = payload['user_id']
            user = await cls.from_id(dbmanager, int(user_id))
            return user
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")


    @classmethod
    async def create(cls, dbmanager: DatabaseManager, snowflake_generator: SnowflakeGenerator, name: str, password: str) -> 'User':
        id = await snowflake_generator.generate()
        await dbmanager.execute('INSERT INTO users (id, username, password) VALUES ($1, $2, $3)', id, name, password)
        return cls(dbmanager, id, name, password)

    @classmethod
    async def from_id(cls, dbmanager: DatabaseManager, id: int) -> Optional['User']:
        d = await dbmanager.fetchrow('SELECT username, password FROM users WHERE id = $1', id)
        if d:
            return cls(dbmanager, id, d['username'], d['password'])
        return None

    @classmethod
    async def from_name(cls, dbmanager: DatabaseManager, name: str) -> Optional['User']:
        d = await dbmanager.fetchrow('SELECT id, password FROM users WHERE username = $1', name)
        if d:
            return cls(dbmanager, d['id'], name, d['password'])
        return None

    @staticmethod
    async def exists(dbmanager: DatabaseManager, name: str) -> bool:
        val = await dbmanager.fetchval('SELECT username FROM users WHERE username = $1', name)
        return bool(val)