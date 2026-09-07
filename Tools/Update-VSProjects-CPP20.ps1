# ============================================================================
# Update-VSProjects-CPP20.ps1
# ============================================================================
# Drag-and-drop PowerShell script to update Visual Studio project files
# (.vcxproj) to use C++20 language standard.
#
# Usage:
#   1. Drag and drop API folder(s) or .vcxproj file(s) onto this script
#   2. Or run: .\Update-VSProjects-CPP20.ps1 -Path "path\to\API\folder"
#
# ============================================================================

param(
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    [string[]]$DroppedItems,
    
    [Parameter(Mandatory=$false)]
    [string]$Path,
    
    [Parameter(Mandatory=$false)]
    [string]$LanguageStandard = "stdcpp20",
    
    [Parameter(Mandatory=$false)]
    [switch]$WhatIf,
    
    [Parameter(Mandatory=$false)]
    [switch]$Recurse = $true
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$Script:Config = @{
    LanguageStandard = $LanguageStandard
    WhatIf = $WhatIf
    Recurse = $Recurse
    FilesUpdated = 0
    FilesSkipped = 0
    ConfigurationsUpdated = 0
    Errors = 0
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

function Write-Status {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    
    $color = switch ($Type) {
        "Info"    { "Cyan" }
        "Success" { "Green" }
        "Warning" { "Yellow" }
        "Error"   { "Red" }
        default   { "White" }
    }
    
    $prefix = switch ($Type) {
        "Info"    { "[*]" }
        "Success" { "[+]" }
        "Warning" { "[!]" }
        "Error"   { "[-]" }
        default   { "[.]" }
    }
    
    Write-Host "$prefix $Message" -ForegroundColor $color
}

function Get-VCXProjFiles {
    param(
        [string[]]$Paths
    )
    
    $files = @()
    
    foreach ($item in $Paths) {
        if (-not $item) { continue }
        
        $resolvedPath = Resolve-Path $item -ErrorAction SilentlyContinue
        if (-not $resolvedPath) {
            Write-Status "Path not found: $item" "Warning"
            continue
        }
        
        $itemPath = $resolvedPath.Path
        
        if (Test-Path $itemPath -PathType Container) {
            # It's a directory - find all .vcxproj files
            Write-Status "Scanning directory: $itemPath" "Info"
            $projFiles = Get-ChildItem -Path $itemPath -Filter "*.vcxproj" -Recurse:$Script:Config.Recurse -File
            $files += $projFiles
        }
        elseif (Test-Path $itemPath -PathType Leaf) {
            # It's a file
            if ($itemPath -like "*.vcxproj") {
                $files += Get-Item $itemPath
            }
            else {
                Write-Status "Skipping non-.vcxproj file: $itemPath" "Warning"
            }
        }
    }
    
    return $files | Select-Object -Unique
}

function Update-VCXProjFile {
    param(
        [string]$FilePath
    )
    
    try {
        # Load the XML file
        [xml]$xmlDoc = Get-Content $FilePath -ErrorAction Stop
        $ns = New-Object System.Xml.XmlNamespaceManager($xmlDoc.NameTable)
        $ns.AddNamespace("msbuild", "http://schemas.microsoft.com/developer/msbuild/2003")
        
        $modified = $false
        $configCount = 0
        
        # Find all ItemDefinitionGroup elements
        # Try with namespace first, then without
        $itemGroups = $xmlDoc.SelectNodes("//msbuild:ItemDefinitionGroup", $ns)
        
        if ($itemGroups.Count -eq 0) {
            # Try without namespace (most .vcxproj files don't use namespace prefixes)
            $itemGroups = $xmlDoc.SelectNodes("//ItemDefinitionGroup")
        }
        
        if ($itemGroups.Count -eq 0) {
            Write-Status "  No ItemDefinitionGroup elements found" "Warning"
            return $false
        }
        
        foreach ($itemGroup in $itemGroups) {
            # Find ClCompile element within this ItemDefinitionGroup
            $clCompile = $itemGroup.ClCompile
            
            if ($null -ne $clCompile) {
                # Check if LanguageStandard already exists
                $existingLangStd = $clCompile.LanguageStandard
                
                if ($null -eq $existingLangStd -or $existingLangStd -ne $Script:Config.LanguageStandard) {
                    # Add or update LanguageStandard
                    if ($null -eq $existingLangStd) {
                        # Create new element
                        # Use the same namespace as the parent, or no namespace if parent has none
                        $namespaceURI = if ($clCompile.NamespaceURI) { $clCompile.NamespaceURI } else { $null }
                        $langStdElement = $xmlDoc.CreateElement("LanguageStandard", $namespaceURI)
                        $langStdElement.InnerText = $Script:Config.LanguageStandard
                        $clCompile.AppendChild($langStdElement) | Out-Null
                        
                        $configCount++
                        $modified = $true
                        
                        $condition = $itemGroup.Condition
                        if ($condition) {
                            Write-Status "  Adding LanguageStandard to configuration: $condition" "Info"
                        }
                        else {
                            Write-Status "  Adding LanguageStandard to default configuration" "Info"
                        }
                    }
                    else {
                        # Update existing element
                        $clCompile.LanguageStandard = $Script:Config.LanguageStandard
                        $configCount++
                        $modified = $true
                        
                        $condition = $itemGroup.Condition
                        if ($condition) {
                            Write-Status "  Updating LanguageStandard in configuration: $condition" "Info"
                        }
                    }
                }
            }
        }
        
        if ($modified) {
            if ($Script:Config.WhatIf) {
                Write-Status "Would update: $FilePath ($configCount configuration(s))" "Info"
                $Script:Config.ConfigurationsUpdated += $configCount
            }
            else {
                # Save the XML file with proper formatting
                $settings = New-Object System.Xml.XmlWriterSettings
                $settings.Indent = $true
                $settings.IndentChars = "  "
                $settings.NewLineChars = "`r`n"
                $settings.Encoding = [System.Text.Encoding]::UTF8
                $settings.OmitXmlDeclaration = $false
                
                $writer = [System.Xml.XmlWriter]::Create($FilePath, $settings)
                $xmlDoc.Save($writer)
                $writer.Close()
                
                Write-Status "Updated: $FilePath ($configCount configuration(s))" "Success"
                $Script:Config.FilesUpdated++
                $Script:Config.ConfigurationsUpdated += $configCount
            }
            return $true
        }
        else {
            Write-Status "Skipped: $FilePath (already has $($Script:Config.LanguageStandard) or no ClCompile found)" "Info"
            $Script:Config.FilesSkipped++
            return $false
        }
    }
    catch {
        Write-Status "Error processing $FilePath : $_" "Error"
        $Script:Config.Errors++
        return $false
    }
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Visual Studio Project C++20 Updater" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Determine input paths - handle drag-and-drop (ValueFromRemainingArguments)
$inputPaths = @()

if ($DroppedItems -and $DroppedItems.Count -gt 0) {
    Write-Status "Processing dropped items..." "Info"
    $inputPaths = $DroppedItems
}
elseif ($Path) {
    Write-Status "Processing specified path: $Path" "Info"
    $inputPaths = @($Path)
}
else {
    Write-Status "No input provided. Drag and drop API folder(s) or .vcxproj file(s) onto the .bat file, or use -Path parameter." "Error"
    Write-Host ""
    Write-Host "Usage examples:" -ForegroundColor Yellow
    Write-Host "  .\Update-VSProjects-CPP20.bat `"D:\games\...\TranscendenceDev-integration-API59`""
    Write-Host "  .\Update-VSProjects-CPP20.ps1 -Path `"D:\games\...\TranscendenceDev-integration-API59`""
    Write-Host "  .\Update-VSProjects-CPP20.bat `"D:\games\...\TranscendenceDev-integration-API59`" -WhatIf"
    Write-Host ""
    exit 1
}

Write-Status "Target C++ standard: $($Script:Config.LanguageStandard)" "Info"
if ($Script:Config.WhatIf) {
    Write-Status "Running in WhatIf mode (no changes will be made)" "Warning"
}
Write-Host ""

# Get all .vcxproj files
$projFiles = Get-VCXProjFiles -Paths $inputPaths

if ($projFiles.Count -eq 0) {
    Write-Status "No .vcxproj files found in the specified paths." "Warning"
    exit 0
}

Write-Status "Found $($projFiles.Count) .vcxproj file(s) to process" "Info"
Write-Host ""

# Process each file
foreach ($file in $projFiles) {
    Write-Status "Processing: $($file.FullName)" "Info"
    Update-VCXProjFile -FilePath $file.FullName
    Write-Host ""
}

# Summary
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Status "Project files found: $($projFiles.Count)" "Info"
Write-Status "Files updated: $($Script:Config.FilesUpdated)" "Success"
Write-Status "Configurations updated: $($Script:Config.ConfigurationsUpdated)" "Success"
Write-Status "Files skipped: $($Script:Config.FilesSkipped)" "Info"
Write-Status "Errors: $($Script:Config.Errors)" $(if ($Script:Config.Errors -gt 0) { "Error" } else { "Info" })
Write-Host ""

if ($Script:Config.WhatIf) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host "  PREVIEW MODE - NO CHANGES WERE MADE" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Status "This was a dry run. To apply changes, run WITHOUT -WhatIf:" "Warning"
    Write-Host ""
    Write-Host "  .\Update-VSProjects-CPP20.bat `"$($inputPaths[0])`"" -ForegroundColor Cyan
    Write-Host ""
}

if (-not $Script:Config.WhatIf -and $Script:Config.FilesUpdated -gt 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  SUCCESS - CHANGES APPLIED!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Status "Updated $($Script:Config.FilesUpdated) project file(s) with C++20 standard" "Success"
    Write-Status "Modified $($Script:Config.ConfigurationsUpdated) configuration(s) total" "Success"
    Write-Host ""
}
elseif (-not $Script:Config.WhatIf -and $Script:Config.FilesUpdated -eq 0) {
    Write-Host ""
    Write-Status "No files were updated. All files may already have C++20 configured." "Info"
    Write-Host ""
}

# Don't prompt for key press - batch file handles pause on error
# This matches the pattern from other scripts (BakeQudTile, SpaceWhaleAssetGenerator, etc.)

