$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "== Nibble Windows build =="

if (-not (Test-Path -LiteralPath "Nibble.py")) {
    throw "Nibble.py was not found."
}

if (-not (Test-Path -LiteralPath "Nibble_background.jpg")) {
    throw "Nibble_background.jpg was not found."
}

if (-not (Test-Path -LiteralPath "chromedriver.exe")) {
    Write-Host "Warning: chromedriver.exe was not found. The packaged app may need to download or configure ChromeDriver on first run."
}

Write-Host "Installing build dependencies..."
python -m pip install -r requirements.txt
python -m pip install pyinstaller

Write-Host "Cleaning old build output..."
if (Test-Path -LiteralPath "build") {
    Remove-Item -LiteralPath "build" -Recurse -Force
}
if (Test-Path -LiteralPath "dist") {
    Remove-Item -LiteralPath "dist" -Recurse -Force
}

$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "Nibble",
    "--add-data", "Nibble_background.jpg;.",
    "--hidden-import", "PIL._tkinter_finder",
    "--collect-data", "undetected_chromedriver"
)

if (Test-Path -LiteralPath "chromedriver.exe") {
    $pyinstallerArgs += @("--add-binary", "chromedriver.exe;.")
}

$pyinstallerArgs += "Nibble.py"

Write-Host "Running PyInstaller..."
python -m PyInstaller @pyinstallerArgs

if (Test-Path -LiteralPath "README.md") {
    Copy-Item -LiteralPath "README.md" -Destination "dist\Nibble\README.md" -Force
}
if (Test-Path -LiteralPath "LICENSE") {
    Copy-Item -LiteralPath "LICENSE" -Destination "dist\Nibble\LICENSE" -Force
}
if (Test-Path -LiteralPath "config.example.json") {
    Copy-Item -LiteralPath "config.example.json" -Destination "dist\Nibble\config.example.json" -Force
}

Write-Host ""
Write-Host "Build finished."
Write-Host "Portable app folder: dist\Nibble"
Write-Host "Send the whole dist\Nibble folder, or zip that folder before sharing."
