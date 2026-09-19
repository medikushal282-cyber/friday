@echo off
title frAIday - Launching Authentication & Public Entry System
echo ========================================================
echo   Starting frAIday Public Entry & Authentication Hub
echo ========================================================
echo.

echo [1/3] Starting Express Auth & Security Gateway (Port 4000)...
start "frAIday Auth Server" /d "%~dp0server" cmd /k "npm run dev"

echo [2/3] Starting Vite React Public Client (Port 5173)...
start "frAIday Public Client" /d "%~dp0client" cmd /k "npm run dev"

echo.
echo [3/3] Opening frAIday Landing Page in your default browser...
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo.
echo ========================================================
echo  frAIday Authentication System is now running!
echo  - Public Entry UI : http://localhost:5173
echo  - Security API    : http://localhost:4000
echo ========================================================
echo.
pause
