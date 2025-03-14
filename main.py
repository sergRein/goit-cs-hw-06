
import mimetypes
import pathlib
import socket
import logging
from urllib.parse import urlparse, unquote_plus
from http.server import HTTPServer, BaseHTTPRequestHandler
from multiprocessing import Process
from datetime import datetime
from pymongo import MongoClient

# 🔹 Конфігурація
URI = "mongodb://mongodb:27017"
BUFFER_SIZE = 1024
HTTP_HOST, HTTP_PORT = '0.0.0.0', 3000
SOCKET_HOST, SOCKET_PORT = '127.0.0.1', 5000

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(processName)s - %(message)s")

client = MongoClient(URI)
db = client.users_db
collection = db.messages

class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        pr_url = urlparse(self.path)
        if pr_url.path == '/message':
            size = self.headers.get("Content-Length")
            data = self.rfile.read(int(size)).decode()

            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SOCKET_HOST, SOCKET_PORT))
            client_socket.sendall(data.encode())
            response = client_socket.recv(BUFFER_SIZE)
            logging.info(f"Server response: {response.decode()}")
            client_socket.close()

            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.send_html_file('error.html', 404)


    def do_GET(self):
        pr_url = urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())


def run_http_server():
    httpd = HTTPServer((HTTP_HOST, HTTP_PORT), HttpHandler)
    logging.info(f"HTTP server started http://{HTTP_HOST}:{HTTP_PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("HTTP server stopped")
        httpd.server_close()


def get_all_messages():
    messages = list(collection.find({}, {"_id": 0})) 
    logging.info(f"All messages from MongoDB:\n{messages}")
    return messages

def save_data_to_db(data):
    parse_data = unquote_plus(data.decode())

    if not parse_data:
        logging.error("Received empty data")
        return

    current_time = datetime.now()
    collected_data = {"date": current_time}

    try:
        parse_data = dict(el.split("=", 1) for el in parse_data.split("&") if "=" in el)
        collected_data.update(parse_data)
        logging.info(f"Saving to MongoDB: {collected_data}")
        collection.insert_one(collected_data)

        #just for debug, sell all stored messages
        get_all_messages()

    except Exception as e:
        logging.error(f"Error saving: {e}")
        

def run_socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((SOCKET_HOST, SOCKET_PORT))
    sock.listen(1)
    logging.info(f"Socket server started {SOCKET_HOST}:{SOCKET_PORT}")

    while True:
        conn, addr = sock.accept()
        data = conn.recv(BUFFER_SIZE)
        logging.info(f"Received message from {addr}: {data.decode()}")
        save_data_to_db(data)
        conn.sendall(b"Data received")



if __name__ == "__main__":
    http_serv = Process(target=run_http_server)
    socket_serv = Process(target=run_socket_server)

    socket_serv.start()
    http_serv.start()

    try:
        http_serv.join()
        socket_serv.join()
    except KeyboardInterrupt:
        logging.info("Stopping servers")
        http_serv.terminate()
        socket_serv.terminate()
        http_serv.join()
        socket_serv.join()
        logging.info("Servers stopped")
