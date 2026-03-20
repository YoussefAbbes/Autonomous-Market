param(
    [string]$Root = (Get-Location).Path,
    [string]$Summary,
    [string[]]$NextSteps,
    [string[]]$Decisions,
    [string[]]$Now,
    [string[]]$Next,
    [string[]]$Later,
    [string[]]$Blocked,
    [switch]$Interactive
)

function Set-MarkedSection {
    param(
        [string]$Content,
        [string]$StartMarker,
        [string]$EndMarker,
        [string[]]$Lines
    )

    $escapedStart = [Regex]::Escape($StartMarker)
    $escapedEnd = [Regex]::Escape($EndMarker)
    $replacement = $StartMarker + "`r`n" + (($Lines -join "`r`n")) + "`r`n" + $EndMarker
    return [Regex]::Replace(
        $Content,
        "(?s)$escapedStart.*?$escapedEnd",
        [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacement }
    )
}

function Ensure-ListLines {
    param([string[]]$Items)
    if (-not $Items -or $Items.Count -eq 0) {
        return @("- None.")
    }
    $result = @()
    foreach ($item in $Items) {
        if ([string]::IsNullOrWhiteSpace($item)) { continue }
        if ($item.TrimStart().StartsWith("- ")) {
            $result += $item.Trim()
        }
        else {
            $result += "- $($item.Trim())"
        }
    }
    if ($result.Count -eq 0) { return @("- None.") }
    return $result
}

if ($Interactive -or [string]::IsNullOrWhiteSpace($Summary)) {
    $Summary = Read-Host "Session summary"
}

$memoryPath = Join-Path $Root "memory.md"
$decisionsPath = Join-Path $Root "DECISIONS.md"
$taskBoardPath = Join-Path $Root "TASK_BOARD.md"

if (-not (Test-Path $memoryPath)) { throw "Missing memory.md at $memoryPath" }
if (-not (Test-Path $decisionsPath)) { throw "Missing DECISIONS.md at $decisionsPath" }
if (-not (Test-Path $taskBoardPath)) { throw "Missing TASK_BOARD.md at $taskBoardPath" }

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"

# Update memory session log and optional next steps
$memory = Get-Content -Path $memoryPath -Raw
$sessionLine = "- ${timestamp}: $Summary"

if ($memory -notmatch "<!-- SESSION_LOG_START -->" -or $memory -notmatch "<!-- SESSION_LOG_END -->") {
    throw "memory.md is missing SESSION_LOG markers."
}

$sessionStart = "<!-- SESSION_LOG_START -->"
$sessionEnd = "<!-- SESSION_LOG_END -->"
$sessionMatch = [Regex]::Match($memory, "(?s)" + [Regex]::Escape($sessionStart) + "(.*?)" + [Regex]::Escape($sessionEnd))
$existingSessionBody = $sessionMatch.Groups[1].Value.Trim()
$sessionLines = @()
if (-not [string]::IsNullOrWhiteSpace($existingSessionBody)) {
    $sessionLines += ($existingSessionBody -split "(`r`n|`n|`r)") | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}
$sessionLines += $sessionLine
$memory = Set-MarkedSection -Content $memory -StartMarker $sessionStart -EndMarker $sessionEnd -Lines $sessionLines

if ($NextSteps -and $NextSteps.Count -gt 0) {
    if ($memory -notmatch "<!-- NEXT_STEPS_START -->" -or $memory -notmatch "<!-- NEXT_STEPS_END -->") {
        throw "memory.md is missing NEXT_STEPS markers."
    }
    $memory = Set-MarkedSection `
        -Content $memory `
        -StartMarker "<!-- NEXT_STEPS_START -->" `
        -EndMarker "<!-- NEXT_STEPS_END -->" `
        -Lines (Ensure-ListLines -Items $NextSteps)
}

Set-Content -Path $memoryPath -Value $memory -NoNewline

# Append decisions
if ($Decisions -and $Decisions.Count -gt 0) {
    $decisionLines = @()
    foreach ($d in $Decisions) {
        if ([string]::IsNullOrWhiteSpace($d)) { continue }
        $decisionLines += "- ${timestamp}: $($d.Trim())"
    }
    if ($decisionLines.Count -gt 0) {
        Add-Content -Path $decisionsPath -Value ("`r`n" + ($decisionLines -join "`r`n"))
    }
}

# Optional task board updates
$board = Get-Content -Path $taskBoardPath -Raw
$sectionUpdates = @(
    @{ Items = $Now; Start = "<!-- NOW_START -->"; End = "<!-- NOW_END -->" },
    @{ Items = $Next; Start = "<!-- NEXT_START -->"; End = "<!-- NEXT_END -->" },
    @{ Items = $Later; Start = "<!-- LATER_START -->"; End = "<!-- LATER_END -->" },
    @{ Items = $Blocked; Start = "<!-- BLOCKED_START -->"; End = "<!-- BLOCKED_END -->" }
)

foreach ($update in $sectionUpdates) {
    if ($update.Items -and $update.Items.Count -gt 0) {
        $board = Set-MarkedSection `
            -Content $board `
            -StartMarker $update.Start `
            -EndMarker $update.End `
            -Lines (Ensure-ListLines -Items $update.Items)
    }
}

Set-Content -Path $taskBoardPath -Value $board -NoNewline

Write-Host "Session files updated:"
Write-Host "- $memoryPath"
Write-Host "- $decisionsPath"
Write-Host "- $taskBoardPath"
