<#
.SYNOPSIS
    Unity Asset Generator for Caves of Qud Mods
    Generates Unity assets (materials, prefabs, SpringUI) for Qud mods using Unity 6

.DESCRIPTION
    Generates missing Unity assets for Caves of Qud mods using Unity 6 in batch mode.
    Supports materials, prefabs, SpringUI assets, and asset bundle building.
    
    Features:
    - Unity 6 compatible asset generation
    - SpringUI asset creation
    - Material and prefab generation
    - Asset bundle building
    - Progress tracking

.PARAMETER ModPath
    Path to Qud mod directory (must contain Assets folder)

.PARAMETER AssetTypes
    Comma-separated list of asset types to generate (materials, prefabs, springui, bundles)
    Default: all

.PARAMETER ScanOnly
    Only scan for missing assets, don't generate

.PARAMETER UnityPath
    Manual Unity Editor path override

.EXAMPLE
    .\QudUnityAssetGenerator.ps1 -ModPath "C:\QudMods\MyMod" -ScanOnly

.EXAMPLE
    .\QudUnityAssetGenerator.ps1 -ModPath "C:\QudMods\MyMod" -AssetTypes "materials,prefabs"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath,
    
    [string]$AssetTypes = "all",
    
    [switch]$ScanOnly,
    
    [string]$UnityPath = ""
)

$ErrorActionPreference = "Stop"

# ============================================================
# CONFIGURATION & UTILITIES
# ============================================================

# Logging utility
function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("Info", "Warning", "Error", "Success", "Debug")]
        [string]$Level = "Info",
        [switch]$NoNewline
    )
    
    $color = switch ($Level) {
        "Info"    { "Gray" }
        "Warning" { "Yellow" }
        "Error"   { "Red" }
        "Success" { "Green" }
        "Debug"   { "DarkGray" }
        default   { "White" }
    }
    
    $prefix = switch ($Level) {
        "Info"    { "[Info]" }
        "Warning" { "[Warning]" }
        "Error"   { "[Error]" }
        "Success" { "[OK]" }
        "Debug"   { "[Debug]" }
        default   { "" }
    }
    
    if ($NoNewline) {
        Write-Host "$prefix $Message" -ForegroundColor $color -NoNewline
    } else {
        Write-Host "$prefix $Message" -ForegroundColor $color
    }
}

# Validation utility
function Test-ValidPath {
    param([string]$Path, [string]$Description = "Path")
    
    if ([string]::IsNullOrWhiteSpace($Path)) {
        Write-Log "$Description is null or empty" -Level Error
        return $false
    }
    
    if (-not (Test-Path $Path)) {
        Write-Log "$Description does not exist: $Path" -Level Error
        return $false
    }
    
    return $true
}

# Load settings with better error handling
function Get-Settings {
    param([string]$SettingsPath)
    
    if (-not (Test-Path $SettingsPath)) {
        Write-Log "settings.json not found at $SettingsPath" -Level Warning
        return @{
            UnityEditorPath = ""
            UnityProjectPath = ""
            UnityVersion = ""
            GameRoot = ""
        }
    }
    
    try {
        $content = [System.IO.File]::ReadAllText($SettingsPath)
        if ($content.Length -gt 0 -and [int][char]$content[0] -eq 0xFEFF) {
            $content = $content.Substring(1)
        }
        $settings = $content | ConvertFrom-Json -ErrorAction Stop
        
        return @{
            UnityEditorPath = if ($settings.unityEditorPath) { $settings.unityEditorPath } else { "" }
            UnityProjectPath = if ($settings.projectPath) { $settings.projectPath } else { "" }
            UnityVersion = if ($settings.unityVersion) { $settings.unityVersion } else { "" }
            GameRoot = if ($settings.gameRoot) { $settings.gameRoot } else { "" }
        }
    }
    catch {
        Write-Log "Failed to parse settings.json: $_" -Level Error
        return @{
            UnityEditorPath = ""
            UnityProjectPath = ""
            UnityVersion = ""
            GameRoot = ""
        }
    }
}

# Initialize settings from JSON, then override version from the live game binary.
$settingsPath = Join-Path $PSScriptRoot "settings.json"
$script:Settings = Get-Settings -SettingsPath $settingsPath
$script:UnityEditorPath = $script:Settings.UnityEditorPath
$script:UnityProjectPath = $script:Settings.UnityProjectPath

# Shared strict Unity resolver (detect game version; refuse wrong-patch Editors).
$sharedPath = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
Import-Module (Join-Path $sharedPath "UnityVersionResolver.psm1") -Force -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "UnityAssetExport.psm1") -Force -ErrorAction SilentlyContinue

$script:QudGameRoot = if ($env:QUD_GAME_ROOT) {
    $env:QUD_GAME_ROOT
} elseif ($script:Settings.GameRoot) {
    $script:Settings.GameRoot
} else {
    "E:\SteamLibrary\steamapps\common\Caves of Qud"
}
if (Get-Command Resolve-UnityEditorForGame -ErrorAction SilentlyContinue) {
    $resolved = Resolve-UnityEditorForGame -GameRoot $script:QudGameRoot -ManualPath $UnityPath
    if ($resolved.RequiredVersion) {
        $script:Settings.UnityVersion = $resolved.RequiredVersion
        Write-Log "Qud game Unity version: $($resolved.RequiredVersion)" -Level Info
    }
    if ($resolved.EditorExe) {
        $script:UnityEditorPath = $resolved.EditorExe
        Write-Log "Matched Editor: $($resolved.MatchedVersion) ($($resolved.EditorExe))" -Level Info
    } else {
        Write-Log "Matching Editor not installed. $($resolved.InstallHint)" -Level Warning
        $script:UnityEditorPath = ""
    }
}

# Override with manual path only if it matches the live game version
if ($UnityPath) {
    $req = $script:Settings.UnityVersion
    if (-not $req -and (Get-Command Get-GameUnityVersion -ErrorAction SilentlyContinue)) {
        $req = Get-GameUnityVersion -GameRoot $script:QudGameRoot
    }
    if ($req -and (Get-Command Find-MatchingUnityEditor -ErrorAction SilentlyContinue)) {
        $exe = Find-MatchingUnityEditor -RequiredVersion $req -ManualPath $UnityPath
        if ($exe) {
            $script:UnityEditorPath = $exe
            Write-Log "Using manually specified Unity path (validated for $req): $exe" -Level Info
        } else {
            Write-Log "Manual Unity path refused — does not match required $req" -Level Warning
        }
    } elseif (Test-Path $UnityPath) {
        Write-Log "Shared resolver unavailable; using manual Unity path unchecked: $UnityPath" -Level Warning
        $script:UnityEditorPath = $UnityPath
    }
}

# Asset type configurations
$script:AssetConfigs = @{
    "materials" = @{
        Folder = "Materials"
        Extensions = @(".mat")
        Description = "Unity materials for textures"
    }
    "prefabs" = @{
        Folder = "Prefabs"
        Extensions = @(".prefab")
        Description = "Unity prefabs for game objects"
    }
    "springui" = @{
        Folder = "SpringUI"
        Extensions = @(".uxml", ".uss")
        Description = "SpringUI visual elements and stylesheets"
    }
    "bundles" = @{
        Folder = "AssetBundles"
        Extensions = @(".assetbundle")
        Description = "Unity asset bundles"
    }
}

# Progress tracking
$script:Progress = @{
    TotalAssets = 0
    ProcessedAssets = 0
    GeneratedAssets = 0
    SkippedAssets = 0
    FailedAssets = 0
    StartTime = Get-Date
}

# ============================================================
# UNITY INTEGRATION
# ============================================================

function Find-UnityEditor {
    param(
        [string]$ManualPath = "",
        [string]$Version = ""
    )
    # Strict: always prefer live game binary version over stale settings.json.
    $required = $Version
    if (-not $required -and (Get-Command Get-GameUnityVersion -ErrorAction SilentlyContinue)) {
        $required = Get-GameUnityVersion -GameRoot $script:QudGameRoot
    }
    if (-not $required -and $script:Settings -and $script:Settings.UnityVersion) {
        $required = $script:Settings.UnityVersion
        Write-Log "Falling back to settings.json unityVersion=$required (game detect failed)" -Level Warning
    }
    if (-not $required) {
        Write-Log "Could not determine required Unity version for Qud (set gameRoot / install CoQ)." -Level Warning
        return $null
    }

    if (Get-Command Find-MatchingUnityEditor -ErrorAction SilentlyContinue) {
        $exe = Find-MatchingUnityEditor -RequiredVersion $required -ManualPath $ManualPath
        if ($exe) { return $exe }
        Write-Log "Matching Unity Editor for $required not installed under E:\tools\Unity_Editor (or Hub roots)." -Level Warning
        return $null
    }

    # Fallback if Shared module failed to import: only accept exact folder name.
    if ($ManualPath -and (Test-Path $ManualPath)) { return $ManualPath }
    $exact = "E:\tools\Unity_Editor\$required\Editor\Unity.exe"
    if (Test-Path $exact) { return $exact }
    Write-Log "Unity Editor not found for $required. Install via Hub into E:\tools\Unity_Editor\$required\" -Level Warning
    return $null
}

function Invoke-UnityEditorScript {
    param(
        [string]$UnityPath,
        [string]$ProjectPath,
        [string]$MethodName,
        [hashtable]$Parameters = @{},
        [int]$TimeoutSeconds = 300
    )
    
    if (-not $UnityPath -or -not (Test-Path $UnityPath)) {
        Write-Log "Unity editor not found" -Level Warning
        return $false
    }
    
    if (-not (Test-ValidPath -Path $ProjectPath -Description "Project path")) {
        return $false
    }
    
    # Create Unity editor script directory if it doesn't exist
    $editorScriptsDir = Join-Path $ProjectPath "Assets\Editor"
    try {
        if (-not (Test-Path $editorScriptsDir)) {
            New-Item -ItemType Directory -Path $editorScriptsDir -Force -ErrorAction Stop | Out-Null
            Write-Log "Created Editor directory: $editorScriptsDir" -Level Debug
        }
    }
    catch {
        Write-Log "Failed to create Editor directory: $_" -Level Error
        return $false
    }
    
    # Create simple Unity 6 editor script using only built-in APIs
    $scriptContent = @"
using UnityEngine;
using UnityEditor;
using System.IO;

public class QudAssetGeneratorEditor
{
    public static void GenerateAsset()
    {
        string methodName = "$MethodName";
        string projectPath = @"$ProjectPath";
        
        // Parameters
        $($Parameters.GetEnumerator() | ForEach-Object { "string $($_.Key) = `"$($_.Value)`";" })
        
        try
        {
            switch (methodName)
            {
                case "GenerateMaterial":
                    GenerateMaterial(projectPath, $($Parameters.Keys -join ', '));
                    break;
                case "GeneratePrefab":
                    GeneratePrefab(projectPath, $($Parameters.Keys -join ', '));
                    break;
                case "BuildAssetBundles":
                    BuildAssetBundles(projectPath);
                    break;
                case "RefreshAssetDatabase":
                    RefreshAssetDatabase();
                    break;
                default:
                    Debug.LogError(`$"Unknown method: {methodName}");
                    EditorApplication.Exit(1);
                    return;
            }
            
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("Asset generation completed successfully");
            EditorApplication.Exit(0);
        }
        catch (System.Exception e)
        {
            Debug.LogError(`$"Asset generation failed: {e.Message}");
            Debug.LogError(`$"Stack trace: {e.StackTrace}");
            EditorApplication.Exit(1);
        }
    }
    
    static void GenerateMaterial(string projectPath, string systemName, string texturePath, string shaderName)
    {
        string materialPath = `$"Assets/Resources/{systemName}/Materials/{systemName}_Material.mat";
        string fullPath = Path.Combine(projectPath, materialPath);
        string dir = Path.GetDirectoryName(fullPath);
        
        if (!Directory.Exists(dir))
            Directory.CreateDirectory(dir);
        
        Material mat = new Material(Shader.Find(shaderName ?? \"Standard\"));
        
        if (!string.IsNullOrEmpty(texturePath) && File.Exists(texturePath))
        {
            // Convert absolute path to relative asset path
            string relativeTexturePath = texturePath.Replace(projectPath + Path.DirectorySeparatorChar, \"\").Replace(Path.DirectorySeparatorChar, '/');
            if (!relativeTexturePath.StartsWith(\"Assets/\"))
            {
                // Try to find texture in Assets folder
                string textureName = Path.GetFileName(texturePath);
                string[] guids = AssetDatabase.FindAssets(textureName);
                if (guids.Length > 0)
                {
                    relativeTexturePath = AssetDatabase.GUIDToAssetPath(guids[0]);
                }
            }
            
            Texture2D tex = AssetDatabase.LoadAssetAtPath<Texture2D>(relativeTexturePath);
            if (tex != null)
            {
                mat.mainTexture = tex;
                if (mat.HasProperty(\"_MainTex\")) mat.SetTexture(\"_MainTex\", tex);
                Debug.Log(`$"Material assigned texture: {relativeTexturePath}");
            }
            else
            {
                Debug.LogWarning(`$"Texture not found at: {relativeTexturePath}");
            }
        }

        // PBR skins from Shared/pbr_skin_generator (Assets/Resources/Textures/Skins or per-system)
        string stem = System.Text.RegularExpressions.Regex.Replace(systemName, \"[^A-Za-z0-9_]\", \"_\");
        string[] skinDirs = new string[] {
            Path.Combine(projectPath, \"Assets\", \"Resources\", \"Textures\", \"Skins\"),
            Path.Combine(projectPath, \"Assets\", \"Resources\", systemName, \"Textures\", \"Skins\")
        };
        foreach (string skinDir in skinDirs)
        {
            if (!Directory.Exists(skinDir)) continue;
            if (mat.mainTexture == null)
            {
                if (QudTryAssignMap(mat, skinDir, stem + \"_diffuse.png\", \"_MainTex\", false)
                    || QudTryAssignMap(mat, skinDir, \"qud_mod_diffuse.png\", \"_MainTex\", false))
                {
                    if (mat.HasProperty(\"_MainTex\") && mat.GetTexture(\"_MainTex\") != null)
                        mat.mainTexture = mat.GetTexture(\"_MainTex\");
                }
            }
            QudTryAssignMap(mat, skinDir, stem + \"_normal.png\", \"_BumpMap\", true);
            QudTryAssignMap(mat, skinDir, \"qud_mod_normal.png\", \"_BumpMap\", true);
            if (!QudTryAssignMap(mat, skinDir, stem + \"_metallicgloss.png\", \"_MetallicGlossMap\", false)
                && !QudTryAssignMap(mat, skinDir, \"qud_mod_metallicgloss.png\", \"_MetallicGlossMap\", false))
            {
                QudTryAssignMap(mat, skinDir, stem + \"_metallic.png\", \"_MetallicGlossMap\", false);
                QudTryAssignMap(mat, skinDir, \"qud_mod_metallic.png\", \"_MetallicGlossMap\", false);
            }
            QudTryAssignMap(mat, skinDir, stem + \"_emission.png\", \"_EmissionMap\", false);
            QudTryAssignMap(mat, skinDir, \"qud_mod_emission.png\", \"_EmissionMap\", false);
        }
        if (mat.HasProperty(\"_MetallicGlossMap\") && mat.GetTexture(\"_MetallicGlossMap\") != null)
            mat.EnableKeyword(\"_METALLICGLOSSMAP\");
        if (mat.HasProperty(\"_EmissionMap\") && mat.GetTexture(\"_EmissionMap\") != null)
        {
            mat.EnableKeyword(\"_EMISSION\");
            mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
        }
        
        AssetDatabase.CreateAsset(mat, materialPath);
        Debug.Log(`$"Material created: {materialPath}");
    }

    static bool QudTryAssignMap(Material mat, string skinDir, string fileName, string property, bool asNormal)
    {
        string full = Path.Combine(skinDir, fileName);
        if (!File.Exists(full)) return false;
        string[] guids = AssetDatabase.FindAssets(Path.GetFileNameWithoutExtension(fileName));
        Texture2D map = null;
        foreach (string g in guids)
        {
            string p = AssetDatabase.GUIDToAssetPath(g);
            if (p.EndsWith(fileName) || p.Contains(\"/Skins/\"))
            {
                map = AssetDatabase.LoadAssetAtPath<Texture2D>(p);
                if (map != null) break;
            }
        }
        if (map == null) return false;
        if (!mat.HasProperty(property)) return false;
        mat.SetTexture(property, map);
        if (asNormal) mat.EnableKeyword(\"_NORMALMAP\");
        Debug.Log(`$"Material assigned {property}: {fileName}");
        return true;
    }
    
    static void GeneratePrefab(string projectPath, string systemName, string prefabName)
    {
        string prefabFileName = prefabName ?? `$"{systemName}_Prefab";
        string prefabPath = `$"Assets/Resources/{systemName}/Prefabs/{prefabFileName}.prefab";
        string fullPath = Path.Combine(projectPath, prefabPath);
        string dir = Path.GetDirectoryName(fullPath);
        
        if (!Directory.Exists(dir))
            Directory.CreateDirectory(dir);

        AssetDatabase.Refresh();
        string stem = System.Text.RegularExpressions.Regex.Replace(systemName, \"[^A-Za-z0-9_]\", \"_\");
        string[] meshPaths = new string[] {
            `$"Assets/Resources/{systemName}/Meshes/{stem}.fbx",
            `$"Assets/Resources/{systemName}/Meshes/{systemName}.fbx",
            \"Assets/Resources/Meshes/\" + stem + \".fbx\",
            \"Assets/Resources/Meshes/qud_mod.fbx\"
        };

        GameObject go = null;
        string usedMesh = null;
        foreach (string meshPath in meshPaths)
        {
            string abs = Path.Combine(projectPath, meshPath.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(abs))
                continue;
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(meshPath);
            if (model != null)
            {
                go = (GameObject)PrefabUtility.InstantiatePrefab(model);
                if (go != null)
                {
                    go.name = prefabFileName;
                    usedMesh = meshPath;
                    break;
                }
            }
            Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
            if (mesh != null)
            {
                go = new GameObject(prefabFileName);
                MeshFilter mf = go.AddComponent<MeshFilter>();
                mf.sharedMesh = mesh;
                go.AddComponent<MeshRenderer>();
                usedMesh = meshPath;
                break;
            }
        }
        if (go == null)
            go = new GameObject(prefabFileName);

        string matPath = `$"Assets/Resources/{systemName}/Materials/{systemName}_Material.mat";
        Material mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (mat != null)
        {
            Renderer[] renderers = go.GetComponentsInChildren<Renderer>(true);
            foreach (Renderer r in renderers)
                r.sharedMaterial = mat;
        }

        PrefabUtility.SaveAsPrefabAsset(go, prefabPath);
        Object.DestroyImmediate(go);
        if (usedMesh != null)
            Debug.Log(`$"Prefab created with mesh {usedMesh}: {prefabPath}");
        else
            Debug.LogWarning(`$"Prefab created without FBX (empty root): {prefabPath}");
    }
    
    static void BuildAssetBundles(string projectPath)
    {
        string outputPath = Path.Combine(projectPath, "Assets", "AssetBundles");
        if (!Directory.Exists(outputPath))
            Directory.CreateDirectory(outputPath);
        
        BuildPipeline.BuildAssetBundles(
            outputPath,
            BuildAssetBundleOptions.ChunkBasedCompression | BuildAssetBundleOptions.StrictMode,
            BuildTarget.StandaloneWindows64
        );
        
        Debug.Log(`$"Asset bundles built to: {outputPath}");
    }
    
    static void RefreshAssetDatabase()
    {
        AssetDatabase.Refresh();
        Debug.Log(\"Asset database refreshed\");
    }
}
"@
    
    $editorScriptPath = Join-Path $editorScriptsDir "QudAssetGeneratorEditor.cs"
    $enc = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($editorScriptPath, $scriptContent, $enc)
    
    # Generate unique log file name
    $logFile = Join-Path $env:TEMP "qud_unity_gen_$(Get-Date -Format 'yyyyMMdd_HHmmss')_$(Get-Random).log"
    
    try {
        # Single Arguments string — PS 5.1 Start-Process array form breaks spaced paths.
        $quotedProject = '"' + ($ProjectPath -replace '"', '') + '"'
        $quotedLog = '"' + ($logFile -replace '"', '') + '"'
        $argString = "-batchmode -quit -nographics -projectPath $quotedProject -executeMethod QudAssetGeneratorEditor.GenerateAsset -logFile $quotedLog"
        
        Write-Log "Executing Unity: $MethodName (timeout: ${TimeoutSeconds}s)" -Level Debug
        
        # Start process in background job for timeout handling
        $job = Start-Job -ScriptBlock {
            param($UnityPath, $ArgString)
            try {
                $process = Start-Process -FilePath $UnityPath -ArgumentList $ArgString -PassThru -NoNewWindow -Wait -ErrorAction Stop
                return @{
                    ExitCode = $process.ExitCode
                    Success = $true
                }
            }
            catch {
                return @{
                    ExitCode = -1
                    Success = $false
                    Error = $_.Exception.Message
                }
            }
        } -ArgumentList $UnityPath, $argString
        
        # Wait for job with timeout
        $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds
        if ($completed) {
            $result = Receive-Job -Job $job
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
            
            if (-not $result.Success) {
                Write-Log "Unity process failed to start: $($result.Error)" -Level Error
                return $false
            }
            
            $process = [PSCustomObject]@{ ExitCode = $result.ExitCode }
        } else {
            # Timeout occurred
            Write-Log "Unity execution timed out after $TimeoutSeconds seconds" -Level Warning
            Stop-Job -Job $job -ErrorAction SilentlyContinue
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
            
            # Try to kill Unity processes
            try {
                Get-Process -Name "Unity" -ErrorAction SilentlyContinue | 
                    Where-Object { $_.Path -like "*Unity.exe*" } | 
                    Stop-Process -Force -ErrorAction SilentlyContinue
            }
            catch {
                Write-Log "Failed to stop Unity processes: $_" -Level Debug
            }
            
            return $false
        }
        
        # Check Unity log for errors
        if (Test-Path $logFile) {
            try {
                $logContent = Get-Content $logFile -Raw -ErrorAction Stop
                $logLines = Get-Content $logFile -ErrorAction Stop
                
                # Check for fatal errors
                $errorPatterns = @(
                    "fatal error",
                    "Aborting batchmode",
                    "Exception:",
                    "Error:",
                    "Scripts have compiler errors",
                    "Compilation failed"
                )
                
                $hasError = $false
                foreach ($pattern in $errorPatterns) {
                    if ($logContent -match $pattern) {
                        $hasError = $true
                        break
                    }
                }
                
                if ($hasError) {
                    Write-Log "Unity reported errors:" -Level Error
                    
                    # Extract relevant error lines
                    $errorLines = $logLines | 
                        Select-String -Pattern "error|Error|ERROR|Exception|fatal|Aborting|compiler|Compilation" -Context 0,2 |
                        Select-Object -Last 15
                    
                    foreach ($match in $errorLines) {
                        Write-Log "  $($match.Line)" -Level Error
                        if ($match.Context.PostContext) {
                            foreach ($contextLine in $match.Context.PostContext) {
                                if ($contextLine.Trim()) {
                                    Write-Log "    $contextLine" -Level Debug
                                }
                            }
                        }
                    }
                    
                    if ($logContent -match "Scripts have compiler errors|Compilation failed") {
                        Write-Log "Unity project has compilation errors. Fix errors in Unity Editor first." -Level Warning
                    }
                    
                    Write-Log "Full Unity log: $logFile" -Level Info
                    return $false
                }
                
                # Check for success indicators
                $successPatterns = @(
                    "Asset created",
                    "Material created",
                    "Prefab created",
                    "completed successfully",
                    "Asset database refreshed"
                )
                
                $hasSuccess = $false
                foreach ($pattern in $successPatterns) {
                    if ($logContent -match $pattern) {
                        $hasSuccess = $true
                        break
                    }
                }
                
                if ($process.ExitCode -eq 0 -and $hasSuccess) {
                    # Clean up log file on success
                    try {
                        Remove-Item $logFile -Force -ErrorAction SilentlyContinue
                    }
                    catch {
                        Write-Log "Failed to remove log file: $_" -Level Debug
                    }
                    return $true
                }
            }
            catch {
                Write-Log "Failed to read Unity log file: $_" -Level Warning
            }
        }
        
        if ($process.ExitCode -ne 0) {
            Write-Log "Unity exited with code: $($process.ExitCode)" -Level Warning
            if (Test-Path $logFile) {
                Write-Log "Check Unity log: $logFile" -Level Info
                try {
                    $logLines = Get-Content $logFile -Tail 10 -ErrorAction Stop
                    Write-Log "Log snippet:" -Level Info
                    $logLines | ForEach-Object { Write-Log "  $_" -Level Debug }
                }
                catch {
                    Write-Log "Could not read log file: $_" -Level Debug
                }
            }
            return $false
        }
    }
    catch {
        Write-Log "Unity execution failed: $_" -Level Error
        return $false
    }
    finally {
        # Cleanup: remove log file if it still exists and execution failed
        if (Test-Path $logFile) {
            try {
                # Keep log file for debugging if there was an error
                $logAge = (Get-Date) - (Get-Item $logFile).LastWriteTime
                if ($logAge.TotalDays -gt 7) {
                    Remove-Item $logFile -Force -ErrorAction SilentlyContinue
                }
            }
            catch {
                # Ignore cleanup errors
            }
        }
    }
    
    return $false
}

function Generate-UnityMaterial {
    param(
        [string]$ProjectPath,
        [string]$SystemName,
        [string]$TexturePath = "",
        [string]$ShaderName = "Standard",
        [string]$UnityPath = ""
    )
    
    if (-not (Test-ValidPath -Path $ProjectPath -Description "Project path")) {
        return $false
    }
    
    $unityPath = Find-UnityEditor -ManualPath $UnityPath
    if (-not $unityPath) {
        Write-Log "Unity not found, skipping material generation" -Level Warning
        return $false
    }
    
    try {
        return Invoke-UnityEditorScript -UnityPath $unityPath -ProjectPath $ProjectPath `
            -MethodName "GenerateMaterial" `
            -Parameters @{
                systemName = $SystemName
                texturePath = $TexturePath
                shaderName = $ShaderName
            }
    }
    catch {
        Write-Log "Material generation failed: $_" -Level Error
        return $false
    }
}

function Generate-UnityPrefab {
    param(
        [string]$ProjectPath,
        [string]$SystemName,
        [string]$PrefabName,
        [string]$UnityPath = ""
    )
    
    if (-not (Test-ValidPath -Path $ProjectPath -Description "Project path")) {
        return $false
    }
    
    if ([string]::IsNullOrWhiteSpace($PrefabName)) {
        Write-Log "Prefab name is required" -Level Error
        return $false
    }
    
    $unityPath = Find-UnityEditor -ManualPath $UnityPath
    if (-not $unityPath) {
        Write-Log "Unity not found, skipping prefab generation" -Level Warning
        return $false
    }
    
    try {
        return Invoke-UnityEditorScript -UnityPath $unityPath -ProjectPath $ProjectPath `
            -MethodName "GeneratePrefab" `
            -Parameters @{
                systemName = $SystemName
                prefabName = $PrefabName
            }
    }
    catch {
        Write-Log "Prefab generation failed: $_" -Level Error
        return $false
    }
}

function Build-UnityAssetBundles {
    param(
        [string]$ProjectPath,
        [string]$UnityPath = ""
    )
    
    if (-not (Test-ValidPath -Path $ProjectPath -Description "Project path")) {
        return $false
    }

    # Prefer Shared labeled builder (assigns Assets/Resources textures to aamt_resources).
    if (Get-Command Invoke-AamtUnityAssetBundles -ErrorAction SilentlyContinue) {
        Write-Log "Building asset bundles via Shared Invoke-AamtUnityAssetBundles..." -Level Info
        return [bool](Invoke-AamtUnityAssetBundles `
            -ProjectPath $ProjectPath `
            -GameRoot $script:QudGameRoot `
            -ManualUnityPath $UnityPath `
            -EnsureProject `
            -TimeoutSeconds 600)
    }
    
    $unityPath = Find-UnityEditor -ManualPath $UnityPath
    if (-not $unityPath) {
        Write-Log "Unity not found, cannot build asset bundles" -Level Warning
        return $false
    }
    
    Write-Log "Building asset bundles (legacy inline editor script)..." -Level Info
    try {
        return Invoke-UnityEditorScript -UnityPath $unityPath -ProjectPath $ProjectPath `
            -MethodName "BuildAssetBundles" `
            -Parameters @{} `
            -TimeoutSeconds 600
    }
    catch {
        Write-Log "Asset bundle build failed: $_" -Level Error
        return $false
    }
}

# ============================================================
# ASSET SCANNING
# ============================================================

function Find-MissingAssets {
    param(
        [string]$ModPath,
        [string]$AssetType
    )
    
    if (-not (Test-ValidPath -Path $ModPath -Description "Mod path")) {
        return @()
    }
    
    $config = $script:AssetConfigs[$AssetType]
    if (-not $config) {
        Write-Log "Unknown asset type: $AssetType" -Level Warning
        return @()
    }
    
    $assetsPath = Join-Path $ModPath "Assets"
    if (-not (Test-Path $assetsPath)) {
        return @(@{
            Type = $AssetType
            Path = $assetsPath
            Reason = "Assets folder missing"
        })
    }
    
    $missingAssets = @()
    $targetFolder = Join-Path $assetsPath $config.Folder
    
    try {
        if (-not (Test-Path $targetFolder)) {
            $missingAssets += @{
                Type = $AssetType
                Path = $targetFolder
                Reason = "Folder missing"
            }
        } else {
            # Check for placeholder or missing assets
            $files = Get-ChildItem -Path $targetFolder -Recurse -File -ErrorAction SilentlyContinue | 
                Where-Object { $config.Extensions -contains $_.Extension }
            
            if ($null -eq $files -or $files.Count -eq 0) {
                $missingAssets += @{
                    Type = $AssetType
                    Path = $targetFolder
                    Reason = "No assets found"
                }
            }
        }
    }
    catch {
        Write-Log "Error scanning for $AssetType assets: $_" -Level Warning
    }
    
    return $missingAssets
}

function Find-OldUIElements {
    param(
        [string]$ModPath
    )
    
    $oldUIElements = @()
    
    # Look for old UI formats in various locations
    $searchPaths = @(
        Join-Path $ModPath "UI",
        Join-Path $ModPath "Assets\UI",
        Join-Path $ModPath "Assets\Resources\UI",
        Join-Path $ModPath "Scripts",
        Join-Path $ModPath "Assets\Scripts"
    )
    
    foreach ($searchPath in $searchPaths) {
        if (-not (Test-Path $searchPath)) { continue }
        
        # Look for old UI XML files
        $xmlFiles = Get-ChildItem -Path $searchPath -Recurse -Filter "*.xml" -ErrorAction SilentlyContinue | Where-Object {
            $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
            if ($content) {
                # Check for old UI patterns
                $content -match "UIElement|UIPanel|UIButton|LegacyUI|OldUI|IMGUI|OnGUI" -or
                ($content -match "Rect\(|GUILayout|GUI\." -and $content -notmatch "SpringUI")
            }
        }
        
        foreach ($xmlFile in $xmlFiles) {
            $uiName = [System.IO.Path]::GetFileNameWithoutExtension($xmlFile.Name)
            $oldUIElements += @{
                Name = $uiName
                Path = $xmlFile.FullName
                Type = "XML"
                Source = "Old XML UI"
            }
        }
        
        # Look for C# files with QupKit (old UI framework) or IMGUI code
        $csFiles = Get-ChildItem -Path $searchPath -Recurse -Filter "*.cs" -ErrorAction SilentlyContinue | Where-Object {
            $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
            if ($content) {
                # Check for QupKit patterns (BaseView, BaseControl, PanelControl, ButtonControl, etc.)
                ($content -match "QupKit\.|BaseView|BaseControl|PanelControl|ButtonControl|LegacyViewManager" -or
                 $content -match "OnGUI\(\)|IMGUI|GUILayout|GUI\." -or 
                 $content -match "Rect\(.*\)|Window\(|Button\(|Label\(") -and
                $content -notmatch "SpringUI|UIElements|UXML|USS|using.*SpringUI"
            }
        }
        
        foreach ($csFile in $csFiles) {
            $uiName = [System.IO.Path]::GetFileNameWithoutExtension($csFile.Name)
            $content = Get-Content $csFile.FullName -Raw
            $sourceType = "Old C# UI Code"
            
            # Extract UI class/component name
            if ($content -match "class\s+(\w+).*BaseView|class\s+(\w+).*extends.*BaseView") {
                $className = if ($Matches[1]) { $Matches[1] } else { $Matches[2] }
                if ($className) {
                    $uiName = $className
                    $sourceType = "QupKit BaseView"
                }
            } elseif ($content -match "class\s+(\w+).*OnGUI|class\s+(\w+).*Window") {
                $className = if ($Matches[1]) { $Matches[1] } else { $Matches[2] }
                if ($className -and $className -ne $uiName) {
                    $uiName = $className
                }
            }
            
            # Check if it's QupKit specifically
            if ($content -match "QupKit\.|BaseView|BaseControl|PanelControl|ButtonControl") {
                $sourceType = "QupKit UI"
            } elseif ($content -match "OnGUI\(\)") {
                $sourceType = "IMGUI/OnGUI"
            }
            
            $oldUIElements += @{
                Name = $uiName
                Path = $csFile.FullName
                Type = "CSharp"
                Source = $sourceType
            }
        }
    }
    
    return $oldUIElements
}

function Convert-OldUIToSpringUI {
    param(
        [hashtable]$OldUIElement,
        [string]$ModPath
    )
    
    $uiName = $OldUIElement.Name
    $sourcePath = $OldUIElement.Path
    $uiType = $OldUIElement.Type
    
    Write-Log "Converting $uiName from $($OldUIElement.Source) to SpringUI..." -Level Info
    
    # Create SpringUI directory
    $springuiPath = Join-Path $ModPath "Assets\SpringUI\$uiName"
    try {
        if (-not (Test-Path $springuiPath)) {
            New-Item -ItemType Directory -Path $springuiPath -Force -ErrorAction Stop | Out-Null
        }
    }
    catch {
        Write-Log "Failed to create SpringUI directory: $_" -Level Error
        return @{ Success = $false }
    }
    
    try {
        # Generate UXML content based on old UI
        $uxmlContent = Generate-SpringUIUXML -UIName $uiName -SourcePath $sourcePath -UIType $uiType
        $uxmlPath = Join-Path $springuiPath "$uiName.uxml"
        $uxmlContent | Out-File -FilePath $uxmlPath -Encoding UTF8 -Force -ErrorAction Stop
        
        # Generate USS content
        $ussContent = Generate-SpringUIUSS -UIName $uiName -SourcePath $sourcePath
        $ussPath = Join-Path $springuiPath "$uiName.uss"
        $ussContent | Out-File -FilePath $ussPath -Encoding UTF8 -Force -ErrorAction Stop
        
        Write-Log "Created SpringUI assets: $uxmlPath" -Level Success
        Write-Log "Created SpringUI stylesheet: $ussPath" -Level Success
    }
    catch {
        Write-Log "Failed to create SpringUI files: $_" -Level Error
        return @{ Success = $false }
    }
    
    # Create Unity .meta files if Unity is available
    $unityPath = Find-UnityEditor
    if ($unityPath) {
        # Refresh asset database to register new files
        Invoke-UnityEditorScript -UnityPath $unityPath -ProjectPath $ModPath `
            -MethodName "RefreshAssetDatabase" `
            -Parameters @{} `
            -TimeoutSeconds 30 | Out-Null
    }
    
    return @{
        UXML = $uxmlPath
        USS = $ussPath
        Success = $true
    }
}

function Generate-SpringUIUXML {
    param(
        [string]$UIName,
        [string]$SourcePath,
        [string]$UIType
    )
    
    # Read source file to extract UI elements
    $sourceContent = Get-Content $SourcePath -Raw -ErrorAction SilentlyContinue
    $elements = @()
    
    if ($UIType -eq "XML" -and $sourceContent) {
        # Parse old XML UI
        if ($sourceContent -match "<Panel|</Panel>") {
            $elements += "Panel"
        }
        if ($sourceContent -match "<Button|</Button>") {
            $elements += "Button"
        }
        if ($sourceContent -match "<Label|</Label>|<Text|</Text>") {
            $elements += "Label"
        }
        if ($sourceContent -match "<Input|</Input>|<TextField") {
            $elements += "TextField"
        }
    } elseif ($UIType -eq "CSharp" -and $sourceContent) {
        # Parse QupKit UI code
        if ($sourceContent -match "ButtonControl|new Button|AddChild.*Button") {
            $elements += "Button"
        }
        if ($sourceContent -match "PanelControl|new Panel|AddChild.*Panel") {
            $elements += "Panel"
        }
        if ($sourceContent -match "Label|\.Label\s*=|Text.*Label") {
            $elements += "Label"
        }
        if ($sourceContent -match "TextField|TextEdit|InputField") {
            $elements += "TextField"
        }
        if ($sourceContent -match "ScrollViewControl|ScrollView") {
            $elements += "ScrollView"
        }
        if ($sourceContent -match "SpriteControl|Image") {
            $elements += "Image"
        }
        
        # Also check for IMGUI patterns
        if ($sourceContent -match "GUI\.Button|GUILayout\.Button") {
            $elements += "Button"
        }
        if ($sourceContent -match "GUI\.Label|GUILayout\.Label") {
            $elements += "Label"
        }
        if ($sourceContent -match "GUI\.TextField|GUILayout\.TextField") {
            $elements += "TextField"
        }
        if ($sourceContent -match "GUI\.Window|GUILayout\.Window") {
            $elements += "Window"
        }
        if ($sourceContent -match "GUI\.Box|GUILayout\.Box") {
            $elements += "Box"
        }
        
        # Extract control names from QupKit code
        if ($sourceContent -match "new\s+(\w+Control)\s*\(") {
            $controlType = $Matches[1]
            switch ($controlType) {
                "ButtonControl" { $elements += "Button" }
                "PanelControl" { $elements += "Panel" }
                "ScrollViewControl" { $elements += "ScrollView" }
                "SpriteControl" { $elements += "Image" }
            }
        }
    }
    
    # Build UXML content
    $uxml = @"
<?xml version="1.0" encoding="utf-8"?>
<ui:UXML xmlns:ui="UnityEngine.UIElements" xmlns:uie="UnityEditor.UIElements" xsi="http://www.w3.org/2001/XMLSchema-instance" engine="UnityEngine.UIElements" editor="UnityEditor.UIElements" noNamespaceSchemaLocation="../../UIElementsSchema/UIElements.xsd" editor-extension-mode="False">
    <ui:VisualElement name="$UIName" class="$($UIName.ToLower())">
        <!-- Converted from $UIType UI: $SourcePath -->
"@
    
    # Add detected elements
    # QupKit BaseView typically has a window structure
    $hasWindow = $elements -contains "Window" -or $elements.Count -eq 0 -or $sourceContent -match "BaseView|OnGUI"
    
    if ($hasWindow) {
        $uxml += @"
        <ui:VisualElement name="window" class="window">
            <ui:VisualElement name="title" class="title">
                <ui:Label text="$UIName" />
            </ui:VisualElement>
            <ui:VisualElement name="content" class="content">
"@
    } else {
        $uxml += @"
        <ui:VisualElement name="content" class="content">
"@
    }
    
    # Remove duplicates and process elements
    $uniqueElements = $elements | Select-Object -Unique
    $elementIndex = 0
    
    foreach ($element in $uniqueElements) {
        switch ($element) {
            "Panel" {
                $uxml += @"
                <ui:VisualElement name="panel_$elementIndex" class="panel">
                    <!-- Panel content -->
                </ui:VisualElement>
"@
                $elementIndex++
            }
            "Button" {
                $uxml += @"
                <ui:Button name="button_$elementIndex" text="Button" class="button" />
"@
                $elementIndex++
            }
            "Label" {
                $uxml += @"
                <ui:Label name="label_$elementIndex" text="Label" class="label" />
"@
                $elementIndex++
            }
            "TextField" {
                $uxml += @"
                <ui:TextField name="textfield_$elementIndex" value="" class="textfield" />
"@
                $elementIndex++
            }
            "ScrollView" {
                $uxml += @"
                <ui:ScrollView name="scrollview_$elementIndex" class="scrollview">
                    <ui:VisualElement name="content" class="scroll-content">
                        <!-- Scrollable content -->
                    </ui:VisualElement>
                </ui:ScrollView>
"@
                $elementIndex++
            }
            "Image" {
                $uxml += @"
                <ui:VisualElement name="image_$elementIndex" class="image">
                    <!-- Image element -->
                </ui:VisualElement>
"@
                $elementIndex++
            }
            "Box" {
                $uxml += @"
                <ui:VisualElement name="box_$elementIndex" class="box">
                    <!-- Box content -->
                </ui:VisualElement>
"@
                $elementIndex++
            }
        }
    }
    
    if ($elements -contains "Window" -or $elements.Count -eq 0) {
        $uxml += @"
            </ui:VisualElement>
        </ui:VisualElement>
"@
    }
    
    $uxml += @"
        </ui:VisualElement>
    </ui:VisualElement>
</ui:UXML>
"@
    
    return $uxml
}

function Generate-SpringUIUSS {
    param(
        [string]$UIName,
        [string]$SourcePath
    )
    
    $className = $UIName.ToLower()
    
    $uss = @"
/* SpringUI Stylesheet for $UIName */
/* Converted from: $SourcePath */

.$className {
    width: 100%;
    height: 100%;
    flex-direction: column;
    align-items: stretch;
    padding: 10px;
    background-color: rgba(20, 20, 20, 255);
}

.$className .window {
    width: 100%;
    height: 100%;
    flex-direction: column;
    background-color: rgba(40, 40, 40, 255);
    border-width: 2px;
    border-color: rgba(100, 100, 100, 255);
    border-radius: 4px;
    padding: 8px;
}

.$className .title {
    width: 100%;
    height: 30px;
    background-color: rgba(60, 60, 60, 255);
    border-bottom-width: 1px;
    border-bottom-color: rgba(100, 100, 100, 255);
    padding: 4px;
    margin-bottom: 8px;
}

.$className .content {
    width: 100%;
    flex-grow: 1;
    flex-direction: column;
    padding: 4px;
}

.$className .button {
    width: 100%;
    height: 30px;
    margin-bottom: 4px;
    background-color: rgba(80, 80, 120, 255);
    border-width: 1px;
    border-color: rgba(120, 120, 160, 255);
    border-radius: 2px;
}

.$className .button:hover {
    background-color: rgba(100, 100, 140, 255);
}

.$className .button:active {
    background-color: rgba(60, 60, 100, 255);
}

.$className .label {
    width: 100%;
    height: 20px;
    margin-bottom: 4px;
    color: rgba(220, 220, 220, 255);
    font-size: 14px;
}

.$className .textfield {
    width: 100%;
    height: 25px;
    margin-bottom: 4px;
    background-color: rgba(30, 30, 30, 255);
    border-width: 1px;
    border-color: rgba(100, 100, 100, 255);
    border-radius: 2px;
    color: rgba(220, 220, 220, 255);
    padding: 4px;
}

.$className .box {
    width: 100%;
    margin-bottom: 4px;
    background-color: rgba(25, 25, 25, 255);
    border-width: 1px;
    border-color: rgba(80, 80, 80, 255);
    border-radius: 2px;
    padding: 4px;
}

.$className .panel {
    width: 100%;
    margin-bottom: 4px;
    background-color: rgba(30, 30, 30, 255);
    border-width: 1px;
    border-color: rgba(70, 70, 70, 255);
    border-radius: 2px;
    padding: 4px;
}

.$className .scrollview {
    width: 100%;
    height: 200px;
    margin-bottom: 4px;
    background-color: rgba(20, 20, 20, 255);
    border-width: 1px;
    border-color: rgba(60, 60, 60, 255);
    border-radius: 2px;
}

.$className .scroll-content {
    width: 100%;
    flex-direction: column;
    padding: 4px;
}

.$className .image {
    width: 100%;
    height: 100px;
    margin-bottom: 4px;
    background-color: rgba(50, 50, 50, 255);
    border-width: 1px;
    border-color: rgba(80, 80, 80, 255);
    border-radius: 2px;
}
"@
    
    return $uss
}

# ============================================================
# MAIN PROCESSING
# ============================================================

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Caves of Qud Unity Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Validate mod path
if (-not (Test-ValidPath -Path $ModPath -Description "Mod path")) {
    exit 1
}

$assetsPath = Join-Path $ModPath "Assets"
if (-not (Test-ValidPath -Path $assetsPath -Description "Assets folder")) {
    exit 1
}

# Determine project path (use settings or mod path)
$projectPath = if ($script:UnityProjectPath -and (Test-Path $script:UnityProjectPath)) {
    $script:UnityProjectPath
} else {
    $ModPath
}

# Parse asset types
$assetTypesList = if ($AssetTypes -eq "all") {
    $script:AssetConfigs.Keys
} else {
    $AssetTypes -split "," | ForEach-Object { $_.Trim() }
}

Write-Log "Mod Path: $ModPath" -Level Info
Write-Log "Project Path: $projectPath" -Level Info
Write-Log "Asset Types: $($assetTypesList -join ', ')" -Level Info
Write-Log "Mode: $(if ($ScanOnly) { 'Scan Only' } else { 'Generate' })" -Level Info
Write-Host ""

# Scan for missing assets
Write-Log "Scanning for missing assets..." -Level Info
$missingAssets = @()

foreach ($assetType in $assetTypesList) {
    $missing = Find-MissingAssets -ModPath $ModPath -AssetType $assetType
    $missingAssets += $missing
}

# Scan for old UI elements that need conversion to SpringUI
if ($assetTypesList -contains "springui" -or $assetTypesList -contains "all") {
    Write-Log "Scanning for old UI elements to convert..." -Level Info
    try {
        $oldUIElements = Find-OldUIElements -ModPath $ModPath
        if ($oldUIElements.Count -gt 0) {
            Write-Log "Found $($oldUIElements.Count) old UI elements to convert" -Level Warning
            foreach ($oldUI in $oldUIElements) {
                $missingAssets += @{
                    Type = "springui"
                    Path = Join-Path $ModPath "Assets\SpringUI\$($oldUI.Name)"
                    Reason = "Convert from $($oldUI.Source)"
                    OldUIElement = $oldUI
                }
            }
        }
    }
    catch {
        Write-Log "Error scanning for old UI elements: $_" -Level Warning
    }
}

$script:Progress.TotalAssets = $missingAssets.Count
Write-Log "Found $($missingAssets.Count) missing/conversion assets" -Level Success
Write-Host ""

if ($ScanOnly) {
    # Display scan results
    Write-Log "Scan Results:" -Level Info
    $missingAssets | Group-Object -Property Type | ForEach-Object {
        Write-Log "$($_.Name): $($_.Count) assets" -Level Warning
    }
    exit 0
}

# Generate assets
Write-Log "Generating assets..." -Level Info
Write-Host ""

foreach ($asset in $missingAssets) {
    $script:Progress.ProcessedAssets++
    $percent = [Math]::Floor(($script:Progress.ProcessedAssets / $script:Progress.TotalAssets) * 100)
    Write-Progress -Activity "Generating" -Status "$($asset.Type)" -PercentComplete $percent
    
    Write-Log "[$($asset.Type)] $($asset.Reason)" -Level Warning
    
    try {
        switch ($asset.Type) {
            "materials" {
                # Find associated texture
                $texturePath = Join-Path $ModPath "Textures"
                $textureFile = $null
                if (Test-Path $texturePath) {
                    $textureFile = Get-ChildItem -Path $texturePath -Filter "*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
                }
                $texPath = if ($textureFile) { $textureFile.FullName } else { "" }
                
                $success = Generate-UnityMaterial -ProjectPath $projectPath -SystemName "QudMod" -TexturePath $texPath -UnityPath $UnityPath
                if ($success) {
                    $script:Progress.GeneratedAssets++
                    Write-Log "Material generated" -Level Success
                } else {
                    $script:Progress.FailedAssets++
                    Write-Log "Material generation failed" -Level Error
                }
            }
            "prefabs" {
                $success = Generate-UnityPrefab -ProjectPath $projectPath -SystemName "QudMod" -PrefabName "QudMod_Prefab" -UnityPath $UnityPath
                if ($success) {
                    $script:Progress.GeneratedAssets++
                    Write-Log "Prefab generated" -Level Success
                } else {
                    $script:Progress.FailedAssets++
                    Write-Log "Prefab generation failed" -Level Error
                }
            }
            "springui" {
                # Check if this is a conversion from old UI
                if ($asset.OldUIElement) {
                    try {
                        $result = Convert-OldUIToSpringUI -OldUIElement $asset.OldUIElement -ModPath $ModPath
                        if ($result.Success) {
                            $script:Progress.GeneratedAssets++
                            Write-Log "Converted old UI to SpringUI" -Level Success
                        } else {
                            $script:Progress.FailedAssets++
                            Write-Log "Conversion failed" -Level Error
                        }
                    }
                    catch {
                        $script:Progress.FailedAssets++
                        Write-Log "Conversion error: $_" -Level Error
                    }
                } else {
                    # Create new SpringUI assets
                    Write-Log "Creating new SpringUI assets..." -Level Info
                    try {
                        $springuiPath = Join-Path $ModPath "Assets\SpringUI\QudModUI"
                        if (-not (Test-Path $springuiPath)) {
                            New-Item -ItemType Directory -Path $springuiPath -Force -ErrorAction Stop | Out-Null
                        }
                        
                        $uxmlPath = Join-Path $springuiPath "QudModUI.uxml"
                        $uxmlContent = Generate-SpringUIUXML -UIName "QudModUI" -SourcePath "" -UIType "New"
                        $uxmlContent | Out-File -FilePath $uxmlPath -Encoding UTF8 -Force -ErrorAction Stop
                        
                        $ussPath = Join-Path $springuiPath "QudModUI.uss"
                        $ussContent = Generate-SpringUIUSS -UIName "QudModUI" -SourcePath ""
                        $ussContent | Out-File -FilePath $ussPath -Encoding UTF8 -Force -ErrorAction Stop
                        
                        $script:Progress.GeneratedAssets++
                        Write-Log "SpringUI assets created" -Level Success
                    }
                    catch {
                        $script:Progress.FailedAssets++
                        Write-Log "SpringUI creation failed: $_" -Level Error
                    }
                }
            }
            "bundles" {
                $success = Build-UnityAssetBundles -ProjectPath $projectPath -UnityPath $UnityPath
                if ($success) {
                    $script:Progress.GeneratedAssets++
                    Write-Log "Asset bundles built" -Level Success
                } else {
                    $script:Progress.FailedAssets++
                    Write-Log "Asset bundle build failed" -Level Error
                }
            }
            default {
                Write-Log "Unknown asset type: $($asset.Type)" -Level Warning
                $script:Progress.SkippedAssets++
            }
        }
    }
    catch {
        $script:Progress.FailedAssets++
        Write-Log "Error processing asset: $_" -Level Error
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Log "Total Assets: $($script:Progress.TotalAssets)" -Level Info
Write-Log "Generated: $($script:Progress.GeneratedAssets)" -Level Success
Write-Log "Skipped: $($script:Progress.SkippedAssets)" -Level Info
Write-Log "Failed: $($script:Progress.FailedAssets)" -Level $(if ($script:Progress.FailedAssets -gt 0) { "Error" } else { "Info" })
$elapsed = (Get-Date) - $script:Progress.StartTime
Write-Log "Time: $($elapsed.ToString('mm\:ss'))" -Level Info
Write-Host ""

# Exit with appropriate code
if ($script:Progress.FailedAssets -gt 0) {
    exit 1
} elseif ($script:Progress.GeneratedAssets -eq 0 -and $script:Progress.TotalAssets -gt 0) {
    exit 1
} else {
    exit 0
}
