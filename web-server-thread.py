import socket
import configparser
import signal
import sys
import pathlib
import psutil
import datetime
import os
import urllib
import threading

config = configparser.ConfigParser()
config.read(pathlib.Path(__file__).parent.absolute() / "config.ini")

ip = config['server']['SERVER_HOST']
port = int(config['server']['SERVER_PORT'])
base_dir = config['server']['SERVER_BASE_DIR']

def sigint_handler(signum, frame):
    print("Desligando o servidor")
    server_socket.close()
    sys.exit(0)

def list_files(directory="."):

    files = os.listdir(directory)  # lista todos os arquivos e pastas no diretório
   
    # cria uma lista de links para cada arquivo
    file_links = []
    for file in files:
        if os.path.isfile(os.path.join(directory, file)):  # verifica se é um arquivo
            file_links.append('<li><a href="{0}" download>{0}</a></li>'.format(file))

    # cria uma lista de links para cada pasta
    folder_links = []
    for folder in files:
        if os.path.isdir(os.path.join(directory, folder)):  # verifica se é uma pasta
            #folder_path = os.path.join(directory, folder)
            folder_links.append('<li><a href="{0}/">{0}</a></li>'.format(folder))

    # lê o arquivo HTML a partir de um arquivo na pasta
    with open('dirlisting.html', 'r') as f:
        html = f.read()

    # formata o HTML com a lista de links para arquivos e pastas
    html = html.format('\n'.join(file_links), '\n'.join(folder_links))

    # retorna o HTML com a lista de arquivos e pastas
    response = 'HTTP/1.1 200 OK\nContent-Type: text/html\n\n{}'.format(html).encode()
    return response

def handle_client(client_socket, client_address):
    # Imprime o IP do cliente conectado
    print(f"Connected by {client_address}")
    
    # Lê a requisição do cliente
    request = client_socket.recv(1024).decode()
    print(request)

    request_parts = request.split(' ')

    if len(request_parts) < 2:
        # Se a requisição não estiver no formato correto, retorna um erro 400 Bad Request
        response = 'HTTP/1.1 400 Bad Request\n\n400 Bad Request'.encode()
        client_socket.sendall(response)
        client_socket.close()
        return

    # Extrai o método HTTP e o caminho a partir do request_parts
    method, path = request_parts[:2]

    if path == '/header':
            # Retorna o cabeçalho HTTP da requisição do cliente
            response = f"HTTP/1.1 200 OK\n\n{request}".encode()

    elif path == '/hello':
        # Retorna Hello e o IP do cliente
        response = f"HTTP/1.1 200 OK\n\nHello {client_address[0]}!".encode()
    
    elif path == "/info":
        # Obtém informações do sistema
        now = datetime.datetime.now()
        temperature = psutil.sensors_temperatures(fahrenheit=False)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu = psutil.cpu_percent(interval=None, percpu=False)
        user = psutil.users()

        # Formata as informações em uma string
        info = f"Data: {now}\nTemperatura: {temperature}\nUso de memoria: {memory.percent}%\nUso de disco \: {disk.percent}%\nUso de cpu: {cpu}%\nUsuario: {user}"

        # Cria a resposta
        response = f"HTTP/1.1 200 OK\n\n{info}".encode()
    
    elif path == "/" or path == "/home":
        path = "/index.html"
        # Abre o arquivo index.html
        file_path = base_dir + path
        try:
            file = open(file_path, 'rb')
            response_data = file.read()
            file.close()

            # Cria a resposta
            response = 'HTTP/1.1 200 OK\n\n'.encode() + response_data
        except:
            # Se o arquivo não for encontrado, retorna 404 Not Found
            response = 'HTTP/1.1 404 Not Found\n\n404 Not Found'.encode()


    elif path == "/dirlisting":
        response = list_files("./")
        
    else:   
        # Abre o arquivo correspondente à URL
        file_path = base_dir + urllib.parse.unquote(path)

        if not os.path.exists(file_path):
            response = 'HTTP/1.1 404 Not Found\n\n404 Not Found'.encode()

        if os.path.isfile(file_path):
            with open(file_path, "r") as f:
                # código para lidar com arquivos
                try:
                    file = open(file_path, 'rb')
                    response_data = file.read()
                    file.close()
                    # Cria a resposta
                    response = 'HTTP/1.1 200 OK\n\n'.encode() + response_data
                except:
                    # Se o arquivo não for encontrado, retorna 404 Not Found
                    response = 'HTTP/1.1 404 Not Found\n\n404 Not Found'.encode()
                pass
        elif os.path.isdir(file_path):
            # código para lidar com pastas
            response = list_files(directory=file_path)
            pass
        else:
            response = 'HTTP/1.1 404 Not Found\n\n404 Not Found'.encode()

    # Envia a resposta para o cliente
    client_socket.sendall(response)

    # Fecha a conexão com o cliente
    client_socket.close()

def run_server():
    # Para parar o servidor
    print("\nCtrl+C para parar o servidor.\n")

    config = configparser.ConfigParser()
    config.read(pathlib.Path(__file__).parent.absolute() / "config.ini")

    print(f'O servidor está sendo executado em {ip}:{port} e o diretório base é {base_dir}')

    # Cria o socket do servidor
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # permite reutilizar o endereço local do socket em caso de falha ou interrupção
    # do servidor, o que ajuda a prevenir erros ao iniciar o servidor novamente.
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Liga o socket à porta e ao IP especificados
    server_socket.bind((ip, port))

    # Começa a escutar conexões na porta especificada
    server_socket.listen(1)

    # Define o handler para o sinal SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, lambda signum, frame: sigint_handler(signum, frame))

    # Loop principal do servidor
    while True:
        # Aceita uma conexão
        client_socket, client_address = server_socket.accept()

        # Cria uma thread para lidar com o cliente
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

if __name__ == '__main__':
    run_server()
