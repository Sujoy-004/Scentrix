# Ralph Loop Orchestration Engine for ScentScape Phase Execution
# Version: 2.0 (Clean-Context Iteration)
# Purpose: Autonomous task execution with state management and git commits

param(
    [string]$Phase = "5.7",
    [int]$MaxIterations = 50,
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

# ============================================================================
# CONFIGURATION
# ============================================================================

$ProjectRoot = "C:\Users\KIIT0001\Downloads\Telegram Desktop\ScentScapeAI\ScentScape"
$ProgressFile = "$ProjectRoot\progress.json"
$ChecklistFile = "$ProjectRoot\RALPH_LOOP_PHASE_$Phase`_CHECKLIST.md"
$LogFile = "$ProjectRoot\ralph-loop-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

function Write-Header {
    param([string]$Text)
    $Border = "=" * 80
    Write-Log $Border
    Write-Log $Text
    Write-Log $Border
}

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

function Get-Progress {
    if (-not (Test-Path $ProgressFile)) {
        Write-Log "Progress file not found. Creating new progress state." "WARN"
        return @{
            current_phase = $Phase
            current_task = "5.$($Phase.Split('.')[1]).1"
            status = "in-progress"
            iteration_count = 0
            last_task_result = "START"
            tasks_completed = @()
            failures = @()
        }
    }
    $content = Get-Content $ProgressFile -Raw | ConvertFrom-Json
    return $content
}

function Set-Progress {
    param([object]$State)
    $State | ConvertTo-Json -Depth 10 | Set-Content $ProgressFile
    Write-Log "Progress state saved." "DEBUG"
}

function Get-NextTask {
    param([object]$Progress)
    
    # Parse checklist to extract task IDs
    if (-not (Test-Path $ChecklistFile)) {
        Write-Log "Checklist file not found: $ChecklistFile" "ERROR"
        return $null
    }
    
    $checklist = Get-Content $ChecklistFile -Raw
    
    # Extract all tasks from format: ## TASK X.X.X: ...
    $taskPattern = "^## TASK (\d+\.\d+\.\d+):"
    $tasks = $checklist | Select-String $taskPattern | ForEach-Object {
        $_.Matches.Groups[1].Value
    }
    
    if ($tasks.Count -eq 0) {
        Write-Log "No tasks found in checklist." "WARN"
        return $null
    }
    
    # Find first incomplete task
    foreach ($task in $tasks) {
        if ($task -notin $Progress.tasks_completed) {
            return $task
        }
    }
    
    Write-Log "All tasks completed!" "INFO"
    return $null
}

# ============================================================================
# GIT OPERATIONS
# ============================================================================

function Test-GitRepo {
    $gitDir = "$ProjectRoot\.git"
    if (-not (Test-Path $gitDir)) {
        Write-Log "Git repository not initialized." "ERROR"
        return $false
    }
    return $true
}

function Get-CurrentBranch {
    Push-Location $ProjectRoot
    try {
        $branch = git branch --show-current 2>$null
        return $branch
    }
    finally {
        Pop-Location
    }
}

function Git-Commit {
    param(
        [string]$TaskId,
        [string]$Message
    )
    
    Push-Location $ProjectRoot
    try {
        git add -A 2>&1 | Out-Null
        $commitMsg = "[phase-$Phase] $TaskId`: $Message"
        git commit -m $commitMsg 2>&1 | Out-Null
        Write-Log "Git commit: $commitMsg" "INFO"
        return $true
    }
    catch {
        Write-Log "Git commit failed: $_" "WARN"
        return $false
    }
    finally {
        Pop-Location
    }
}

# ============================================================================
# TASK EXECUTION
# ============================================================================

function Invoke-BuildCheck {
    Write-Log "Running build check: npm run build" "INFO"
    Push-Location $ProjectRoot\frontend
    try {
        $output = npm run build 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Build successful!" "INFO"
            return $true
        }
        else {
            Write-Log "Build failed: $output" "ERROR"
            return $false
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-LintCheck {
    Write-Log "Running lint check: npm run lint" "INFO"
    Push-Location $ProjectRoot\frontend
    try {
        $output = npm run lint 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Lint check passed." "INFO"
            return $true
        }
        else {
            Write-Log "Lint errors found: $output" "WARN"
            return $false
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-TestCheck {
    Write-Log "Running test check: npm run test:e2e" "INFO"
    Push-Location $ProjectRoot\frontend
    try {
        $output = npm run test:e2e 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "All tests passed!" "INFO"
            return $true
        }
        else {
            Write-Log "Some tests failed." "WARN"
            return $false
        }
    }
    finally {
        Pop-Location
    }
}

function Execute-Task {
    param(
        [string]$TaskId,
        [object]$Progress
    )
    
    Write-Header "EXECUTING TASK: $TaskId"
    
    $startTime = Get-Date
    
    # Log task execution start
    Write-Log "Task execution started at $startTime" "INFO"
    
    # Task-specific execution logic
    $result = @{
        task_id = $TaskId
        status = "pending"
        start_time = $startTime
        end_time = $null
        duration = $null
        result = "pending"
        notes = ""
    }
    
    # Example: Tasks 5.7.1 pre-check
    if ($TaskId -eq "5.7.1") {
        Write-Log "Task 5.7.1: Visual Regression Testing Setup" "INFO"
        Write-Log "Pre-check 1: Verify Playwright installed..." "DEBUG"
        
        Push-Location $ProjectRoot\frontend
        $pw_version = npm list @playwright/test 2>&1 | grep playwright
        Write-Log "Playwright version: $pw_version" "INFO"
        Pop-Location
        
        $result.status = "ready-to-execute"
        $result.notes = "Playwright is installed and ready. Awaiting manual execution of snapshot captures."
    }
    
    # Example: Generic quality gate
    Write-Log "Running quality gates..." "DEBUG"
    $buildOk = Invoke-BuildCheck
    $lintOk = Invoke-LintCheck
    
    if ($buildOk -and $lintOk) {
        $result.status = "quality-gates-pass"
        $result.result = "ready"
    }
    else {
        $result.status = "quality-gates-fail"
        $result.result = "blocked"
    }
    
    $result.end_time = Get-Date
    $result.duration = (New-TimeSpan -Start $startTime -End $result.end_time).TotalSeconds
    
    Write-Log "Task result: $($result.result) (Duration: $($result.duration)s)" "INFO"
    
    return $result
}

# ============================================================================
# RALPH LOOP MAIN ENGINE
# ============================================================================

function Start-RalphLoop {
    Write-Header "RALPH LOOP ORCHESTRATION ENGINE"
    Write-Log "Phase: $Phase" "INFO"
    Write-Log "Dry Run: $DryRun" "INFO"
    Write-Log "Max Iterations: $MaxIterations" "INFO"
    
    # Pre-flight checks
    if (-not (Test-GitRepo)) {
        Write-Log "Git repository check failed. Exiting." "ERROR"
        exit 1
    }
    
    $currentBranch = Get-CurrentBranch
    Write-Log "Current branch: $currentBranch" "INFO"
    
    if ($currentBranch -ne "phase/5-hardening") {
        Write-Log "Warning: Expected branch 'phase/5-hardening', but on '$currentBranch'" "WARN"
    }
    
    # Initialize progress
    $progress = Get-Progress
    $progress.iteration_count = 0
    
    # Ralph Loop iterations
    for ($i = 0; $i -lt $MaxIterations; $i++) {
        $progress.iteration_count++
        Write-Header "RALPH LOOP ITERATION $($progress.iteration_count)"
        
        # Get next task
        $nextTask = Get-NextTask $progress
        
        if ($null -eq $nextTask) {
            Write-Log "All tasks completed. Ralph Loop exiting successfully." "INFO"
            $progress.status = "complete"
            Set-Progress $progress
            break
        }
        
        Write-Log "Next task: $nextTask" "INFO"
        $progress.current_task = $nextTask
        Set-Progress $progress
        
        # Execute task
        $taskResult = Execute-Task $nextTask $progress
        
        # Update progress with result
        $progress.last_task_result = $taskResult.result
        
        if ($taskResult.result -eq "ready" -or $taskResult.result -eq "ready-to-execute") {
            Write-Log "Task $nextTask marked as complete." "INFO"
            $progress.tasks_completed += $nextTask
            
            if (-not $DryRun) {
                # Commit task completion
                Git-Commit $nextTask "Task $nextTask complete"
            }
            else {
                Write-Log "[DRY RUN] Would have committed: [phase-$Phase] $nextTask`: Task $nextTask complete" "INFO"
            }
        }
        elseif ($taskResult.result -eq "blocked") {
            Write-Log "Task $nextTask blocked by quality gates. Pausing loop." "WARN"
            break
        }
        else {
            Write-Log "Task $nextTask result: $($taskResult.result)" "INFO"
        }
        
        Set-Progress $progress
        
        # Small delay between iterations
        Start-Sleep -Seconds 2
    }
    
    Write-Header "RALPH LOOP EXECUTION SUMMARY"
    Write-Log "Total iterations: $($progress.iteration_count)" "INFO"
    Write-Log "Tasks completed: $($progress.tasks_completed.Count)" "INFO"
    Write-Log "Final status: $($progress.status)" "INFO"
    Write-Log "Log file: $LogFile" "INFO"
}

# ============================================================================
# ENTRY POINT
# ============================================================================

try {
    Start-RalphLoop
}
catch {
    Write-Log "Ralph Loop encountered fatal error: $_" "ERROR"
    exit 1
}

Write-Log "Ralph Loop automation complete." "INFO"
