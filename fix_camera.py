from pathlib import Path

ROOT = Path(__file__).resolve().parent
base = ROOT / 'tracker' / 'templates' / 'tracker' / 'base.html'
dash = ROOT / 'tracker' / 'templates' / 'tracker' / 'dashboard.html'

if not base.exists() or not dash.exists():
    raise SystemExit('ERROR: Extract SmartPresence_Final_Competition.zip first, then run this script from the project root.')

b = base.read_text(encoding='utf-8')
b = b.replace('<script src="/static/tracker/app.js"></script>', '')
base.write_text(b, encoding='utf-8')

d = dash.read_text(encoding='utf-8')
bad = "},'image/jpeg',.78)});setTimeout(scan,850)}"
good = "},'image/jpeg',.78);setTimeout(scan,850)}"
if bad not in d:
    raise SystemExit('ERROR: Expected broken scan() line was not found. No file changed.')
d = d.replace(bad, good)
dash.write_text(d, encoding='utf-8')

print('CAMERA BUTTON FIXED.')
print('Removed the extra JavaScript brace/parenthesis that prevented the entire dashboard script from running.')
print('The existing Start camera button now executes its onclick handler and requests the webcam.')
