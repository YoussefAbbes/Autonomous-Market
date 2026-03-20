# Agent Workflow

## Purpose
Keep context persistent across new chats by storing project memory in versioned markdown files.

## Files
- `SYSTEM.md`: global operating rules.
- `memory.md`: preferences, project snapshot, current focus, next steps, session log.
- `TASK_BOARD.md`: Now / Next / Later / Blocked.
- `DECISIONS.md`: decision history and rationale.

## Start a New Chat
Run:

```powershell
.\scripts\session-start.ps1
```

Then ask the new agent:
"Read SYSTEM.md, memory.md, TASK_BOARD.md, and DECISIONS.md from this repo and continue from the current focus."

## End a Session
Run:

```powershell
.\scripts\session-end.ps1 -Summary "Implemented X" `
  -NextSteps "Do Y","Do Z" `
  -Decisions "Chose approach A because B" `
  -Now "Current active task" `
  -Next "Queued task" `
  -Later "Future idea" `
  -Blocked "None"
```

## Interactive End Mode
If you only want to be prompted for summary:

```powershell
.\scripts\session-end.ps1 -Interactive
```
