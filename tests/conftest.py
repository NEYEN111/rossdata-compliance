import pytest
from crossdata import create_app
from crossdata.models import db

@pytest.fixture()
def app():
    app = create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://','WTF_CSRF_ENABLED':False,'SECRET_KEY':'test-only-key'})
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    client = app.test_client()
    client.post('/login',data={'username':'admin','password':'AndeClass2026!'})
    return client
