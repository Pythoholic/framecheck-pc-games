$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
py -m pip install --user pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name FrameCheck --distpath $PSScriptRoot --workpath (Join-Path $PSScriptRoot '.build\work') --specpath (Join-Path $PSScriptRoot '.build') (Join-Path $PSScriptRoot 'FrameCheck.py')
