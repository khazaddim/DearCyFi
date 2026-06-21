# Activate the custom DearCyGui environment and run the demo
# This environment uses your custom DearCyGui branch: integrate/replay-upstream-2026-06-20

Write-Host "Activating custom DearCyGui environment (.venv-dcg)..." -ForegroundColor Cyan
& .\.venv-dcg\Scripts\Activate.ps1

Write-Host "`nRunning DearCyFi demo with custom DearCyGui..." -ForegroundColor Green
Write-Host "Location: $PWD" -ForegroundColor Gray
Write-Host "Python: $(python --version)" -ForegroundColor Gray
Write-Host "DearCyGui: $(python -c 'import dearcygui; print(dearcygui.__version__)')" -ForegroundColor Gray
Write-Host "`n" -ForegroundColor Gray

cd examples\DearCyFi_Demo
python DearCyFi_Demo.py
