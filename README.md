# IMDb to 2-Minute Video Generator

Automated pipeline: IMDb URL -> script -> voiceover -> visuals -> subtitles -> MP4.

## Quick start (Windows)

1. Install Python from https://www.python.org/downloads/  (tick Add to PATH)
2. Install FFmpeg:  winget install --id Gyan.FFmpeg
3. Double-click:    setup_windows.bat
4. Edit .env and add your API keys
5. Double-click:    run.bat https://www.imdb.com/title/tt0111161/

## Manual usage

    venv\Scripts\activate
    python main.py https://www.imdb.com/title/tt0111161/
    python main.py https://www.imdb.com/title/tt0111161/ --skip-whisper

Output -> output\MovieTitle_ttXXXXXXX\final_video.mp4
