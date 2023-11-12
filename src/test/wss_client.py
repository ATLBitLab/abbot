import json
import socket


def send_data_to_server(data: str, host="127.0.0.1", port=8080):
    print("send_data_to_server")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print("with socket.socket")
            hostport = (host, port)
            print("hostport", hostport)
            s.connect(hostport)
            print("data.encode()", data.encode())
            s.sendall(data.encode())
            response = s.recv(1024)
            print(f"response: {response}")
            print(f"Received: {response.decode()}")
    except KeyboardInterrupt:
        s.close()


EVENT_CLOSE = [
    json.dumps(
        [
            "EVENT",
            {
                "id": "9eeccf4081494dd634b0ddde4a6abf8e0511514eb213839a8aa6ae03b99034df",
                "pubkey": "15884dadb63453c58d6e9d976996cffaa186dc9e8f82c5da2a368080cafc005b",
                "created_at": 1698699725,
                "kind": 4,
                "tags": [["p", "ea0110bcc29b5fecf70b9898aff07e9b74ae764f673a38a8f95c78fb0a41188c"]],
                "content": "rRf/LawNRB3JmVb6dyBrTg==?iv=rG3shPgYPJ202X8JHRJk4g==",
                "sig": "e07b2500c6a3619631f867e952d4bd8126bd1c11cb89b21201f4d25ee96f7d4d4ae88ec68241bda28f9ef24da89d9449c5d247f48534f06424ef153dc7f70508",
            },
        ]
    ),
]


for ec in EVENT_CLOSE:
    send_data_to_server(ec)
