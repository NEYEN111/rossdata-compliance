import os
import secrets
from pathlib import Path
from datetime import timedelta, timezone
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect, CSRFError
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from .models import db

csrf = CSRFProtect()

@event.listens_for(Engine, 'connect')
def sqlite_foreign_keys(connection, _):
    if type(connection).__module__ == 'sqlite3':
        connection.execute('PRAGMA foreign_keys=ON')

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret_path = Path(app.instance_path) / '.secret'
    configured_secret = os.environ.get('SECRET_KEY')
    if not configured_secret and not secret_path.exists():
        secret_path.write_text(secrets.token_hex(32), encoding='utf-8')
    app.config.update(
        SECRET_KEY=configured_secret or secret_path.read_text(encoding='utf-8'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///crossdata.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=4), MAX_CONTENT_LENGTH=2*1024*1024,
        SEED_DEMO=True,
        DEMO_PASSWORD=os.environ.get('DEMO_PASSWORD', 'AndeClass2026!'),
        SHOW_DEMO_CREDENTIALS=os.environ.get('SHOW_DEMO_CREDENTIALS', '1') == '1' and not os.environ.get('DEMO_PASSWORD'),
        DEMO_EPHEMERAL=os.environ.get('DEMO_EPHEMERAL') == '1',
    )
    if test_config:
        app.config.update(test_config)
    if len(app.config['DEMO_PASSWORD']) < 12:
        raise ValueError('DEMO_PASSWORD debe tener al menos 12 caracteres.')
    db.init_app(app)
    csrf.init_app(app)
    from .views import bp
    app.register_blueprint(bp)
    from .enhancements import bp as enhancements_bp
    app.register_blueprint(enhancements_bp)
    from .services import badge_class
    app.jinja_env.filters['badge'] = badge_class
    app.jinja_env.filters['lima'] = lambda dt: dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-5))).strftime('%d/%m/%Y · %H:%M')
    for code in (400, 403, 404, 409, 413, 500):
        app.register_error_handler(code, lambda error: (render_template('error.html', error=error), error.code))
    app.register_error_handler(CSRFError, lambda error: (render_template('error.html', error=error), 400))
    @app.get('/healthz')
    def healthz():
        try:
            db.session.execute(db.text('SELECT 1'))
        except SQLAlchemyError:
            db.session.rollback()
            return {'status': 'unavailable'}, 503
        return {'status': 'ok'}
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Cache-Control'] = 'no-store'
        return response
    with app.app_context():
        db.create_all()
        if app.config['SEED_DEMO']:
            from .seed import seed_demo, seed_interactive_links
            seed_demo()
            seed_interactive_links()
    return app
