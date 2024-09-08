from quart.wrappers import Websocket
from typing import (
    Optional,
    Any,
    Union,
)
import uuid
from .database import User, DatabaseManager

class Codes:
    Event = 0
    Identify = 1
    Reconnect = 2
    Reidentify = 3
    SessionId = 4
    Hello = 5
    Error = 101
    Success = 102
    Any = 100

class BaseConnection:
    def __init__(self, websocket: Websocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id

class IdentifyPayload:
    def __init__(self, token: str, websocket: Optional[Websocket] = None):
        self.token = token
        self.websocket = websocket

class ReconnectPayload:
    def __init__(self, token: str, session_id: str):
        self.token = token
        self.session_id = session_id

JSONLike = Union[dict, list]

class Client:
    all_connections: list[Websocket] = []
    verified_connections: dict[str, dict[str, Websocket | str | Any]] = {}

    def __init__(self, connection_data: BaseConnection):
        self._connection = connection_data
        self._identified: bool = False
        self.all_connections.append(self._connection.websocket)

    @classmethod
    def from_websocket(cls, websocket: Websocket) -> 'Client':
        session_id = str(uuid.uuid4())
        base_connection = BaseConnection(websocket, session_id)
        return cls(base_connection)

    @property
    def session_id(self):
        return self._connection.session_id

    @property
    def identified(self):
        return self._identified
    
    @property
    def websocket(self):
        return self._connection.websocket

    async def identify(self, identify_data: IdentifyPayload, db: DatabaseManager) -> None:
        if identify_data.websocket:
            self._connection.websocket = identify_data.websocket
        

        if self._connection.websocket not in self.all_connections:
            self.all_connections.append(self._connection.websocket)

        user = await User.from_token(db, identify_data.token)
        if not user:
            return await self._connection.websocket.send_json({'code': Codes.Error, 'd': {'message': 'Invalid payload', 'from': Codes.Reconnect}})
        
        # Change data if already exists
        if self.verified_connections.get(self._connection.session_id):
            self.verified_connections[self._connection.session_id]['token'] = identify_data.token
            self.verified_connections[self._connection.session_id]['websocket'] = self._connection.websocket
        else:
            self.verified_connections[self._connection.session_id] = {
                'token': identify_data.token,
                'websocket': self._connection.websocket
            }
        
        self._identified = True
    
    async def reconnect(self, reconnect_data: ReconnectPayload, db: DatabaseManager) -> None:
        # If not in verified connections, invalidate
        if reconnect_data.session_id not in self.verified_connections:
            return await self._connection.websocket.send_json({'code': Codes.Error, 'd': {'message': 'Invalid payload', 'from': Codes.Reconnect}})
        
        user = await User.from_token(db, reconnect_data.token)
        if not user:
            return await self._connection.websocket.send_json({'code': Codes.Error, 'd': {'message': 'Invalid payload', 'from': Codes.Reconnect}})

        # Update connection in verified list
        self.verified_connections[reconnect_data.session_id]['token'] = reconnect_data.token
        self.verified_connections[reconnect_data.session_id]['websocket'] = self._connection.websocket
        self._identified = True

        # Ensure the connection is added to all connections
        if self._connection.websocket not in self.all_connections:
            self.all_connections.append(self._connection.websocket)
    
    async def receive_json(self) -> JSONLike:
        return await self._connection.websocket.receive_json()
    
    async def send_json(self, payload: JSONLike) -> None:
        await self._connection.websocket.send_json(payload)