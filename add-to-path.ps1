$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$target = "$env:USERPROFILE\.codex-switcher"
if ($currentPath -notlike "*$target*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$target", "User")
    Write-Host "Added $target to user PATH."
    Write-Host "Restart your terminal for the change to take effect."
} else {
    Write-Host "Already in PATH."
}
