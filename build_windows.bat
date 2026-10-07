@echo off
setlocal
python -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --name FC26PlaystyleEditor playstyle_tool.py
if errorlevel 1 exit /b 1
echo.
echo Built dist\FC26PlaystyleEditor.exe
endlocal