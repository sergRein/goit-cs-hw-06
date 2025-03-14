import socket
import threading

HOST = '91.196.55.203'
PORT = 12345

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

def receive_messages():
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break
            print("\n" + message)
        except:
            break

receive_thread = threading.Thread(target=receive_messages)
receive_thread.start()

while True:
    message = input()
    if message.lower() == 'exit':
        break
    client_socket.sendall(message.encode())

client_socket.close()