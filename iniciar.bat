@echo off
rem Inicia o MechHub no Windows (cria o ambiente na primeira vez).
rem Para abrir sem janela preta, use o atalho criado por criar_atalho.py.
cd /d "%~dp0"
if not exist .venv (
    echo Criando ambiente virtual...
    py -3 -m venv .venv 2>nul || python -m venv .venv || goto erro
    .venv\Scripts\python.exe -m pip install -r requirements.txt || goto erro
    .venv\Scripts\python.exe criar_atalho.py
)
echo Abrindo http://127.0.0.1:5000  (login: demo@mechhub.local / mechhub123)
start "" http://127.0.0.1:5000
.venv\Scripts\python.exe run.py
goto fim
:erro
echo Nao foi possivel preparar o ambiente. Verifique se o Python 3 esta instalado.
pause
:fim
