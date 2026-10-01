@echo off
cd /d "%~dp0"
python fix_camera.py
if errorlevel 1 pause
