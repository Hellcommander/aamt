<#
.SYNOPSIS
  Resource Integrity Checker Module
  
.DESCRIPTION
  Validates resource files:
  - Image sizes match declared dimensions
  - Spritesheets have correct frame counts
  - Sound files exist and are valid formats
  - Missing /Resources entries

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
#>

# ============================================================
# RESOURCE INTEGRITY CHECKER
# ============================================================

function Get-ResourceIntegrityIssues {
    param([string[]]$Files)
    
    $issues = [System.Collections.ArrayList]::new()
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        $fileDir = [System.IO.Path]::GetDirectoryName($file)
        $modRoot = Get-ModRootDirectory -FilePath $file
        
        # Check Image resources
        $imageIssues = Get-ImageResourceIssues -Text $text -FileDir $fileDir -ModRoot $modRoot -FilePath $file
        $issues.AddRange($imageIssues)
        
        # Check Sound resources
        $soundIssues = Get-SoundResourceIssues -Text $text -FileDir $fileDir -ModRoot $modRoot -FilePath $file
        $issues.AddRange($soundIssues)
        
        # Check for missing /Resources entries
        $resourceIssues = Get-MissingResourceEntries -Text $text -FileDir $fileDir -ModRoot $modRoot -FilePath $file
        $issues.AddRange($resourceIssues)
    }
    
    return $issues
}

function Get-ImageResourceIssues {
    param(
        [string]$Text,
        [string]$FileDir,
        [string]$ModRoot,
        [string]$FilePath
    )
    
    $issues = [System.Collections.ArrayList]::new()
    
    # Find Image definitions
    $imagePattern = '<Image[^>]+UNID\s*=\s*"([^"]+)"[^>]*>'
    $imageMatches = [regex]::Matches($Text, $imagePattern, [System.Text.RegularExpressions.RegexOptions]::Singleline -bor [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    
    foreach ($m in $imageMatches) {
        $imageTag = $m.Value
        $lineNum = Get-LineNumber -Text $Text -Position $m.Index
        
        # Extract attributes
        $bitmapMatch = [regex]::Match($imageTag, 'bitmap\s*=\s*"([^"]+)"', 'IgnoreCase')
        $bitmaskMatch = [regex]::Match($imageTag, 'bitmask\s*=\s*"([^"]+)"', 'IgnoreCase')
        $widthMatch = [regex]::Match($imageTag, 'imageWidth\s*=\s*"(\d+)"', 'IgnoreCase')
        $heightMatch = [regex]::Match($imageTag, 'imageHeight\s*=\s*"(\d+)"', 'IgnoreCase')
        $frameCountMatch = [regex]::Match($imageTag, 'imageFrameCount\s*=\s*"(\d+)"', 'IgnoreCase')
        $rotationColumnsMatch = [regex]::Match($imageTag, 'rotationColumns\s*=\s*"(\d+)"', 'IgnoreCase')
        
        # Check bitmap file
        if ($bitmapMatch.Success) {
            $bitmapPath = $bitmapMatch.Groups[1].Value
            $fullBitmapPath = Resolve-ResourcePath -ResourcePath $bitmapPath -FileDir $fileDir -ModRoot $modRoot
            
            if (-not (Test-Path $fullBitmapPath)) {
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'MISSING_IMAGE'
                    Severity = 'Error'
                    Message = "Image bitmap file not found: $bitmapPath"
                    ResourceType = 'Image'
                    ResourcePath = $bitmapPath
                })
            }
            else {
                # Check image dimensions if specified
                if ($widthMatch.Success -or $heightMatch.Success) {
                    try {
                        $img = [System.Drawing.Image]::FromFile($fullBitmapPath)
                        $actualWidth = $img.Width
                        $actualHeight = $img.Height
                        $img.Dispose()
                        
                        if ($widthMatch.Success) {
                            $declaredWidth = [int]$widthMatch.Groups[1].Value
                            if ($actualWidth -ne $declaredWidth) {
                                [void]$issues.Add([PSCustomObject]@{
                                    File = $FilePath
                                    Line = $lineNum
                                    Code = 'IMAGE_SIZE_MISMATCH'
                                    Severity = 'Error'
                                    Message = "Image width mismatch: declared $declaredWidth, actual $actualWidth"
                                    ResourceType = 'Image'
                                    ResourcePath = $bitmapPath
                                })
                            }
                        }
                        
                        if ($heightMatch.Success) {
                            $declaredHeight = [int]$heightMatch.Groups[1].Value
                            if ($actualHeight -ne $declaredHeight) {
                                [void]$issues.Add([PSCustomObject]@{
                                    File = $FilePath
                                    Line = $lineNum
                                    Code = 'IMAGE_SIZE_MISMATCH'
                                    Severity = 'Error'
                                    Message = "Image height mismatch: declared $declaredHeight, actual $actualHeight"
                                    ResourceType = 'Image'
                                    ResourcePath = $bitmapPath
                                })
                            }
                        }
                        
                        # Check spritesheet frame count
                        if ($frameCountMatch.Success) {
                            $declaredFrames = [int]$frameCountMatch.Groups[1].Value
                            
                            # Calculate expected frames based on image dimensions
                            if ($rotationColumnsMatch.Success) {
                                $columns = [int]$rotationColumnsMatch.Groups[1].Value
                                $rows = [Math]::Ceiling($declaredFrames / $columns)
                                $expectedWidth = $actualWidth / $columns
                                $expectedHeight = $actualHeight / $rows
                                
                                if ($actualWidth % $columns -ne 0 -or $actualHeight % $rows -ne 0) {
                                    [void]$issues.Add([PSCustomObject]@{
                                        File = $FilePath
                                        Line = $lineNum
                                        Code = 'SPRITESHEET_FRAME_MISMATCH'
                                        Severity = 'Error'
                                        Message = "Spritesheet dimensions don't divide evenly: $actualWidth x $actualHeight with $columns columns"
                                        ResourceType = 'Image'
                                        ResourcePath = $bitmapPath
                                    })
                                }
                            }
                        }
                    }
                    catch {
                        # Couldn't read image - might be invalid format
                        [void]$issues.Add([PSCustomObject]@{
                            File = $FilePath
                            Line = $lineNum
                            Code = 'INVALID_IMAGE_FORMAT'
                            Severity = 'Warning'
                            Message = "Could not read image file (may be invalid format): $bitmapPath"
                            ResourceType = 'Image'
                            ResourcePath = $bitmapPath
                        })
                    }
                }
            }
        }
        
        # Check bitmask file
        if ($bitmaskMatch.Success) {
            $bitmaskPath = $bitmaskMatch.Groups[1].Value
            $fullBitmaskPath = Resolve-ResourcePath -ResourcePath $bitmaskPath -FileDir $fileDir -ModRoot $modRoot
            
            if (-not (Test-Path $fullBitmaskPath)) {
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'MISSING_IMAGE'
                    Severity = 'Warning'
                    Message = "Image bitmask file not found: $bitmaskPath"
                    ResourceType = 'Image'
                    ResourcePath = $bitmaskPath
                })
            }
        }
    }
    
    # Check Image elements in types (imageID references)
    $imageRefPattern = '<Image[^>]+imageID\s*=\s*"([^"]+)"[^>]*>'
    $imageRefMatches = [regex]::Matches($Text, $imageRefPattern, 'IgnoreCase')
    
    foreach ($m in $imageRefMatches) {
        $imageTag = $m.Value
        $lineNum = Get-LineNumber -Text $Text -Position $m.Index
        
        # Extract dimensions
        $widthMatch = [regex]::Match($imageTag, 'imageWidth\s*=\s*"(\d+)"', 'IgnoreCase')
        $heightMatch = [regex]::Match($imageTag, 'imageHeight\s*=\s*"(\d+)"', 'IgnoreCase')
        $xMatch = [regex]::Match($imageTag, 'imageX\s*=\s*"(\d+)"', 'IgnoreCase')
        $yMatch = [regex]::Match($imageTag, 'imageY\s*=\s*"(\d+)"', 'IgnoreCase')
        $frameCountMatch = [regex]::Match($imageTag, 'imageFrameCount\s*=\s*"(\d+)"', 'IgnoreCase')
        
        # Note: Can't validate imageID references without resolving the UNID to actual image
        # But we can check if dimensions are specified
        if ($widthMatch.Success -and $heightMatch.Success) {
            # Dimensions are specified - could validate against source image if we had it
        }
    }
    
    return $issues
}

function Get-SoundResourceIssues {
    param(
        [string]$Text,
        [string]$FileDir,
        [string]$ModRoot,
        [string]$FilePath
    )
    
    $issues = [System.Collections.ArrayList]::new()
    
    # Find Sound definitions (both filename and fileName variants)
    $soundPattern = '<Sound[^>]+(?:filename|fileName)\s*=\s*"([^"]+)"'
    $soundMatches = [regex]::Matches($Text, $soundPattern, 'IgnoreCase')
    
    foreach ($m in $soundMatches) {
        $soundPath = $m.Groups[1].Value
        $lineNum = Get-LineNumber -Text $Text -Position $m.Index
        $fullSoundPath = Resolve-ResourcePath -ResourcePath $soundPath -FileDir $fileDir -ModRoot $modRoot
        
        if (-not (Test-Path $fullSoundPath)) {
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $lineNum
                Code = 'MISSING_SOUND'
                Severity = 'Error'
                Message = "Sound file not found: $soundPath"
                ResourceType = 'Sound'
                ResourcePath = $soundPath
            })
        }
        else {
            # Check file format
            $ext = [System.IO.Path]::GetExtension($fullSoundPath).ToLower()
            $validFormats = @('.wav', '.mp3', '.ogg')
            
            if ($validFormats -notcontains $ext) {
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'INVALID_SOUND_FORMAT'
                    Severity = 'Warning'
                    Message = "Sound file format may not be supported: $ext (expected .wav, .mp3, or .ogg)"
                    ResourceType = 'Sound'
                    ResourcePath = $soundPath
                })
            }
        }
    }
    
    return $issues
}

function Get-MissingResourceEntries {
    param(
        [string]$Text,
        [string]$FileDir,
        [string]$ModRoot,
        [string]$FilePath
    )
    
    $issues = [System.Collections.ArrayList]::new()
    
    # Find references to /Resources paths
    $resourcePattern = '["\']([^"\']*[/\\]Resources[/\\][^"\']+)["\']'
    $resourceMatches = [regex]::Matches($Text, $resourcePattern, 'IgnoreCase')
    
    foreach ($m in $resourceMatches) {
        $resourcePath = $m.Groups[1].Value
        $lineNum = Get-LineNumber -Text $Text -Position $m.Index
        
        # Check if it's a file reference (has extension)
        if ($resourcePath -match '\.(jpg|jpeg|png|bmp|gif|wav|mp3|ogg)$') {
            $fullPath = Resolve-ResourcePath -ResourcePath $resourcePath -FileDir $fileDir -ModRoot $modRoot
            
            if (-not (Test-Path $fullPath)) {
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'MISSING_RESOURCE_ENTRY'
                    Severity = 'Warning'
                    Message = "Resource file referenced but not found: $resourcePath"
                    ResourceType = 'Resource'
                    ResourcePath = $resourcePath
                })
            }
        }
    }
    
    return $issues
}

function Resolve-ResourcePath {
    param(
        [string]$ResourcePath,
        [string]$FileDir,
        [string]$ModRoot
    )
    
    # Normalize path separators
    $resourcePath = $resourcePath -replace '/', [System.IO.Path]::DirectorySeparatorChar
    
    # If absolute path, use as-is
    if ([System.IO.Path]::IsPathRooted($resourcePath)) {
        return $resourcePath
    }
    
    # Try relative to file directory first
    $fullPath = Join-Path $fileDir $resourcePath
    if (Test-Path $fullPath) {
        return $fullPath
    }
    
    # Try relative to mod root
    if ($modRoot) {
        $fullPath = Join-Path $modRoot $resourcePath
        if (Test-Path $fullPath) {
            return $fullPath
        }
    }
    
    # Return what we tried (for error reporting)
    return $fullPath
}

function Get-ModRootDirectory {
    param([string]$FilePath)
    
    $current = [System.IO.DirectoryInfo]::new($FilePath).Parent
    
    while ($current) {
        # Check if this looks like a mod root (has .xml files with TranscendenceExtension/Module)
        $xmlFiles = Get-ChildItem -LiteralPath $current.FullName -Filter '*.xml' -ErrorAction SilentlyContinue
        foreach ($xmlFile in $xmlFiles) {
            $content = Get-Content $xmlFile.FullName -Raw -ErrorAction SilentlyContinue
            if ($content -match '<Transcendence(Extension|Module|Library|Adventure)') {
                return $current.FullName
            }
        }
        
        $current = $current.Parent
    }
    
    return $null
}

function Get-LineNumber {
    param([string]$Text, [int]$Position)
    
    $before = $Text.Substring(0, $Position)
    return ([regex]::Matches($before, "`n")).Count + 1
}

# Export functions
# Functions are available for dot-sourcing

