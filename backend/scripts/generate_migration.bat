@echo off
if "%~1"=="" (
    echo Error: Migration message required
    echo Usage: scripts\generate_migration.bat "migration message"
    exit /b 1
)

echo Generating migration: %*
pushd %~dp0..

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

alembic revision --autogenerate -m %*

echo Migration generated
echo Review the migration file in migrations\versions\
echo Apply with: alembic upgrade head

popd

