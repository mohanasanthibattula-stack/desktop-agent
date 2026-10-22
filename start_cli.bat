@echo off
title Antigravity Desktop Agent (Terminal)
cd /d "%~dp0"
call ".\venv\Scripts\activate.bat"
python main.py
pause
