r"""Cria o atalho "MechHub" na Área de Trabalho e no Menu Iniciar (Windows).

Uso:  .venv\Scripts\python.exe criar_atalho.py
Depois é só dar dois cliques no ícone MechHub ou procurar "MechHub" no Iniciar.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ICON = HERE / "mechhub" / "static" / "mechhub.ico"


def make_icon() -> None:
    """Desenha o ícone (quadrado laranja com uma engrenagem branca) com o Pillow."""
    from PIL import Image, ImageDraw

    pts = [(25.5, 16.0), (28.9, 17.5), (28.4, 19.9), (24.7, 19.8), (23.7, 21.6), (25.6, 24.8), (23.8, 26.4),
           (20.8, 24.2), (18.9, 25.0), (18.6, 28.7), (16.2, 29.0), (15.0, 25.5), (13.1, 25.0), (10.6, 27.8),
           (8.5, 26.6), (9.7, 23.1), (8.3, 21.6), (4.7, 22.4), (3.7, 20.2), (6.7, 18.0), (6.5, 16.0), (3.1, 14.5),
           (3.6, 12.1), (7.3, 12.2), (8.3, 10.4), (6.4, 7.2), (8.2, 5.6), (11.2, 7.8), (13.1, 7.0), (13.4, 3.3),
           (15.8, 3.0), (17.0, 6.5), (18.9, 7.0), (21.4, 4.2), (23.5, 5.4), (22.3, 8.9), (23.7, 10.4), (27.3, 9.6),
           (28.3, 11.8), (25.3, 14.0)]
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=56, fill="#e8590c")
    scale, off = size * 0.68 / 32, size * 0.16
    draw.polygon([(off + x * scale, off + y * scale) for x, y in pts], fill="#ffffff")
    c, r = off + 16 * scale, 4.2 * scale
    draw.ellipse((c - r, c - r, c + r, c + r), fill="#e8590c")
    img.save(ICON, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def create_shortcut(folder: str) -> str:
    """Cria MechHub.lnk numa pasta especial do Windows ("Desktop" ou "Programs")."""
    pythonw = HERE / ".venv" / "Scripts" / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable).with_name("pythonw.exe")
    ps = (
        "[Console]::OutputEncoding = [Text.Encoding]::UTF8;"
        "$link = Join-Path ([Environment]::GetFolderPath($env:MH_FOLDER)) 'MechHub.lnk';"
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($link);"
        "$s.TargetPath = $env:MH_TARGET; $s.Arguments = '\"' + $env:MH_SCRIPT + '\"';"
        "$s.WorkingDirectory = $env:MH_DIR; $s.IconLocation = $env:MH_ICON;"
        "$s.Description = 'MechHub - GearTech (abre http://127.0.0.1:5000)'; $s.Save(); $link"
    )
    env = dict(os.environ, MH_FOLDER=folder, MH_TARGET=str(pythonw), MH_SCRIPT=str(HERE / "abrir_mechhub.pyw"),
               MH_DIR=str(HERE), MH_ICON=str(ICON))
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, env=env,
                         capture_output=True, encoding="utf-8")
    return out.stdout.strip()


if __name__ == "__main__":
    if not ICON.exists():
        make_icon()
    for folder in ("Desktop", "Programs"):
        print("Atalho criado:", create_shortcut(folder))
