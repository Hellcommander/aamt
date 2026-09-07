@echo off
REM ============================================================
REM Generate Test Sample Images
REM Creates sample images/models for GUI testing
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\TestSamples"

echo.
echo ============================================================
echo   Generating Test Sample Images
echo ============================================================
echo.
echo Creating sample images for GUI testing...
echo Output: %OUTPUT_DIR%
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

REM Create output directory
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
)

REM Use the dedicated test sample generator
python CreateQuickTestSamples.py --output "%OUTPUT_DIR%" --count 5

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   Test Samples Generated!
    echo ============================================================
    echo.
    echo Sample images and XML created in: %OUTPUT_DIR%
    echo.
    echo You can now test the GUI with these samples.
) else (
    echo.
    echo ============================================================
    echo   Generation Failed
    echo ============================================================
    echo.
    echo Trying fallback method...
    python -c "from PIL import Image; import os; os.makedirs(r'%OUTPUT_DIR%', exist_ok=True); img = Image.new('RGB', (256, 256), color='#1a2a3a'); img.save(r'%OUTPUT_DIR%\test_texture_diffuse.png'); img2 = Image.new('RGB', (256, 256), color='#66ccff'); img2.save(r'%OUTPUT_DIR%\test_texture_emission.png'); img3 = Image.new('RGB', (512, 512), color='#88ffff'); img3.save(r'%OUTPUT_DIR%\test_spritesheet_120_facings.png'); print('Test images created')"
    
    if %ERRORLEVEL% equ 0 (
        echo Fallback images created.
    ) else (
        echo.
        echo ERROR: Could not create test images.
        echo Install Pillow: pip install Pillow
    )
)

pause
endlocal

