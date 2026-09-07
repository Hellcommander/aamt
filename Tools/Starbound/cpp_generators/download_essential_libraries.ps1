# Download essential asset-generation libraries into Transcendence Tools/Starbound.
# Moved from Magi-Tech mod root (download_essential_libraries.ps1).
# Runtime C++ vendor stays in the mod; this tree is for offline generators.

param(
    [string]$TargetDir = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $TargetDir) {
    $TargetDir = Join-Path $scriptDir "vendor"
}

if (!(Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    Write-Host "Created directory: $TargetDir" -ForegroundColor Green
}

# Generation-focused subset (+ rectpack2D used by AtlasAssetFactory / SpritesheetAssembler)
$libraries = @(
    @{ Name = "rectpack2D"; URL = "https://github.com/TeamHypersomnia/rectpack2D.git" },
    @{ Name = "stb"; URL = "https://github.com/nothings/stb.git" },
    @{ Name = "glm"; URL = "https://github.com/g-truc/glm.git" },
    @{ Name = "OpenImageIO"; URL = "https://github.com/AcademySoftwareFoundation/OpenImageIO.git" },
    @{ Name = "OpenEXR"; URL = "https://github.com/AcademySoftwareFoundation/OpenEXR.git" },
    @{ Name = "ozz-animation"; URL = "https://github.com/guillaumeblanc/ozz-animation.git" },
    @{ Name = "FastNoise2"; URL = "https://github.com/Auburn/FastNoise2.git" },
    @{ Name = "OpenMesh"; URL = "https://www.graphics.rwth-aachen.de:9000/OpenMesh/OpenMesh.git" },
    @{ Name = "libigl"; URL = "https://github.com/libigl/libigl.git" }
)

Write-Host "Downloading asset-generation libraries to: $TargetDir" -ForegroundColor Cyan
$successCount = 0
$skipCount = 0
$errorCount = 0

foreach ($lib in $libraries) {
    $Name = $lib.Name
    $URL = $lib.URL
    $LibPath = Join-Path $TargetDir $Name
    Write-Host "Processing $Name..." -ForegroundColor Yellow
    if (Test-Path $LibPath) {
        Write-Host "  Library $Name already exists, skipping..." -ForegroundColor Blue
        $skipCount++
        continue
    }
    try {
        git clone --depth 1 $URL $LibPath 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Successfully cloned $Name" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "  Failed to clone $Name" -ForegroundColor Red
            $errorCount++
        }
    } catch {
        Write-Host "  Error cloning $Name : $($_.Exception.Message)" -ForegroundColor Red
        $errorCount++
    }
}

Write-Host ""
Write-Host "Downloaded: $successCount  Skipped: $skipCount  Errors: $errorCount"
Write-Host "Python packing uses pip rectpack (python_pipeline/requirements.txt) — no clone required."
