# Lanza la jornada completa de la redaccion de El Hoyformativo (jefe de produccion + agentes) sin abrir VS Code.
# Uso:  powershell -ExecutionPolicy Bypass -File edicion.ps1 [AAAA-MM-DD]
# Usa el Claude Code de la extension de VS Code (la version mas nueva instalada) con la cuenta del usuario.
param([string]$Fecha = (Get-Date -Format "yyyy-MM-dd"))

$raiz = $PSScriptRoot
Set-Location $raiz
$claude = Get-ChildItem "$env:USERPROFILE\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe" |
          Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $claude) { Write-Error "No encuentro claude.exe"; exit 1 }

New-Item -ItemType Directory -Force "dia\$Fecha" | Out-Null
$log = "dia\$Fecha\jornada.log"
"[$(Get-Date -Format s)] Empieza la jornada $Fecha con $($claude.FullName)" | Out-File $log -Encoding utf8
& $claude.FullName -p "/edicion-diaria $Fecha" --output-format text 2>&1 | Out-File $log -Append -Encoding utf8
"[$(Get-Date -Format s)] Fin (codigo $LASTEXITCODE)" | Out-File $log -Append -Encoding utf8
if ($LASTEXITCODE -ne 0) {
    & "$raiz\.venv\Scripts\python.exe" notifica.py $Fecha --error "la jornada termino con error $LASTEXITCODE (ver jornada.log)"
}
