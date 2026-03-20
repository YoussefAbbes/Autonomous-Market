param(
    [string]$Root = (Get-Location).Path
)

$files = @(
    "SYSTEM.md",
    "memory.md",
    "TASK_BOARD.md",
    "DECISIONS.md"
)

Write-Host "=== SESSION START BRIEF ==="
Write-Host "Project root: $Root"
Write-Host ""

foreach ($name in $files) {
    $path = Join-Path $Root $name
    if (Test-Path $path) {
        Write-Host "----- $name -----"
        Get-Content -Path $path
        Write-Host ""
    }
    else {
        Write-Host "----- $name -----"
        Write-Host "Missing"
        Write-Host ""
    }
}

Write-Host "=== Suggested first prompt in a new chat ==="
Write-Host "Read SYSTEM.md, memory.md, TASK_BOARD.md, and DECISIONS.md from this repo and continue from the current focus."
