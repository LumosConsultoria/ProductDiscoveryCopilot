@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LOG=%cd%\build_log.txt"
> "%LOG%" echo Product Discovery Copilot V3.3 - Build iniciado
>> "%LOG%" echo Pasta: %cd%
>> "%LOG%" echo Data/hora: %date% %time%
>> "%LOG%" echo.

echo ==========================================
echo Product Discovery Copilot - V3.3
echo ==========================================
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py"
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [ERRO] Python nao foi encontrado.
    >> "%LOG%" echo [ERRO] Nem py nem python foram encontrados no PATH.
    echo Consulte build_log.txt.
    pause
    exit /b 1
)

echo [1/6] Ambiente virtual...
if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv >> "%LOG%" 2>&1
    if errorlevel 1 goto :error
)

echo [2/6] Pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo [3/6] Dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo [4/6] Imports...
".venv\Scripts\python.exe" -c "import tkinter, openai, keyring, sounddevice, numpy" >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo [5/6] Limpando build anterior...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "ProductDiscoveryCopilot.spec" del /q "ProductDiscoveryCopilot.spec"

echo [6/6] Gerando EXE...
".venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name ProductDiscoveryCopilot ^
    --hidden-import=sounddevice ^
    --hidden-import=keyring.backends.Windows ^
    --collect-all=keyring ^
    desktop_app.py >> "%LOG%" 2>&1

if errorlevel 1 goto :error
if not exist "dist\ProductDiscoveryCopilot.exe" goto :error

echo.
echo ==========================================
echo CONCLUIDO COM SUCESSO
echo ==========================================
echo %cd%\dist\ProductDiscoveryCopilot.exe
start "" "%cd%\dist"
pause
exit /b 0

:error
echo.
echo ==========================================
echo BUILD FALHOU
echo ==========================================
echo Consulte:
echo %LOG%
>> "%LOG%" echo [ERRO] Build interrompido. Codigo %errorlevel%
pause
exit /b 1
