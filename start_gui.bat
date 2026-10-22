@echo off
title Antigravity Desktop Agent
cd /d "%~dp0"
call ".\venv\Scripts\activate.bat"
start "" pythonw gui.py
