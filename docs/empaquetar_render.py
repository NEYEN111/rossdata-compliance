"""Source-only Render package; excludes runtime data, secrets and other archives."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output/compartir/CrossData_Render.zip'
FILES = ['.gitignore', '.python-version', 'render.yaml', 'README.md', 'run.py',
         'requirements.txt', 'requirements-lock.txt', 'iniciar.bat', 'iniciar.ps1']
FOLDERS = ['crossdata', 'docs', 'tests', 'output/pdf']


def package():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in FILES:
            bundle.write(ROOT / name, name)
        for folder in FOLDERS:
            for path in sorted((ROOT / folder).rglob('*')):
                relative = path.relative_to(ROOT)
                if path.is_file() and '__pycache__' not in relative.parts and path.suffix not in {'.pyc', '.pyo', '.db', '.zip', '.log'}:
                    bundle.write(path, relative.as_posix())
    with zipfile.ZipFile(OUTPUT) as bundle:
        assert bundle.testzip() is None
        assert 'render.yaml' in bundle.namelist()
        assert not any(name.startswith(('instance/', '.venv/', '.git/', 'output/compartir/')) for name in bundle.namelist())
    print(f'{OUTPUT}\n{OUTPUT.stat().st_size} bytes; ZIP verificado')


if __name__ == '__main__':
    package()
