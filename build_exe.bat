@echo off
echo ========================================
echo FS25 Translator - Build Script
echo ========================================

REM Clean old builds
echo Cleaning old builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del *.spec 2>nul

REM Build with PyInstaller
echo.
echo Building EXE with PyInstaller...
echo This may take a few minutes...
echo.

pyinstaller --clean ^
    --onefile ^
    --windowed ^
    --name "FS25_Translator" ^
    --icon="icons/icon.ico" ^
    --add-data "icons/flags;icons/flags" ^
    --add-data "icons/icon.ico;icons" ^
    --hidden-import="keyring.backends.Windows" ^
    --hidden-import="keyring.backends.null" ^
    --hidden-import="deepl" ^
    --hidden-import="googletrans" ^
    --hidden-import="certifi" ^
    --exclude-module="matplotlib" ^
    --exclude-module="numpy" ^
    --exclude-module="pandas" ^
    --exclude-module="scipy" ^
    --exclude-module="tkinter" ^
    --exclude-module="pygame" ^
    --exclude-module="pygame_menu" ^
    fs25_translator.py

REM Check if build succeeded
if not exist "dist\FS25_Translator.exe" (
    echo.
    echo ========================================
    echo ERROR: Build failed!
    echo Check the error messages above.
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo EXE location: dist\FS25_Translator.exe
echo.

REM Show file size
for %%I in ("dist\FS25_Translator.exe") do echo File size: %%~zI bytes

echo.
echo You can now distribute the EXE file.
echo Note: First run may trigger antivirus scan (normal behavior).
echo.
echo ========================================
pause