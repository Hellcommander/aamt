# Download Essential Libraries for Magi-Tech Mech System
# This script downloads only the most critical dependencies

param(
    [string]$TargetDir = "cpp_backend/vendor"
)

# Create target directory if it doesn't exist
if (!(Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force
    Write-Host "Created directory: $TargetDir" -ForegroundColor Green
}

# Define essential libraries with their git URLs
$libraries = @(
    @{ Name = "OpenMesh"; URL = "https://www.graphics.rwth-aachen.de:9000/OpenMesh/OpenMesh.git" },
    @{ Name = "CGAL"; URL = "https://github.com/CGAL/cgal.git" },
    @{ Name = "libigl"; URL = "https://github.com/libigl/libigl.git" },
    @{ Name = "ozz-animation"; URL = "https://github.com/guillaumeblanc/ozz-animation.git" },
    @{ Name = "Bullet"; URL = "https://github.com/bulletphysics/bullet3.git" },
    @{ Name = "FastNoise2"; URL = "https://github.com/Auburn/FastNoise2.git" },
    @{ Name = "stb"; URL = "https://github.com/nothings/stb.git" },
    @{ Name = "glm"; URL = "https://github.com/g-truc/glm.git" },
    @{ Name = "Eigen"; URL = "https://gitlab.com/libeigen/eigen.git" },
    @{ Name = "OpenImageIO"; URL = "https://github.com/AcademySoftwareFoundation/OpenImageIO.git" },
    @{ Name = "OpenEXR"; URL = "https://github.com/AcademySoftwareFoundation/OpenEXR.git" },
    @{ Name = "vcpkg"; URL = "https://github.com/microsoft/vcpkg.git" },
    @{ Name = "conan"; URL = "https://github.com/conan-io/conan.git" }
)

Write-Host "Downloading essential libraries to: $TargetDir" -ForegroundColor Cyan
Write-Host "Total libraries to download: $($libraries.Count)" -ForegroundColor Cyan
Write-Host ""

$successCount = 0
$skipCount = 0
$errorCount = 0

foreach ($lib in $libraries) {
    $Name = $lib.Name
    $URL = $lib.URL
    $LibPath = Join-Path $TargetDir $Name
    
    Write-Host "Processing $Name..." -ForegroundColor Yellow
    
    # Check if library already exists
    if (Test-Path $LibPath) {
        Write-Host "  Library $Name already exists, skipping..." -ForegroundColor Blue
        $skipCount++
        continue
    }
    
    try {
        Write-Host "  Cloning $Name from $URL..." -ForegroundColor White
        
        # Use depth=1 for faster cloning (shallow clone)
        $result = git clone --depth 1 $URL $LibPath 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Successfully cloned $Name" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "  Failed to clone $Name" -ForegroundColor Red
            Write-Host "  Git output: $result" -ForegroundColor Red
            $errorCount++
        }
    }
    catch {
        Write-Host "  Error cloning $Name" -ForegroundColor Red
        Write-Host "  Exception: $($_.Exception.Message)" -ForegroundColor Red
        $errorCount++
    }
    
    Write-Host ""
}

# Summary
Write-Host "Download Summary:" -ForegroundColor Cyan
Write-Host "  Successfully downloaded: $successCount" -ForegroundColor Green
Write-Host "  Skipped (already exists): $skipCount" -ForegroundColor Blue
Write-Host "  Errors: $errorCount" -ForegroundColor Red
Write-Host ""

if ($errorCount -gt 0) {
    Write-Host "Some libraries failed to download. Check the error messages above." -ForegroundColor Yellow
    Write-Host "You may need to manually download these libraries or check their URLs." -ForegroundColor Yellow
} else {
    Write-Host "All libraries downloaded successfully!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Build the libraries using CMake" -ForegroundColor White
Write-Host "2. Update CMakeLists.txt with library paths" -ForegroundColor White
Write-Host "3. Link the libraries in your project" -ForegroundColor White
Write-Host ""
Write-Host "See LIBRARY_SETUP_README.md for detailed building instructions." -ForegroundColor Cyan
