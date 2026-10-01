from pathlib import Path

ROOT = Path(__file__).resolve().parent
base = ROOT / 'tracker' / 'templates' / 'tracker' / 'base.html'
dash = ROOT / 'tracker' / 'templates' / 'tracker' / 'dashboard.html'

if not base.exists() or not dash.exists():
    raise SystemExit('ERROR: Extract the SmartPresence project first, then run FIX_CAMERA.bat from the project root.')

b = base.read_text(encoding='utf-8')
b = b.replace('<script src="/static/tracker/app.js"></script>', '')
base.write_text(b, encoding='utf-8')

d = dash.read_text(encoding='utf-8')
old = "'X-CSRFToken:getCookie('csrftoken')'"
new = '"X-CSRFToken":getCookie(\'csrftoken\')'
if old in d:
    d = d.replace(old, new)
else:
    print('INFO: CSRF JavaScript line already fixed or changed.')
dash.write_text(d, encoding='utf-8')
print('Camera fix applied successfully.')
print('Fixed: dashboard JavaScript syntax error and removed stale app.js reference.')
