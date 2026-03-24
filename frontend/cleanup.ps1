# Kill old Next.js processes and clean cache
Write-Host "Stopping old Next.js processes..."
Get-Process node | Where-Object { $_.CommandLine -like "*next*" } | ForEach-Object {
    Write-Host "Killing process $($_.Id)..."
    $_ | Stop-Process -Force -ErrorAction SilentlyContinue
}

Write-Host "Clearing Next.js cache..."
Remove-Item -Path .\.next -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path .\node_modules\.cache -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Starting fresh dev server..."
node ".\node_modules\next\dist\bin\next" dev
