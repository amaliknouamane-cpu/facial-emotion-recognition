@echo off
title Emotion Detection System

cd /d C:\Users\pc\Desktop\noa

echo Activation de l'environnement virtuel...
call venv\Scripts\activate

echo Lancement du Backend...
start cmd /k "cd /d C:\Users\pc\Desktop\noa\backend && call ..\venv\Scripts\activate && python server.py"

timeout /t 3 >nul

echo Lancement du Frontend...
start cmd /k "cd /d C:\Users\pc\Desktop\noa && call venv\Scripts\activate && python -m http.server 5500 -d frontend"

echo.
echo ==========================================
echo Le projet est en cours d'execution.
echo Frontend : http://localhost:5500
echo Backend  : http://localhost:5000
echo ==========================================
pause