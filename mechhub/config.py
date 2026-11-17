"""Configurações da plataforma MechHub."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"


class Config:
    # Em produção, defina a variável de ambiente MECHHUB_SECRET_KEY.
    SECRET_KEY = os.environ.get("MECHHUB_SECRET_KEY", "mechhub-chave-de-desenvolvimento")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "MECHHUB_DATABASE_URL", f"sqlite:///{(INSTANCE_DIR / 'mechhub.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Cria a organização de demonstração com dados fictícios na primeira execução.
    SEED_DEMO = True
    TESTING = False
