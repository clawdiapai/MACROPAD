@echo off
title MacroPad - Unregister Startup App
echo ================================================================
echo   REMOVING MACROPAD BRIDGE FROM WINDOWS STARTUP
echo ================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$StartupPath = [System.Environment]::GetFolderPath('Startup'); " ^
  "$ShortcutPath = Join-Path $StartupPath 'MacroPad Bridge.lnk'; " ^
  "if (Test-Path $ShortcutPath) { Remove-Item $ShortcutPath -Force; Write-Host '[SUCCESS] Startup shortcut removed.' } else { Write-Host '[INFO] No startup shortcut found.' }"

echo.
pause
