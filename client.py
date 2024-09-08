import asyncio
import websockets
import json

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

async def connect_and_communicate():
    uri = "ws://localhost:5000"
    try:
        async with websockets.connect(uri) as websocket:
            response = json.loads(await websocket.recv())
            session_id = response['d']['id']
            print(f"Session ID received: {session_id}")

            identify_payload = {
                'code': Codes.Identify,
                'd': {'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNDg3NTUyMjQzMzI3OTYzMTM2In0.rinVOc4MIDZtKvCAHa6qbB4XT8aSspf8RCXgLvlaeqg'}
            }
            await websocket.send(json.dumps(identify_payload))

            while True:
                response = json.loads(await websocket.recv())
                print(f"Received: {response}")
                if response['code'] == Codes.Success and response['d'].get('from') == Codes.Reconnect:
                    print('Reconnected successfully')

                if response['code'] == Codes.Reconnect:
                    reconnect_payload = {
                        'code': Codes.Reconnect,
                        'd': {'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNDg3NTUyMjQzMzI3OTYzMTM2In0.rinVOc4MIDZtKvCAHa6qbB4XT8aSspf8RCXgLvlaeqg', 'session_id': session_id}
                    }
                    await websocket.send(json.dumps(reconnect_payload))

                elif response['code'] == Codes.Event:
                    print(f"Received event: {response['ev']}")
                    print(f"Event data: {response['d']}")

                elif response['code'] == Codes.Hello:
                    print("Received Hello message")

    except Exception as e:
        print(f"Error: {e}")

asyncio.run(connect_and_communicate())
