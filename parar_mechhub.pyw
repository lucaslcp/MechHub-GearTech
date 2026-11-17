"""Desliga o servidor do MechHub iniciado por abrir_mechhub.pyw (ou por python run.py)."""
import os
import subprocess
from pathlib import Path

RUN = Path(__file__).resolve().parent / "run.py"

# Encerra apenas os processos Python que estão executando o run.py desta pasta.
subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" |"
     " Where-Object { $_.CommandLine -and $_.CommandLine.Contains($env:MH_RUN) } |"
     " ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
    capture_output=True, env=dict(os.environ, MH_RUN=str(RUN)),
)
