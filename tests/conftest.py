import pytest

from mechhub import create_app
from mechhub.core.seed import DEMO_EMAIL, DEMO_PASSWORD
from mechhub.extensions import db


@pytest.fixture()
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        "SEED_DEMO": True,  # dados fictícios: organização demo + 4 conjuntos
        "SECRET_KEY": "teste",
    })
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged(client):
    resp = client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert resp.status_code == 302
    return client


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield
