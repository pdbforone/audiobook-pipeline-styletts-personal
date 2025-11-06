@echo off
echo Testing Phase 3 directly...
cd ..\phase3-chunking
echo.
echo Running Phase 3 with Poetry:
poetry run python src\phase3_chunking\main.py --file_id=test_story --json_path=..\pipeline.json --config=config.yaml
echo.
echo Exit code: %ERRORLEVEL%
pause
