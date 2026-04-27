$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$reportPath = Join-Path $env:TEMP 'pg_reset_report.txt'
if (Test-Path $reportPath) { Remove-Item $reportPath -Force }
function Log([string]$m) { Add-Content -Path $reportPath -Value $m }
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

try {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    Log ("1. Admin check result: IS_ADMIN=" + $isAdmin)
    if (-not $isAdmin) { throw 'Shell is not elevated.' }

    $hbaPath = 'C:\Program Files\PostgreSQL\18\data\pg_hba.conf'
    $psqlPath = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
    $svcName = 'postgresql-x64-18'

    # Step 1
    $txt = Get-Content -Path $hbaPath -Raw
    $txt = $txt -replace 'md5', 'trust'
    $txt = $txt -replace 'scram-sha-256', 'trust'
    [System.IO.File]::WriteAllText($hbaPath, $txt, $utf8NoBom)
    Log '2. Modified pg_hba.conf lines:'
    $hostLines = Select-String -Path $hbaPath -Pattern '^host' | ForEach-Object { $_.Line }
    foreach ($line in $hostLines) { Log $line }

    # Step 2
    try {
        $stop1 = cmd /c "net stop $svcName" 2>&1
        $stop1Code = $LASTEXITCODE
    } catch {
        $stop1 = $_.Exception.Message
        $stop1Code = -1
    }

    try {
        $start1 = cmd /c "net start $svcName" 2>&1
        $start1Code = $LASTEXITCODE
    } catch {
        $start1 = $_.Exception.Message
        $start1Code = -1
    }
    $svc1 = Get-Service $svcName | Select-Object Name,Status | Out-String
    Log '3. Service restart status (first):'
    Log ($stop1 | Out-String).TrimEnd()
    Log ($start1 | Out-String).TrimEnd()
    Log $svc1.TrimEnd()
    if ($start1Code -ne 0 -or (Get-Service $svcName).Status -ne 'Running') {
        throw ("First service restart failed. stopExit=$stop1Code startExit=$start1Code")
    }

    # Step 3
    $login = & $psqlPath -w -U postgres -d postgres -c "\conninfo" 2>&1
    $loginCode = $LASTEXITCODE
    Log '4. psql login success (no password):'
    Log ($login | Out-String).TrimEnd()
    if ($loginCode -ne 0) { throw ("psql no-password login failed. exit=$loginCode") }

    # Step 4
    $alter = & $psqlPath -w -U postgres -d postgres -c "ALTER USER postgres WITH PASSWORD 'postgres123';" 2>&1
    $alterCode = $LASTEXITCODE
    Log '5. ALTER USER result:'
    Log ($alter | Out-String).TrimEnd()
    if ($alterCode -ne 0) { throw ("ALTER USER failed. exit=$alterCode") }

    # Step 5
    $txt2 = Get-Content -Path $hbaPath -Raw
    $txt2 = $txt2 -replace 'trust', 'scram-sha-256'
    [System.IO.File]::WriteAllText($hbaPath, $txt2, $utf8NoBom)

    # Step 6
    try {
        $stop2 = cmd /c "net stop $svcName" 2>&1
        $stop2Code = $LASTEXITCODE
    } catch {
        $stop2 = $_.Exception.Message
        $stop2Code = -1
    }

    try {
        $start2 = cmd /c "net start $svcName" 2>&1
        $start2Code = $LASTEXITCODE
    } catch {
        $start2 = $_.Exception.Message
        $start2Code = -1
    }
    $svc2 = Get-Service $svcName | Select-Object Name,Status | Out-String
    Log '3. Service restart status (second):'
    Log ($stop2 | Out-String).TrimEnd()
    Log ($start2 | Out-String).TrimEnd()
    Log $svc2.TrimEnd()
    if ($start2Code -ne 0 -or (Get-Service $svcName).Status -ne 'Running') {
        throw ("Second service restart failed. stopExit=$stop2Code startExit=$start2Code")
    }

    # Step 7
    $env:PGPASSWORD = 'postgres123'
    $verify = & $psqlPath -U postgres -h localhost -d postgres -c "SELECT 1;" 2>&1
    $verifyCode = $LASTEXITCODE
    $env:PGPASSWORD = ''
    Log '6. Final SELECT 1 result:'
    Log ($verify | Out-String).TrimEnd()
    if ($verifyCode -ne 0) { throw ("Final verification failed. exit=$verifyCode") }

} catch {
    Log ('ERROR: ' + $_.Exception.Message)
    exit 1
}
