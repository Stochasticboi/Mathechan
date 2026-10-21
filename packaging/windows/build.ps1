[CmdletBinding()]
param([string]$PythonExecutable = '')

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$venvRoot = Join-Path $projectRoot '.venv-build'
$distRoot = Join-Path $projectRoot 'dist'
$buildRoot = Join-Path $projectRoot 'build\windows'
$licenseRoot = Join-Path $buildRoot 'licenses'

if ($env:OS -ne 'Windows_NT') { throw 'Build this executable on Windows.' }
if (Test-Path -LiteralPath $venvRoot) {
    throw '.venv-build already exists. Use a clean checkout for a new build.'
}

Push-Location $projectRoot
try {
    if ($PythonExecutable) {
        & $PythonExecutable -m venv $venvRoot
    }
    else {
        & py -3.12 -m venv $venvRoot
    }
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    $buildPython = Join-Path $venvRoot 'Scripts\python.exe'
    & $buildPython -c "import struct,sys; assert struct.calcsize('P') == 8 and sys.version_info[:2] == (3,12), 'Use 64-bit Python 3.12'"
    if ($LASTEXITCODE -ne 0) { throw 'A 64-bit Python 3.12 installation is required.' }
    & $buildPython -m pip install -r (Join-Path $PSScriptRoot 'requirements-build.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }
    & $buildPython -m pip install --no-deps --no-build-isolation .
    if ($LASTEXITCODE -ne 0) { throw 'Project installation failed.' }
    & $buildPython -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }

    New-Item -ItemType Directory -Path $licenseRoot -Force | Out-Null
    & $buildPython (Join-Path $PSScriptRoot 'collect_licenses.py') $licenseRoot
    if ($LASTEXITCODE -ne 0) { throw 'License collection failed.' }
    Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE') -Destination (Join-Path $licenseRoot 'MATHECHAN-LICENSE.txt')
    & $buildPython -m PyInstaller --noconfirm --clean --onefile --console --name Mathechan `
        --paths (Join-Path $projectRoot 'src') `
        --distpath $distRoot --workpath (Join-Path $buildRoot 'work') --specpath $buildRoot `
        --copy-metadata sympy --copy-metadata mpmath `
        --add-data ('{0}:licenses' -f $licenseRoot) (Join-Path $PSScriptRoot 'launcher.py')
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }

    & $buildPython (Join-Path $PSScriptRoot 'smoke_test.py') (Join-Path $distRoot 'Mathechan.exe') --timeout 60 --scientific --sessions
    if ($LASTEXITCODE -ne 0) { throw 'Executable smoke tests failed.' }
    Copy-Item -LiteralPath $licenseRoot -Destination (Join-Path $distRoot 'licenses') -Recurse -Force
    & $buildPython -m pip list --format=freeze | Set-Content -LiteralPath (Join-Path $distRoot 'build-environment.txt') -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw 'Environment recording failed.' }
    & $buildPython -VV | Add-Content -LiteralPath (Join-Path $distRoot 'build-environment.txt') -Encoding utf8
    Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $distRoot 'Mathechan.exe') |
        Format-List | Out-String | Set-Content -LiteralPath (Join-Path $distRoot 'SHA256.txt') -Encoding utf8
    Write-Output 'Built and smoke-tested dist/Mathechan.exe. Separate clean-Windows validation remains required before publishing.'
}
finally {
    Pop-Location
}
