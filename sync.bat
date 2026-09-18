@echo off
title Fraiday - Git Auto-Sync
echo ========================================================
echo          Syncing Fraiday Repository with Git
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Git status...
git status

echo.
echo [2/4] Staging changes...
git add .

echo.
echo [3/4] Committing changes...
if "%~1"=="" (
    git commit -m "chore: automated sync for Fraiday %date% %time%"
) else (
    git commit -m "%~1"
)

echo.
echo [4/4] Pushing to remote repository...
git push -u origin main

echo.
echo ========================================================
echo  Git Sync Completed!
echo ========================================================
echo.
pause
