const Codes = {
    Event: 0,
    Identify: 1,
    Reconnect: 2,
    Reidentify: 3,
    SessionId: 4,
    Hello: 5,
    Error: 101,
    Success: 102,
    Any: 100
};

let cname = null;

async function loadMessages() {
    const token = getCookie('token');

    if (!token) {
        console.error('No token found.');
        return;
    }

    try {
        const response = await fetch('/api/v1/messages/', {
            method: 'GET',
            headers: {
                'Authorization': `${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load messages');
        }

        const messages = await response.json();
        messages.forEach(message => {
            displayMessage(message[0], message[1], message[2]);
        });
    } catch (error) {
        console.error('Failed to load messages', error);
    }
}

async function connectAndCommunicate() {
    const uri = "ws://localhost:5000";
    
    try {
        const websocket = new WebSocket(uri);

        websocket.onopen = () => {
            console.log('WebSocket connection opened');
            loadMessages();
        };

        websocket.onmessage = (event) => {
            const response = JSON.parse(event.data);

            if (response.code === Codes.SessionId) {
                const session_id = response.d.id;
                console.log(`Session ID received: ${session_id}`);

                const identifyPayload = {
                    code: Codes.Identify,
                    d: { token: getCookie('token') }
                };
                websocket.send(JSON.stringify(identifyPayload));
            } 
            else if (response.code === Codes.Reconnect) {
                const reconnectPayload = {
                    code: Codes.Reconnect,
                    d: { token: getCookie('token'), session_id: session_id }
                };
                websocket.send(JSON.stringify(reconnectPayload));
            } 
            else if (response.code === Codes.Event) {
                console.log(`Received event: ${response.ev}`);
                console.log(`Event data: ${JSON.stringify(response.d)}`);
                if (response.ev === "MESSAGE_SENT") {
                    displayMessage(response.d.id, response.d.content, response.d.from.username);
                } else if (response.ev === "MESSAGE_DELETE") {
                    deleteMessage(response.d.id);
                }
            } 
            else if (response.code === Codes.Hello) {
                console.log("Received Hello message");  
            } else if (response.code === Codes.Error) {
                if (response.d.from === Codes.Identify) {
                    console.log(`Failed to identify, message: ${response.d.message}`);
                } else if (response.d.from === Codes.Reconnect) {
                    console.log(`Failed to reconnect, message: ${response.d.message}`);
                }
            } else if (response.code === Codes.Success) {
            } else {
                console.log(`Got unknown code, data: ${JSON.stringify(response)}`);
            }
        };

        websocket.onerror = (error) => {
            console.error(`WebSocket error: ${error.message}`);
        };

        websocket.onclose = () => {
            console.log('WebSocket connection closed');
        };

    } catch (error) {
        console.error(`Error: ${error.message}`);
    }
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

function displayMessage(id, content, username) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    messageElement.setAttribute('data-id', id);
    messageElement.setAttribute('isowner', username === getCookie('username'));
    
    const userElement = document.createElement('strong');
    userElement.textContent = `${username}: `;

    const contentElement = document.createElement('span');
    contentElement.textContent = `${content} (message id: ${id})`;

    messageElement.appendChild(userElement);
    messageElement.appendChild(contentElement);

    const chatContainer = document.getElementById('messages');
    if (chatContainer) {
        chatContainer.appendChild(messageElement);
    } else {
        console.error('Chat container not found');
    }
}

function deleteMessage(id) {
    const message = document.querySelector(`[data-id='${id}']`).remove();
}

function sendMessage() {
    const messageInput = document.getElementById('input-message');
    if (!messageInput) {
        console.error('Send button or message input not found');
        return;
    }

    const message = messageInput.value.trim();
    if (!message) {
        console.error('Message cannot be empty');
        return;
    }

    const token = getCookie('token');

    if (!token) {
        console.error('No token found');
        return;
    }

    fetch('/api/v1/messages/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `${token}`
        },
        body: JSON.stringify({ content: message })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to send message');
        }
        messageInput.value = '';
    })
    .catch(error => {
        console.error('Error sending message:', error);
    });
}

document.getElementById('send-button').addEventListener('click', sendMessage);
document.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});



if (getCookie('token') === null) {window.location.href = '/register'} // Doesnt work

connectAndCommunicate();