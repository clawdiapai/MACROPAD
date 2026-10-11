@echo off
title MacroPad - Register Startup App
echo ================================================================
echo   INSTALLING MACROPAD BRIDGE TO WINDOWS STARTUP
echo ================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell; " ^
  "$StartupPath = [System.Environment]::GetFolderPath('Startup'); " ^
  "$ShortcutPath = Join-Path $StartupPath 'MacroPad Bridge.lnk'; " ^
  "$Shortcut = $WshShell.CreateShortcut($ShortcutPath); " ^
  "$Pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source; " ^
  "if (-not $Pythonw) { $Pythonw = (Get-Command python.exe).Source.Replace('python.exe', 'pythonw.exe') }; " ^
  "$Shortcut.TargetPath = $Pythonw; " ^
  "$Shortcut.Arguments = '\"' + (Join-Path '%~dp0' 'macropad_bridge.py') + '\"'; " ^
  "$Shortcut.WorkingDirectory = '%~dp0'; " ^
  "$Shortcut.Description = 'MacroPad Windows PC Audio & Discord Controller Bridge'; " ^
  "$Shortcut.Save(); " ^
  "Write-Host '[SUCCESS] Startup shortcut created at:' $ShortcutPath"

echo.
echo MacroPad Bridge is now registered to start automatically on Windows logon.
echo.
pause
