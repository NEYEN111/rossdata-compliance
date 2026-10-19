import pytest
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash
from crossdata import create_app
from crossdata.models import db, User
from crossdata.seed import seed_demo


def test_health_is_public_and_does_not_expose_data(app):
    response = app.test_client().get('/healthz')
    assert response.status_code == 200
    assert response.json == {'status': 'ok'}
    assert response.headers['Cache-Control'] == 'no-store'


def test_health_reports_database_failure_without_details(app, monkeypatch):
    def fail(*args, **kwargs):
        raise SQLAlchemyError('private database connection details')
    with app.app_context():
        monkeypatch.setattr(db.session, 'execute', fail)
        response = app.test_client().get('/healthz')
        assert response.status_code == 503
        assert response.json == {'status': 'unavailable'}


def test_hosted_credentials_and_secure_session(monkeypatch):
    password = 'Test-hosted-only-2026!'
    monkeypatch.setenv('DEMO_PASSWORD', password)
    monkeypatch.setenv('COOKIE_SECURE', '1')
    monkeypatch.setenv('DEMO_EPHEMERAL', '1')
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://',
                      'SECRET_KEY': 'test-hosted-session-key', 'WTF_CSRF_ENABLED': False})
    client = app.test_client()
    login_page = client.get('/login', base_url='https://example.test')
    assert b'AndeClass2026!' not in login_page.data
    assert password.encode() not in login_page.data
    assert b'perderse al reiniciar' in login_page.data
    assert client.post('/login', base_url='https://example.test',
                       data={'username': 'admin', 'password': 'AndeClass2026!'}).status_code == 401
    response = client.post('/login', base_url='https://example.test',
                           data={'username': 'admin', 'password': password})
    assert response.status_code == 302
    assert '; Secure;' in response.headers['Set-Cookie']
    assert client.get('/simulador', base_url='https://example.test').status_code == 200
    with app.app_context():
        app.config['DEMO_PASSWORD'] = 'Another-test-password!'
        seed_demo()
        assert check_password_hash(User.query.filter_by(username='admin').one().password_hash, password)
        db.session.remove()
        db.drop_all()


def test_rejects_short_deployment_password(monkeypatch):
    monkeypatch.setenv('DEMO_PASSWORD', 'short')
    with pytest.raises(ValueError, match='al menos 12'):
        create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'SECRET_KEY': 'test'})
