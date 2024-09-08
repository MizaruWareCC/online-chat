from modules.client import Client, IdentifyPayload, ReconnectPayload
from modules.utils import indexof
from modules.database import DatabaseManager, User
from modules.snowflake import SnowflakeGenerator
from typing import (
    Optional
)
import asyncio

from quart import Quart, websocket, request, Response, jsonify, make_response, render_template

app = Quart(__name__)

db = DatabaseManager(dsn='postgres://zrxw:zrxw@localhost:5432/chat')

def is_valid_str(s: Optional[str], type: int) -> bool:       
    if not s:
        return Response(status=400)
    if (len(s) < 2 or len(s) > 34) and type == 1: 
        return Response(status=400)
    if (len(s) < 6 or len(s) > 125) and type == 2: 
        return Response(status=400)
    
    for char in s:
        if not (char.isdigit() or char.isalpha()):
            return False
    
    return True


snowflake = SnowflakeGenerator(worker_id=1, process_id=1)

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

@app.websocket('/')
async def gateway():
    try:
        client = Client.from_websocket(websocket._get_current_object())
        await client.send_json({'code': Codes.SessionId, 'd': {'id': client.session_id}})

        while True:
            try:
                data = await client.receive_json()
            except Exception as e:
                await client.send_json({'code': Codes.Error, 'd': {'message': f'Invalid payload: {str(e)}', 'from': Codes.Any}})
                continue
            
            if data.get('code') == Codes.Identify:
                try:
                    await client.identify(IdentifyPayload(token=data['d']['token']), db)
                    await client.send_json({'code': Codes.Success, 'd': {'from': Codes.Identify}})
                except Exception as e:
                    await client.send_json({'code': Codes.Error, 'd': {'message': 'Invalid payload', 'from': Codes.Identify}})
            elif data.get('code') == Codes.Reconnect:
                try:
                    await client.reconnect(ReconnectPayload(token=data['d']['token'], session_id=data['d']['session_id']), db)
                    await client.send_json({'code': Codes.Success, 'd': {'from': Codes.Reconnect}})
                except Exception as e:
                    await client.send_json({'code': Codes.Error, 'd': {'message': 'Invalid payload', 'from': Codes.Reconnect}})
            else:
                await client.send_json({'code': Codes.Error, 'd': {'message': 'Unknown code', 'from': Codes.Any}})

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        index = await indexof(client.all_connections, client.websocket)
        if index is not None:
            client.all_connections.pop(index)
        
        if client.identified:
            client.verified_connections.pop(client.session_id, None)
        

@app.route('/api/v1/register', methods=['POST'])
async def registerapi():
    js = await request.get_json()
    if not isinstance(js, dict): 
        return Response('Invalid JSON', status=400)
    
    isvn = is_valid_str(js.get('username'), 1)
    isvp = is_valid_str(js.get('password'), 2)
    
    if isvn != True: return isvn if isvn != False else Response(status=400)
    if isvp != True: return isvp if isvp != False else Response(status=400)

    if await User.exists(db, js.get('username')):
        return Response('User already exists', status=409)

    await User.create(db, snowflake, js.get('username'), js.get('password'))
    return Response(status=201)

@app.route('/api/v1/users/<id>', methods=['GET', 'PATCH', 'DELETE'])
async def user_request_handle(id: Optional[int] = None):
    try:
        id = int(id)
    except:
        return Response('Invalid id (not an integer)', status=400)
    if request.method == 'GET':
        user = await User.from_id(db, id)
        if not user: return Response('Invalid id', status=400)
        return jsonify({'username': user.name, 'id': user.id})
    elif request.method == 'PATCH':
        token = request.headers.get('Authorization')
        if not token: return Response('No token provided', status=401)
            
        user = await User.from_id(db, id)

        if not user: return Response('Invalid id', status=400)
        if await user.get_token() != token: return Response('Invalid token', status=401)

        
        js = await request.get_json()
        if not isinstance(js, dict): return Response('Invalid json', status=400)
        
        if js.get('username'):
            isvn = is_valid_str(js.get('username'), 1)
            if isvn != True: return isvn if isvn != False else Response(status=400)
            await user.change_name(js.get('username'))
        if js.get('password'):
            isvp = is_valid_str(js.get('password'), 2)
            if isvp != True: return isvp if isvp != False else Response(status=400)
            await user.change_password(js.get('password'))

        return Response(status=201)
    elif request.method == 'DELETE':
        token = request.headers.get('Authorization')
        if not token: return Response('No token provided', status=401)
            
        user = await User.from_id(db, id)

        if not user: return Response('Invalid id', status=400)
        if await user.get_token() != token: return Response('Invalid token', status=401)
        await user.delete()
        return Response(status=201)
    
@app.route('/api/v1/get_token', methods=['POST'])
async def gettnk():
    try:
        js = await request.get_json()
        if not isinstance(js, dict): return Response(status=400)
        if not js.get('username') or not js.get('password'): return Response(status=400)
        user = await User.from_name(db, js['username'])
        if not user: return Response(status=401)
        if user.password != js['password']: return Response(status=403)
        return await user.get_token()
    except: return Response(status=500)

@app.route('/api/v1/set_cookies', methods=['POST'])
async def settnk():
    try:
        js = await request.get_json()
        if not isinstance(js, dict): return Response(status=400)
        if not js.get('username') or not js.get('password'): return Response(status=400)
        user = await User.from_name(db, js['username'])
        if not user: return Response(status=401)
        if user.password != js['password']: return Response(status=403)
        r: Response = await make_response('Set cookie')
        r.set_cookie('token', await user.get_token())
        r.set_cookie('userId', str(user.id))
        r.set_cookie('username', user.name)
        return r
    except: return Response(status=500)

@app.route('/')
async def index_chat():
    return await render_template('index.html')

@app.route('/api/v1/validate_token', methods=['GET'])
async def validate_token():
    token = request.headers.get('Authorization')
    if not token:
        return Response(status=401)
    
    try:
        user = await User.from_token(db, token)
        if not user:
            return Response('Invalid token', status=401)
        
        return jsonify({'message': 'Token is valid', 'username': user.name}), 200
    except Exception as e:
        return Response('Invalid token or error occurred', status=401)

@app.route('/api/v1/messages/', methods=['POST', 'GET'])
async def messages():
    auth = request.headers.get('Authorization')
    if request.method == 'POST':
        data = await request.get_json()
        if not auth:
            return Response(status=401)
        user = await User.from_token(db, auth)
        if not user:
            return Response(status=400)
        if not data.get('content') or len(data.get('content', '')) > 600:
            return Response(status=400)
        
        id = await snowflake.generate()
        
        await db.execute('INSERT INTO messages VALUES ($1, $2, $3, $4)', id, data.get('content'), user.id, user.name)
        for session_id, connection_data in Client.verified_connections.items():
            if connection_data.get('websocket'):
                asyncio.create_task(connection_data['websocket'].send_json({'code': Codes.Event, 'ev': 'MESSAGE_SENT', 'd': {'content': data.get('content'), 'id': str(id),'from': {'username': user.name}}}))
        return Response(status=201)
    elif request.method == 'GET':
        if not auth:
            return Response(status=401)
        user = await User.from_token(db, auth)
        if not user:
            return Response(status=400)
        
        messages = await db.fetch('SELECT * FROM messages ORDER BY id LIMIT 100')
        messages = [[str(m[0]), m[1], m[3]] for m in messages]
        return jsonify(messages)


@app.route('/api/v1/messages/<id>', methods=['DELETE', 'GET'])
async def message(id: int = None):
    try:
        id = int(id)
    except: return Response(status=400)
    auth = request.headers.get('Authorization')
    if not auth: return Response(status=401)
    user = await User.from_token(db, auth)
    if not user: return Response(status=400)
    if request.method == 'DELETE':
        val = await db.fetchval('SELECT userid FROM messages WHERE id = $1', int(id))
        if not val: return Response(status=404)
        if val != user.id: return Response(status=403)
        await db.execute('DELETE FROM messages WHERE id = $1', id)
        for session_id, connection_data in Client.verified_connections.items():
            if connection_data.get('websocket'):
                asyncio.create_task(connection_data['websocket'].send_json({'code': Codes.Event, 'ev': 'MESSAGE_DELETE', 'd': {'id': str(id)}}))
        return Response(status=201)
    elif request.method == 'GET':
        val = await db.fetchrow('SELECT * FROM messages WHERE id = $1', int(id))
        if not val: return Response(status=404)
        return jsonify([str(v) for v in val])


        

@app.route('/register')
async def register():
    return await render_template('register.html')

@app.route('/login')
async def login():
    return await render_template('login.html')

@app.route('/dashboard')
async def dashboard():
    return await render_template('dashboard.html')


async def for_verified():
    while True:        
        await asyncio.sleep(1.5)

@app.before_serving
async def setup():
    await db.start([
        'users(id BIGINT, username VARCHAR(34), password VARCHAR(125))',
        'messages(id BIGINT, content TEXT, userid BIGINT, username VARCHAR(34))'
    ])
    asyncio.create_task(for_verified())

if __name__ == "__main__":
    app.run(debug=True)