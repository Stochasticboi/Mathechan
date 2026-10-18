"""Check the published document set and local links without network access."""

from pathlib import Path
import re
import sys
import tomllib
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '.venv', '.venv-build', 'work', 'build', 'dist', '__pycache__'}
ALLOWED = {'.gitattributes', '.github', '.gitignore', 'MANIFEST.in', 'CHANGELOG.md',
           'CONTRIBUTING.md', 'LICENSE', 'README.md', 'README.en.md',
           'THIRD_PARTY_NOTICES.md', 'docs', 'examples', 'packaging',
           'pyproject.toml', 'scripts', 'src', 'tests'}


def main():
    errors = []
    for path in ROOT.iterdir():
        if path.name not in ALLOWED | SKIP and not path.name.endswith(('.egg-info', '.spec')):
            errors.append(f'Unexpected top-level path: {path.name}')
    required = ('README.md', 'README.en.md', 'LICENSE', 'pyproject.toml',
                'docs/es/objetivos.md', 'docs/en/objectives.md',
                'docs/es/historia.md', 'docs/en/history.md',
                'docs/es/lenguaje.md', 'docs/en/language.md')
    for name in required:
        if not (ROOT / name).is_file():
            errors.append(f'Missing file: {name}')
    documents = [p for p in ROOT.rglob('*.md')
                 if not set(p.relative_to(ROOT).parts) & SKIP]
    for path in documents:
        content = path.read_text(encoding='utf-8')
        if '\ufffd' in content:
            errors.append(f'{path.relative_to(ROOT)}: invalid text encoding')
        for target in re.findall(r'\]\(([^\s)]+)\)', content):
            if '://' in target or target.startswith(('#', 'mailto:')):
                continue
            target = unquote(target.split('#', 1)[0])
            if target and not (path.parent / target).resolve().exists():
                errors.append(f'{path.relative_to(ROOT)}: broken link {target}')
    for path in ROOT.rglob('*.toml'):
        if not set(path.relative_to(ROOT).parts) & SKIP:
            try:
                tomllib.loads(path.read_text(encoding='utf-8'))
            except (ValueError, UnicodeError) as error:
                errors.append(f'{path.relative_to(ROOT)}: {error}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'OK: {len(documents)} documents and local links.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
