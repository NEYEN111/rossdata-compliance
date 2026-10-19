"""Local entry point. The database and demo records are created once."""
import os
from crossdata import create_app
from waitress import serve

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    print(f'CrossData Compliance: http://127.0.0.1:{port}', flush=True)
    serve(app, host=os.environ.get('HOST', '127.0.0.1'), port=port)
