# Smart Presence — Privacy-Preserving Identity & Presence Intelligence

A local Django competition/demo system using OpenCV YuNet + SFace for multi-face detection and recognition. It does **not** use GPS or continuous location tracking.

## Feature set
- Live multi-face monitoring with recognition boxes, confidence and liveness status
- Unknown-person red alert + browser beep + optional local evidence snapshot
- Basic temporal/motion liveness gate (not certified presentation-attack detection)
- Admin authentication and people management
- Register/re-register/disable/delete profiles
- Presence logging with configurable duplicate window
- Current-presence view and event timeline
- Security events and evidence acknowledgement
- Unknown-event snapshots
- Search/filter people
- Analytics dashboard and 7-day chart
- CSV and PDF daily reports
- Privacy Center
- Data controls + one-click demo-history reset
- Recognition/liveness/alert/camera settings
- Dark responsive operations-console UI
- Django admin at `/django-admin/`

## Windows 11 setup
1. Install Python 3.12 (64-bit).
2. Extract/clone this project.
3. Double-click `RUN_WINDOWS.bat` or run the commands below.
4. Create an admin account when prompted.
5. Open `http://127.0.0.1:8000/`.

### Manual
```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python download_models.py
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The first model download requires internet. After the ONNX files exist, recognition runs locally.

## Models
`download_models.py` downloads OpenCV Zoo YuNet and SFace into `tracker/face_models/`. Models are intentionally ignored by Git; every machine can download them during setup.

## Important security/privacy note
This is an educational/competition prototype. The liveness feature is a lightweight temporal/motion heuristic and should not be described as defeating all photo/video/deepfake presentation attacks. Production deployment should add a dedicated PAD model, encryption at rest, retention policies, role-based permissions, HTTPS and formal privacy/security review.
