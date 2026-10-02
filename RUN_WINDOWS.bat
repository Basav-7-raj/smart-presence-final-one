@echo off
setlocal
where py >nul 2>nul || (echo Python is not installed. Install Python 3.12 64-bit first.&pause&exit /b 1)
if not exist .venv py -3.12 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python download_models.py
python manage.py migrate
if not exist db.sqlite3 echo.>nul
if not exist tracker\static mkdir tracker\static
python manage.py runserver 127.0.0.1:8000
