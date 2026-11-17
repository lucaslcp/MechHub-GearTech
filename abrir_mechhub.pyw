"""Abre o MechHub com dois cliques (sem janela preta).

1. Se o servidor ainda não estiver ligado, liga-o em segundo plano.
2. Abre o navegador em http://127.0.0.1:5000.

O atalho "MechHub" da Área de Trabalho e do Menu Iniciar aponta para este
arquivo (crie-o com: python criar_atalho.py). O servidor fica ligado até o
computador ser desligado; para desligá-lo antes, use parar_mechhub.pyw.
"""
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST, PORT = "127.0.0.1", 5000
URL = f"http://{HOST}:{PORT}"


def server_running() -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((HOST, PORT)) == 0


def start_server() -> None:
    venv = HERE / ".venv" / "Scripts" / "pythonw.exe"
    exe = venv if venv.exists() else Path(sys.executable)
    (HERE / "instance").mkdir(exist_ok=True)
    log = open(HERE / "instance" / "servidor.log", "a", encoding="utf-8")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen([str(exe), str(HERE / "run.py")], cwd=HERE, stdout=log, stderr=log,
                     stdin=subprocess.DEVNULL, creationflags=flags)
    for _ in range(80):  # espera até 20 s
        if server_running():
            return
        time.sleep(0.25)


if __name__ == "__main__":
    if not server_running():
        start_server()
    webbrowser.open(URL)
