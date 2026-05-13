@echo off
if "%1"=="" (
    echo Usage: run.bat ^<imdb_url^>
    echo Example: run.bat https://www.imdb.com/title/tt0111161/
    pause & exit /b 1
)
if not exist venv\Scripts\activate.bat (
    echo [ERROR] Run setup_windows.bat first.
    pause & exit /b 1
)
call venv\Scripts\activate.bat
python main.py %*
pause
