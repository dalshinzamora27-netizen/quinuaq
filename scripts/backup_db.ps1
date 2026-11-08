# backup_db.ps1 — US-017 Respaldo automatico de la base de datos (SQL Server)
#
# Uso:
#   .\scripts\backup_db.ps1 -Servidor "MI-PC\SQLEXPRESS" -Carpeta "D:\respaldos"
#
# Se puede programar con el Programador de tareas de Windows para que corra cada noche.
# Requiere sqlcmd y autenticacion de Windows (-E) con permiso de BACKUP.

param(
    [string]$Servidor   = $(if ($env:QUINUAQ_SQL_SERVER) { $env:QUINUAQ_SQL_SERVER } else { "localhost" }),
    [string]$BaseDatos  = "quinuaq_db",
    [string]$Carpeta    = (Join-Path $PSScriptRoot "..\backups"),
    [int]   $DiasRetencion = 30
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $Carpeta)) {
    New-Item -ItemType Directory -Path $Carpeta | Out-Null
}
$Carpeta    = (Resolve-Path $Carpeta).Path
$fecha      = Get-Date -Format "yyyy-MM-dd_HHmmss"
$archivoBak = Join-Path $Carpeta "${BaseDatos}_$fecha.bak"
$archivoZip = Join-Path $Carpeta "${BaseDatos}_$fecha.zip"

Write-Host "Iniciando backup de $BaseDatos en $Servidor..."

# 1) backup nativo de SQL Server
$query = "BACKUP DATABASE [$BaseDatos] TO DISK = N'$archivoBak' WITH INIT, COMPRESSION;"
sqlcmd -S $Servidor -E -b -Q $query

if ($LASTEXITCODE -ne 0 -or !(Test-Path $archivoBak)) {
    Write-Host "ERROR: no se genero el archivo de backup." -ForegroundColor Red
    exit 1
}
Write-Host "Backup generado: $archivoBak"

# 2) comprimir y conservar solo el .zip
Compress-Archive -Path $archivoBak -DestinationPath $archivoZip -Force
Remove-Item $archivoBak
Write-Host "Comprimido: $archivoZip"

# 3) purgar respaldos antiguos
$limite = (Get-Date).AddDays(-$DiasRetencion)
Get-ChildItem -Path $Carpeta -Filter "${BaseDatos}_*.zip" |
    Where-Object { $_.LastWriteTime -lt $limite } |
    ForEach-Object {
        Write-Host "Eliminando backup antiguo: $($_.Name)"
        Remove-Item $_.FullName
    }

Write-Host "Backup completado correctamente." -ForegroundColor Green
