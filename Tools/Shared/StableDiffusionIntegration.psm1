<#
.SYNOPSIS
    Shared Stable Diffusion 3.5 integration module for AI-Assisted Modding Tools (AAMT).

.DESCRIPTION
    Talks to the local SD3.5 Medium server (Shared\sd35_server.py, port 1338,
    version string "aamt-1338*"). Optionally enhances prompts through Ollama first.

    Design notes
    - File is plain ASCII / UTF-8 without BOM. Keep it that way: Windows PowerShell 5.1
      reads BOM-less files as ANSI, so smart quotes and em-dashes corrupt parsing.
    - Detection order: SD3.5 /ping -> SD3.5 python process -> fallback servers
      (A1111, ComfyUI, legacy API server, InvokeAI).
    - IPv4 and IPv6 loopback are both probed (127.0.0.1 and [::1]). The host that
      answered last is cached and tried first. Override with AAMT_SD_HOST, disable
      IPv6 with AAMT_SD_IPV6=0, change the port with AAMT_SD_PORT.
    - "Busy" is not "down": /ping uses a generous timeout with retries, requests never
      go through a system proxy, and a server that stops answering /ping while its
      port still accepts connections is treated as busy for AAMT_SD_BUSY_GRACE_SEC.
    - The AAMT server speaks HTTP/1.1 only. A 426 reply means a foreign process owns
      the port (for example a WebSocket++ service), not that HTTP/2 is needed.
#>

# ============================================================
# CONFIGURATION
# ============================================================

# Fallback servers probed only after the SD3.5 server was not found.
$script:KnownSDSetups = @(
    @{ Name = "SD3.5 API Server"; Port = 1338; ApiEndpoint = "/v1/images/generations"; HealthEndpoint = "/ping"; Type = "SD35Server" },
    @{ Name = "AUTOMATIC1111 WebUI"; Port = 7860; ApiEndpoint = "/sdapi/v1/txt2img"; HealthEndpoint = "/sdapi/v1/sd-models"; Type = "A1111" },
    @{ Name = "ComfyUI"; Port = 8188; ApiEndpoint = "/prompt"; HealthEndpoint = "/system_stats"; Type = "ComfyUI" },
    @{ Name = "Legacy Stable Diffusion API Server (Port 8000)"; Port = 8000; ApiEndpoint = "/v1/images/generations"; HealthEndpoint = "/ping"; Type = "APIServer" },
    @{ Name = "InvokeAI"; Port = 9090; ApiEndpoint = "/api/v1/images/generate"; HealthEndpoint = "/api/v1/app/version"; Type = "InvokeAI" }
)

$script:SDPort = 1338
$parsedPort = 0
if ($env:AAMT_SD_PORT -and [int]::TryParse($env:AAMT_SD_PORT, [ref]$parsedPort) -and $parsedPort -gt 0 -and $parsedPort -lt 65536) {
    $script:SDPort = $parsedPort
}
$script:KnownSDSetups[0].Port = $script:SDPort

$script:ServerStartupScript = "Start-StableDiffusionServer.ps1"
$script:SDPreferredHost = $null      # host that answered last (127.0.0.1 or ::1)
$script:SDLastGoodPing = $null       # [datetime] of the last successful /ping

# Probe tuning. The server is threaded, but heavy torch work can still starve /ping,
# so the timeout is generous and a miss is retried before the server is called down.
$script:SDPingTimeoutSec = 4.0
$script:SDPingAttempts = 2
$script:SDBusyGraceSec = 120
$parsedNum = 0.0
if ($env:AAMT_SD_PING_TIMEOUT_SEC -and [double]::TryParse($env:AAMT_SD_PING_TIMEOUT_SEC, [ref]$parsedNum) -and $parsedNum -gt 0) {
    $script:SDPingTimeoutSec = $parsedNum
}
if ($env:AAMT_SD_BUSY_GRACE_SEC -and [double]::TryParse($env:AAMT_SD_BUSY_GRACE_SEC, [ref]$parsedNum) -and $parsedNum -ge 0) {
    $script:SDBusyGraceSec = $parsedNum
}

# Default generation parameters tuned for SD3 Medium.
$script:DefaultGenerationParams = @{
    Width = 1024
    Height = 1024
    Steps = 28
    GuidanceScale = 7.0
    NegativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark, simple, basic"
}

# Generous FINITE read timeout. SD3.5 Medium with CPU offload can take many minutes
# per image. Override with AAMT_SD_HTTP_TIMEOUT_SEC.
$script:SDHttpTimeoutSec = 3600
$parsedTimeout = 0
if ($env:AAMT_SD_HTTP_TIMEOUT_SEC -and [int]::TryParse($env:AAMT_SD_HTTP_TIMEOUT_SEC, [ref]$parsedTimeout) -and $parsedTimeout -gt 0) {
    $script:SDHttpTimeoutSec = $parsedTimeout
}

# On-disk output cache of the SD3.5 server (mirrors sd_http_client.py salvage).
$script:SDOutputsDir = "E:\tools\sd3.5\sd3.5\outputs"
if ($env:AAMT_SD_OUTPUTS_DIR) { $script:SDOutputsDir = $env:AAMT_SD_OUTPUTS_DIR }

# ============================================================
# PRIVATE HELPERS (not exported)
# ============================================================

function Format-SdUrlHost {
    param([string]$HostName)
    if ($HostName -match ':' -and $HostName -notmatch '^\[') { return "[$HostName]" }
    return $HostName
}

function Get-SdBaseUrl {
    param([string]$HostName, [int]$Port)
    return ("http://" + (Format-SdUrlHost -HostName $HostName) + ":" + $Port)
}

function Get-SdHostCandidates {
    $list = @()
    if ($env:AAMT_SD_HOST) { $list += $env:AAMT_SD_HOST.Trim().Trim('[', ']') }
    if ($script:SDPreferredHost) { $list += $script:SDPreferredHost }
    $list += '127.0.0.1'
    if ($env:AAMT_SD_IPV6 -ne '0') { $list += '::1' }
    $seen = @{}
    $out = @()
    foreach ($item in $list) {
        if ([string]::IsNullOrWhiteSpace($item)) { continue }
        $key = $item.ToLowerInvariant()
        if ($env:AAMT_SD_IPV6 -eq '0' -and $key -eq '::1') { continue }
        if (-not $seen.ContainsKey($key)) {
            $seen[$key] = $true
            $out += $item
        }
    }
    return $out
}

function New-SdSetup {
    param(
        [string]$Name,
        [string]$HostName,
        [int]$Port,
        [string]$ApiEndpoint,
        [string]$HealthEndpoint,
        [string]$Type,
        [bool]$Responding = $false
    )
    return @{
        Name = $Name
        Host = $HostName
        Port = $Port
        BaseUrl = (Get-SdBaseUrl -HostName $HostName -Port $Port)
        ApiEndpoint = $ApiEndpoint
        HealthEndpoint = $HealthEndpoint
        Type = $Type
        Responding = $Responding
        Loaded = $false
        Version = ""
        ProcessFound = $false
        ProcessId = 0
    }
}

function Set-SdActiveSetup {
    param([hashtable]$Setup)
    $script:ActiveSDSetup = $Setup
    $script:StableDiffusionUrl = [string]$Setup.BaseUrl
    $script:StableDiffusionApiUrl = ([string]$Setup.BaseUrl) + ([string]$Setup.ApiEndpoint)
    if ($Setup.Host) { $script:SDPreferredHost = [string]$Setup.Host }
}

function Resolve-SdOutputPath {
    param([string]$Path)
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}

function Test-SdTcpPort {
    # True if any address of HostName accepts a TCP connection on Port. Works for
    # IPv4 literals, IPv6 literals and DNS names (all resolved addresses are tried).
    param([string]$HostName, [int]$Port, [int]$TimeoutMs = 500)
    $addresses = @()
    try {
        $ip = $null
        if ([System.Net.IPAddress]::TryParse($HostName.Trim('[', ']'), [ref]$ip)) {
            $addresses = @($ip)
        } else {
            $addresses = @([System.Net.Dns]::GetHostAddresses($HostName))
        }
    } catch {
        return $false
    }
    foreach ($addr in $addresses) {
        $client = $null
        try {
            $client = [System.Net.Sockets.TcpClient]::new($addr.AddressFamily)
            $async = $client.BeginConnect($addr, $Port, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
                $client.EndConnect($async)
                if ($client.Connected) { return $true }
            }
        } catch {
            # try next address
        } finally {
            if ($client) { $client.Close() }
        }
    }
    return $false
}

function Invoke-SdHttpRequest {
    # Single place that builds an HTTP/1.1 request. Never throws; returns a hashtable:
    #   Ok, StatusCode (0 = no HTTP response), Body, Error, TimedOut, Refused
    param(
        [string]$Url,
        [string]$Method = "GET",
        [string]$JsonBody = "",
        [double]$TimeoutSec = 5
    )
    $result = @{ Ok = $false; StatusCode = 0; Body = ""; Error = ""; TimedOut = $false; Refused = $false }
    $handler = $null
    $client = $null
    $request = $null
    $response = $null
    try {
        Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
        $handler = [System.Net.Http.HttpClientHandler]::new()
        # Loopback traffic must never be routed through a system proxy.
        try { $handler.UseProxy = $false } catch { }
        $client = [System.Net.Http.HttpClient]::new($handler)
        $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSec)
        $httpMethod = [System.Net.Http.HttpMethod]::new($Method)
        $request = [System.Net.Http.HttpRequestMessage]::new($httpMethod, $Url)
        try { $request.Version = [Version]"1.1" } catch { }
        $request.Headers.Add("Accept", "application/json")
        if (-not [string]::IsNullOrEmpty($JsonBody)) {
            $request.Content = [System.Net.Http.StringContent]::new($JsonBody, [System.Text.Encoding]::UTF8, "application/json")
        }
        $response = $client.SendAsync($request).GetAwaiter().GetResult()
        $result.StatusCode = [int]$response.StatusCode
        $result.Ok = [bool]$response.IsSuccessStatusCode
        $result.Body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    } catch {
        $ex = $_.Exception
        $result.Error = $ex.Message
        while ($ex) {
            $typeName = $ex.GetType().Name
            if ($typeName -match 'TaskCanceled|OperationCanceled|Timeout') { $result.TimedOut = $true }
            if ($ex -is [System.Net.Sockets.SocketException] -and $ex.SocketErrorCode -eq [System.Net.Sockets.SocketError]::ConnectionRefused) {
                $result.Refused = $true
            }
            $ex = $ex.InnerException
        }
    } finally {
        if ($response) { $response.Dispose() }
        if ($request) { $request.Dispose() }
        if ($client) { $client.Dispose() }
        if ($handler) { $handler.Dispose() }
    }
    return $result
}

function Get-SdPingProbe {
    # GET /ping on one host. Returns $null if nothing answered with HTTP.
    param([string]$HostName, [int]$Port, [double]$TimeoutSec = 0, [int]$Attempts = 0)
    if ($TimeoutSec -le 0) { $TimeoutSec = $script:SDPingTimeoutSec }
    if ($Attempts -le 0) { $Attempts = $script:SDPingAttempts }
    $url = (Get-SdBaseUrl -HostName $HostName -Port $Port) + "/ping"
    for ($i = 1; $i -le $Attempts; $i++) {
        $r = Invoke-SdHttpRequest -Url $url -Method "GET" -TimeoutSec $TimeoutSec
        if ($r.StatusCode -gt 0) {
            $probe = @{
                Host = $HostName
                Port = $Port
                StatusCode = $r.StatusCode
                Version = ""
                Loaded = $false
                Loading = $false
                Generating = $false
                IsAamt = $false
            }
            if ($r.StatusCode -eq 200 -and $r.Body) {
                try {
                    $data = $r.Body | ConvertFrom-Json
                    if ($data.version) { $probe.Version = [string]$data.version }
                    $probe.Loaded = [bool]$data.loaded
                    $probe.Loading = [bool]$data.loading
                    $probe.Generating = [bool]$data.generating
                } catch {
                    # not JSON; stays "foreign"
                }
            }
            $probe.IsAamt = $probe.Version.StartsWith("aamt-1338")
            return $probe
        }
        if ($r.Refused) { return $null }   # nothing listening on this family; do not wait
        if ($i -lt $Attempts) { Start-Sleep -Milliseconds 300 }
    }
    return $null
}

function Get-SdListenerPid {
    # Process ids listening on Port (IPv4 and IPv6).
    param([int]$Port)
    $found = @()
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($conns) { $found += @($conns | Select-Object -ExpandProperty OwningProcess -Unique) }
    } catch { }
    if ($found.Count -eq 0) {
        try {
            $pattern = '^\s*TCP\s+\S*:' + $Port + '\s+\S+\s+LISTENING\s+(\d+)\s*$'
            foreach ($line in @(netstat -ano 2>$null)) {
                if ([string]$line -match $pattern) { $found += [int]$Matches[1] }
            }
        } catch { }
    }
    return @($found | Where-Object { $_ -gt 0 } | Select-Object -Unique)
}

function Find-SdServerProcess {
    # python process running the AAMT server.py (not sd_server.py of other tools).
    param([int]$Port)
    try {
        $procs = @(Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" -ErrorAction Stop)
        foreach ($p in $procs) {
            $cmd = [string]$p.CommandLine
            if ([string]::IsNullOrWhiteSpace($cmd)) { continue }
            if ($cmd -match '(^|[\\/\s"])server\.py' -and ($cmd -match 'sd3\.5' -or $cmd -match ('--port\s+' + $Port + '\b'))) {
                return $p
            }
        }
    } catch { }
    return $null
}

function Test-SdBusyGrace {
    # A server that does not answer /ping right now is still "up" when its port accepts
    # connections and it either answered recently or its process is found.
    param([hashtable]$Setup)
    if (-not (Test-SdTcpPort -HostName ([string]$Setup.Host) -Port ([int]$Setup.Port) -TimeoutMs 1000)) { return $false }
    if ($script:SDLastGoodPing) {
        $age = ((Get-Date) - $script:SDLastGoodPing).TotalSeconds
        if ($age -le $script:SDBusyGraceSec) {
            Write-Host "  [SD] /ping slow but port is open; treating server as busy (last OK $([int]$age)s ago)" -ForegroundColor Yellow
            return $true
        }
    }
    if ($Setup.ProcessFound) {
        Write-Host "  [SD] /ping not answering but SD3.5 process owns the port; treating server as busy" -ForegroundColor Yellow
        return $true
    }
    return $false
}

function ConvertFrom-SdJson {
    # ConvertFrom-Json in Windows PowerShell 5.1 fails on strings over 2 MB; fall back
    # to a serializer with no length cap.
    param([string]$Raw)
    try {
        return ($Raw | ConvertFrom-Json)
    } catch {
        Add-Type -AssemblyName System.Web.Extensions -ErrorAction Stop
        $ser = New-Object System.Web.Script.Serialization.JavaScriptSerializer
        $ser.MaxJsonLength = [int]::MaxValue
        return $ser.DeserializeObject($Raw)
    }
}

function Get-SdImagesFromResponse {
    # Returns an array of base64 image strings. Handles SD3.5 / OpenAI "b64_json",
    # OpenAI "url" and A1111 "images".
    param([string]$Raw, [string]$ApiType)
    if ([string]::IsNullOrWhiteSpace($Raw)) { throw "Empty response from SD API" }
    $images = @()

    # Fast path that also avoids JSON size limits: pull b64_json values directly.
    foreach ($m in [regex]::Matches($Raw, '"b64_json"\s*:\s*"([^"]+)"')) {
        $images += ($m.Groups[1].Value -replace '\\/', '/')
    }
    if ($images.Count -gt 0) { return $images }

    $data = ConvertFrom-SdJson -Raw $Raw
    if ($ApiType -eq "A1111") {
        if ($data.images -and @($data.images).Count -gt 0) {
            foreach ($img in @($data.images)) { $images += [string]$img }
        } else {
            throw "No images in A1111 response"
        }
    } else {
        if ($data.data -and @($data.data).Count -gt 0) {
            foreach ($item in @($data.data)) {
                if ($item.b64_json) {
                    $images += [string]$item.b64_json
                } elseif ($item.url) {
                    $bytes = Get-SdBytesFromUrl -Url ([string]$item.url)
                    $images += [Convert]::ToBase64String($bytes)
                }
            }
        } elseif ($data.images -and @($data.images).Count -gt 0) {
            foreach ($img in @($data.images)) { $images += [string]$img }
        } else {
            throw "No image data in API response"
        }
    }
    if ($images.Count -eq 0) { throw "No images were generated" }
    return $images
}

function Get-SdBytesFromUrl {
    param([string]$Url)
    Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
    $handler = [System.Net.Http.HttpClientHandler]::new()
    try { $handler.UseProxy = $false } catch { }
    $client = [System.Net.Http.HttpClient]::new($handler)
    try {
        $client.Timeout = [TimeSpan]::FromSeconds(120)
        return $client.GetByteArrayAsync($Url).GetAwaiter().GetResult()
    } finally {
        $client.Dispose()
        $handler.Dispose()
    }
}

function Get-SdEnhancedPrompt {
    # Optional Ollama prompt enhancement. Returns the original prompt on any problem.
    param([string]$Prompt)
    try {
        if (-not (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue)) {
            $ollamaModule = Join-Path $PSScriptRoot "OllamaIntegration.psm1"
            if (-not (Test-Path -LiteralPath $ollamaModule)) { return $Prompt }
            Import-Module $ollamaModule -Force -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
        }
        if (-not (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue)) { return $Prompt }
        if (Get-Command Test-OllamaConnection -ErrorAction SilentlyContinue) {
            if (-not (Test-OllamaConnection)) { return $Prompt }
        }
        Write-Host "  Enhancing prompt with Ollama..." -ForegroundColor Cyan
        $ask = "You are a game asset designer. Enhance this asset description for high-quality Stable Diffusion image generation.`n`n" +
               "Original: $Prompt`n`n" +
               "Include specific visual details (colors, textures, materials, lighting), style, composition and framing. " +
               "Return ONLY the enhanced prompt, no introductory text."
        $enhanced = Invoke-OllamaRequest -Prompt $ask -TaskType "visual" -ResponseLength "detailed" -AutoEscalate:$true
        if ($enhanced -and ([string]$enhanced).Length -gt $Prompt.Length) {
            $text = ([string]$enhanced).Trim()
            Write-Host "  [OK] Prompt enhanced ($($text.Length) chars)" -ForegroundColor Green
            return $text
        }
    } catch {
        Write-Host "  [WARN] Ollama enhancement skipped: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    return $Prompt
}

function Test-SdImageDimensions {
    # $true = size matches, $false = size differs, $null = could not read the image.
    param([string]$Path, [int]$Width, [int]$Height)
    $stream = $null
    $img = $null
    try {
        Add-Type -AssemblyName System.Drawing -ErrorAction Stop
        $stream = [System.IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
        $img = [System.Drawing.Image]::FromStream($stream, $false, $false)
        return (($img.Width -eq $Width) -and ($img.Height -eq $Height))
    } catch {
        return $null
    } finally {
        if ($img) { $img.Dispose() }
        if ($stream) { $stream.Dispose() }
    }
}

# ------------------------------------------------------------
# Module state. ActiveSDSetup is ALWAYS a hashtable and the URLs are ALWAYS strings.
# ------------------------------------------------------------
$script:ActiveSDSetup = New-SdSetup -Name "SD3.5 API Server" -HostName "127.0.0.1" -Port $script:SDPort `
    -ApiEndpoint "/v1/images/generations" -HealthEndpoint "/ping" -Type "SD35Server" -Responding $false
$script:StableDiffusionUrl = [string]$script:ActiveSDSetup.BaseUrl
$script:StableDiffusionApiUrl = [string]$script:ActiveSDSetup.BaseUrl + [string]$script:ActiveSDSetup.ApiEndpoint

# ============================================================
# PUBLIC FUNCTIONS
# ============================================================

function Get-FreeVramMB {
    <#
    .SYNOPSIS
    Free GPU VRAM in MB via nvidia-smi, or $null when unavailable. Never throws.
    #>
    param([switch]$Total)
    try {
        $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
        if (-not $smi) { return $null }
        $query = "memory.free"
        if ($Total) { $query = "memory.total" }
        $out = & nvidia-smi --query-gpu=$query --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
        $vals = @($out | ForEach-Object { ($_ -replace '[^\d]', '') } | Where-Object { $_ } | ForEach-Object { [int]$_ })
        if ($vals.Count -eq 0) { return $null }
        return ($vals | Measure-Object -Maximum).Maximum
    } catch {
        return $null
    }
}

function Test-SdOomError {
    <#
    .SYNOPSIS
    Heuristic: does this message look like a CUDA / GPU out-of-memory failure?
    #>
    param([string]$Message)
    if ([string]::IsNullOrWhiteSpace($Message)) { return $false }
    $m = $Message.ToLowerInvariant()
    if ($m -match 'out of memory') { return $true }
    if ($m -match 'cuda' -and $m -match 'memory') { return $true }
    if ($m -match '\boom\b') { return $true }
    return $false
}

function Get-SalvagedSdOutput {
    <#
    .SYNOPSIS
    Recovers a finished image from the server's output cache when the HTTP client gave
    up but generation completed server-side. Returns the output path or $null.
    Mirrors sd_http_client.py salvage_server_output.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][datetime]$StartedAt,
        [int]$MaxAgeSec = 14400,
        [int]$Width = 0,
        [int]$Height = 0
    )
    try {
        $dir = $script:SDOutputsDir
        if ([string]::IsNullOrWhiteSpace($dir)) { return $null }
        if (-not (Test-Path -LiteralPath $dir -PathType Container)) { return $null }
        $target = Resolve-SdOutputPath -Path $OutputPath

        $candidates = @()
        # gen_*.png is unique per job; prefer it over the shared latest.png.
        $candidates += @(Get-ChildItem -LiteralPath $dir -Filter "gen_*.png" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending)
        $latest = Join-Path $dir "latest.png"
        if (Test-Path -LiteralPath $latest -PathType Leaf) { $candidates += (Get-Item -LiteralPath $latest) }

        $now = Get-Date
        $seen = @{}
        foreach ($src in $candidates) {
            if (-not $src) { continue }
            if ($seen.ContainsKey($src.FullName)) { continue }
            $seen[$src.FullName] = $true
            if (($now - $src.LastWriteTime).TotalSeconds -gt $MaxAgeSec) { continue }
            if ($src.LastWriteTime -lt $StartedAt.AddSeconds(-5)) { continue }
            if ($Width -gt 0 -and $Height -gt 0) {
                $dimOk = Test-SdImageDimensions -Path $src.FullName -Width $Width -Height $Height
                if ($dimOk -eq $false) { continue }
            }
            try {
                $outDir = Split-Path -Parent $target
                if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
                    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
                }
                Copy-Item -LiteralPath $src.FullName -Destination $target -Force -ErrorAction Stop
                Write-Host "  [OK] Salvaged SD output from server cache: $($src.FullName)" -ForegroundColor Green
                return $target
            } catch {
                continue
            }
        }
    } catch {
        return $null
    }
    return $null
}

function Find-LocalStableDiffusionServer {
    <#
    .SYNOPSIS
    Finds a usable local SD server. Order: SD3.5 /ping (IPv4 then IPv6) -> SD3.5 python
    process -> fallback servers. Returns the setup hashtable, or $null if none found.
    Updates the module's active setup and URLs when something is found.
    #>
    [CmdletBinding()]
    param()
    $isVerbose = ($VerbosePreference -eq 'Continue')
    $port = $script:SDPort
    $hostList = @(Get-SdHostCandidates)

    if ($isVerbose) { Write-Host "`n  Scanning for local Stable Diffusion servers..." -ForegroundColor Cyan }

    # 1) SD3.5 /ping on each loopback family
    $foreign = $null
    foreach ($h in $hostList) {
        if ($isVerbose) { Write-Host "    Checking SD3.5 /ping at $(Get-SdBaseUrl -HostName $h -Port $port) ..." -ForegroundColor Gray }
        $probe = Get-SdPingProbe -HostName $h -Port $port
        if ($null -eq $probe) { continue }
        if ($probe.IsAamt) {
            $setup = New-SdSetup -Name "SD3.5 API Server" -HostName $h -Port $port `
                -ApiEndpoint "/v1/images/generations" -HealthEndpoint "/ping" -Type "SD35Server" -Responding $true
            $setup.Loaded = [bool]$probe.Loaded
            $setup.Version = [string]$probe.Version
            Set-SdActiveSetup -Setup $setup
            $script:SDLastGoodPing = Get-Date
            if ($isVerbose) { Write-Host "    [OK] SD3.5 server answered on $h (version $($probe.Version), loaded=$($probe.Loaded))" -ForegroundColor Green }
            return $setup
        }
        if (-not $foreign) { $foreign = $probe }
    }
    if ($foreign) {
        Write-Host "    [WARN] Port $port answers but is not the AAMT SD3.5 server (HTTP $($foreign.StatusCode), version '$($foreign.Version)')." -ForegroundColor Yellow
    }

    # 2) SD3.5 python process (server alive but /ping not answering yet, or busy)
    if (-not $foreign) {
        if ($isVerbose) { Write-Host "    Checking for SD3.5 server process (port $port)..." -ForegroundColor Gray }
        $proc = Find-SdServerProcess -Port $port
        if ($proc) {
            $h = "127.0.0.1"
            if ($script:SDPreferredHost) { $h = [string]$script:SDPreferredHost }
            $setup = New-SdSetup -Name "SD3.5 API Server" -HostName $h -Port $port `
                -ApiEndpoint "/v1/images/generations" -HealthEndpoint "/ping" -Type "SD35Server" -Responding $false
            $setup.ProcessFound = $true
            $setup.ProcessId = [int]$proc.ProcessId
            Set-SdActiveSetup -Setup $setup
            if ($isVerbose) { Write-Host "    [OK] Found SD3.5 server process (PID $($proc.ProcessId)) but /ping did not answer" -ForegroundColor Yellow }
            return $setup
        }
    }

    # 3) Fallback servers
    foreach ($def in $script:KnownSDSetups) {
        if ($def.Type -eq "SD35Server") { continue }
        foreach ($h in $hostList) {
            if (-not (Test-SdTcpPort -HostName $h -Port ([int]$def.Port) -TimeoutMs 300)) { continue }
            if ($isVerbose) { Write-Host "    Checking $($def.Name) on $(Get-SdBaseUrl -HostName $h -Port ([int]$def.Port)) ..." -ForegroundColor Gray }
            $url = (Get-SdBaseUrl -HostName $h -Port ([int]$def.Port)) + [string]$def.HealthEndpoint
            $r = Invoke-SdHttpRequest -Url $url -Method "GET" -TimeoutSec 3
            if ($r.StatusCode -eq 200) {
                $setup = New-SdSetup -Name ([string]$def.Name) -HostName $h -Port ([int]$def.Port) `
                    -ApiEndpoint ([string]$def.ApiEndpoint) -HealthEndpoint ([string]$def.HealthEndpoint) `
                    -Type ([string]$def.Type) -Responding $true
                Set-SdActiveSetup -Setup $setup
                if ($isVerbose) { Write-Host "    [OK] Found $($def.Name)" -ForegroundColor Green }
                return $setup
            }
        }
    }

    if ($isVerbose) { Write-Host "    [FAIL] No Stable Diffusion server detected" -ForegroundColor Red }
    return $null
}

function Test-StableDiffusionConnection {
    <#
    .SYNOPSIS
    $true if a Stable Diffusion server can take requests, otherwise $false.
    Without -Url the server is auto-detected (IPv4 and IPv6). Always returns a [bool].
    #>
    [CmdletBinding()]
    param([string]$Url = "")
    $isVerbose = ($VerbosePreference -eq 'Continue')

    if ([string]::IsNullOrWhiteSpace($Url)) {
        $setup = Find-LocalStableDiffusionServer -Verbose:$isVerbose
        if ($setup -is [hashtable]) {
            if ($setup.Responding) { return $true }
            return [bool](Test-SdBusyGrace -Setup $setup)
        }
        return $false
    }

    $uri = $null
    if (-not [System.Uri]::TryCreate($Url, [System.UriKind]::Absolute, [ref]$uri)) {
        if ($isVerbose) { Write-Host "    [FAIL] Not a valid URL: $Url" -ForegroundColor Red }
        return $false
    }
    if ($isVerbose) { Write-Host "    Testing connection to $Url ..." -ForegroundColor Gray }
    if (-not (Test-SdTcpPort -HostName $uri.DnsSafeHost -Port $uri.Port -TimeoutMs 1500)) {
        if ($isVerbose) { Write-Host "    [FAIL] Port $($uri.Port) is not accepting connections" -ForegroundColor Red }
        return $false
    }
    $base = $uri.GetLeftPart([System.UriPartial]::Authority)
    foreach ($endpoint in @("/ping", "/", "/sdapi/v1/sd-models", "/system_stats", "/api/v1/app/version")) {
        $r = Invoke-SdHttpRequest -Url ($base + $endpoint) -Method "GET" -TimeoutSec 4
        if ($r.StatusCode -eq 200) {
            if ($isVerbose) { Write-Host "    [OK] Server responded to $endpoint" -ForegroundColor Green }
            return $true
        }
    }
    if ($isVerbose) { Write-Host "    [FAIL] Server did not answer any known health endpoint" -ForegroundColor Red }
    return $false
}

function Stop-StableDiffusionServer {
    <#
    .SYNOPSIS
    Stops the SD3.5 server (graceful /shutdown first) and frees GPU VRAM. Returns [bool].
    #>
    param([string]$ToolsRoot = "")
    $candidates = @()
    if ($ToolsRoot) { $candidates += $ToolsRoot }
    $candidates += (Split-Path $PSScriptRoot -Parent)
    $candidates += $PSScriptRoot
    foreach ($root in $candidates) {
        $stop = Join-Path $root "Stop-StableDiffusionServer.ps1"
        if (Test-Path -LiteralPath $stop) {
            & $stop
            $script:SDLastGoodPing = $null
            return ($LASTEXITCODE -eq 0)
        }
    }
    Write-Host "Stop script missing: Stop-StableDiffusionServer.ps1" -ForegroundColor Red
    return $false
}

function Start-StableDiffusionServerIfNeeded {
    <#
    .SYNOPSIS
    Makes sure the SD3.5 server is running; starts it when it is not. Returns [bool].
    -NoStart only checks. -TimeoutSec is how long to wait for /ping after launching.
    #>
    [CmdletBinding()]
    param(
        [string]$ToolsRoot = $PSScriptRoot,
        [int]$TimeoutSec = 300,
        [switch]$NoStart
    )
    $isVerbose = ($VerbosePreference -eq 'Continue')
    $port = $script:SDPort
    if ([string]::IsNullOrWhiteSpace($ToolsRoot)) { $ToolsRoot = $PSScriptRoot }
    Write-Host "`n  Checking SD3.5 server status..." -ForegroundColor Cyan

    if (Test-StableDiffusionConnection -Verbose:$isVerbose) {
        Write-Host "  [OK] SD server is running ($($script:ActiveSDSetup.BaseUrl))" -ForegroundColor Green
        return $true
    }

    # Is port 1338 held by a foreign HTTP server (for example Starfield sd_server.py)?
    $foreign = $null
    foreach ($h in @(Get-SdHostCandidates)) {
        $probe = Get-SdPingProbe -HostName $h -Port $port -Attempts 1
        if ($probe -and -not $probe.IsAamt) { $foreign = $probe; break }
    }
    $listeners = @(Get-SdListenerPid -Port $port)

    if ($foreign) {
        Write-Host "  [WARN] Port $port is owned by a non-AAMT server (PID(s): $($listeners -join ', '))." -ForegroundColor Yellow
        if ($NoStart) { return $false }
        Write-Host "  Replacing it (AAMT owns this port)..." -ForegroundColor Yellow
        $null = Stop-StableDiffusionServer
        Start-Sleep -Seconds 1
    } elseif ($listeners.Count -gt 0) {
        $ownerPid = $listeners[0]
        $name = "unknown"
        try { $name = (Get-Process -Id $ownerPid -ErrorAction Stop).ProcessName } catch { }
        Write-Host "  Port $port is held by PID $ownerPid ($name) but /ping is not answering; waiting up to 20s..." -ForegroundColor Yellow
        for ($i = 0; $i -lt 10; $i++) {
            Start-Sleep -Seconds 2
            if (Test-StableDiffusionConnection) {
                Write-Host "  [OK] Server is now responding" -ForegroundColor Green
                return $true
            }
        }
        Write-Host "  [ERROR] Port $port is blocked by PID $ownerPid ($name). Stop it: Stop-Process -Id $ownerPid -Force" -ForegroundColor Red
        return $false
    }

    if ($NoStart) {
        Write-Host "  [INFO] SD server not running (-NoStart given)." -ForegroundColor Yellow
        return $false
    }

    $startScript = $null
    $searchRoots = @($ToolsRoot, (Split-Path $ToolsRoot -Parent), (Split-Path $PSScriptRoot -Parent), $PSScriptRoot)
    foreach ($root in $searchRoots) {
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        $candidate = Join-Path $root $script:ServerStartupScript
        if (Test-Path -LiteralPath $candidate) { $startScript = $candidate; break }
    }
    if (-not $startScript) {
        Write-Host "  [ERROR] Cannot find $($script:ServerStartupScript)" -ForegroundColor Red
        return $false
    }

    if (-not $env:SD_IDLE_SHUTDOWN_SEC) { $env:SD_IDLE_SHUTDOWN_SEC = "180" }
    $psExe = "powershell.exe"
    if (-not (Get-Command $psExe -ErrorAction SilentlyContinue)) { $psExe = "pwsh" }
    Write-Host "  Starting SD3.5 server: $startScript" -ForegroundColor Cyan
    $proc = $null
    try {
        $psArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ('"' + $startScript + '"'), "-NoStatusGui")
        $proc = Start-Process -FilePath $psExe -ArgumentList $psArgs -WindowStyle Hidden -PassThru
    } catch {
        Write-Host "  [ERROR] Could not launch start script: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $lastNote = Get-Date
    while ((Get-Date) -lt $deadline) {
        if (Test-StableDiffusionConnection) {
            $state = "loading model"
            if ($script:ActiveSDSetup.Loaded) { $state = "model loaded" }
            Write-Host "  [OK] SD server is up ($state) at $($script:ActiveSDSetup.BaseUrl)" -ForegroundColor Green
            return $true
        }
        if ($proc -and $proc.HasExited) {
            Write-Host "  [ERROR] Start script exited (code $($proc.ExitCode)) before the server answered" -ForegroundColor Red
            return $false
        }
        if (((Get-Date) - $lastNote).TotalSeconds -ge 15) {
            Write-Host "    ...still waiting for SD server" -ForegroundColor Gray
            $lastNote = Get-Date
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "  [ERROR] Timed out after ${TimeoutSec}s waiting for the SD server" -ForegroundColor Red
    return $false
}

function Start-SDServerIfNeeded {
    <#
    .SYNOPSIS
    Short name used by the main AAMT scripts. Forwards to Start-StableDiffusionServerIfNeeded.
    Always returns [bool]; errors are reported, never thrown.
    #>
    [CmdletBinding()]
    param(
        [string]$ToolsRoot = "",
        [int]$TimeoutSec = 300,
        [switch]$NoStart
    )
    $isVerbose = ($VerbosePreference -eq 'Continue')
    $root = $ToolsRoot
    if ([string]::IsNullOrWhiteSpace($root)) { $root = $PSScriptRoot }
    try {
        if ($isVerbose) { Write-Host "Invoking Start-StableDiffusionServerIfNeeded..." -ForegroundColor Gray }
        $ok = Start-StableDiffusionServerIfNeeded -ToolsRoot $root -TimeoutSec $TimeoutSec -NoStart:$NoStart -Verbose:$isVerbose
        return [bool]($ok | Select-Object -Last 1)
    } catch {
        Write-Host "  [ERROR] Start-StableDiffusionServerIfNeeded failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Invoke-StableDiffusionGeneration {
    <#
    .SYNOPSIS
    Generates image(s). Returns base64 string(s); wrap the call in @() when you need
    an array (a single image comes back as one string). Supports the SD3.5 server (primary), A1111 and OpenAI-style servers.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [string]$NegativePrompt = "",
        [int]$Width = 1024,
        [int]$Height = 1024,
        [int]$Steps = 28,
        [double]$GuidanceScale = 7.0,
        [int]$Seed = 0,
        [int]$NumOutputs = 1,
        [string]$ApiUrl = "",
        [switch]$AutoStartServer,
        [switch]$EnhanceWithOllama,
        [string]$OllamaUrl = "http://localhost:11434",
        [string]$ReferenceImagePath = "",
        [double]$ImageStrength = 0.7
    )
    $isVerbose = ($VerbosePreference -eq 'Continue')

    if ($EnhanceWithOllama) { $Prompt = Get-SdEnhancedPrompt -Prompt $Prompt }

    # Server must be reachable (optionally start it).
    if (-not (Test-StableDiffusionConnection -Verbose:$isVerbose)) {
        if ($AutoStartServer) {
            if (-not (Start-SDServerIfNeeded -Verbose:$isVerbose)) {
                throw "SD server is not running and could not be started."
            }
        } else {
            throw "SD server is not reachable on port $($script:SDPort). Run Start-StableDiffusionServer.ps1 or pass -AutoStartServer."
        }
    }
    $setup = $script:ActiveSDSetup

    # Resolve the API URL. An explicit -ApiUrl is honoured; otherwise use the detected one.
    $explicitUrl = -not [string]::IsNullOrWhiteSpace($ApiUrl)
    if (-not $explicitUrl) { $ApiUrl = [string]$script:StableDiffusionApiUrl }
    $parsedUri = $null
    if ([string]::IsNullOrWhiteSpace($ApiUrl) -or -not [System.Uri]::TryCreate($ApiUrl, [System.UriKind]::Absolute, [ref]$parsedUri)) {
        $ApiUrl = [string]$script:StableDiffusionApiUrl
        if (-not [System.Uri]::TryCreate($ApiUrl, [System.UriKind]::Absolute, [ref]$parsedUri)) {
            throw "Stable Diffusion API URL is invalid: '$ApiUrl'"
        }
    }
    $apiType = [string]$setup.Type
    if ($explicitUrl -and $parsedUri.Port -ne [int]$setup.Port) { $apiType = "APIServer" }

    if ([string]::IsNullOrWhiteSpace($NegativePrompt)) { $NegativePrompt = $script:DefaultGenerationParams.NegativePrompt }

    $referenceImageBase64 = $null
    if ($ReferenceImagePath -and (Test-Path -LiteralPath $ReferenceImagePath)) {
        try {
            $referenceImageBase64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes((Resolve-SdOutputPath -Path $ReferenceImagePath)))
            Write-Host "  Using reference image: $(Split-Path -Leaf $ReferenceImagePath) (strength $ImageStrength)" -ForegroundColor Cyan
        } catch {
            Write-Host "  [WARN] Failed to load reference image: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

    $mode = "Text-to-Image"
    if ($referenceImageBase64) { $mode = "Image-to-Image" }
    Write-Host "  Generating image with $($setup.Name) ($mode)..." -ForegroundColor Cyan
    Write-Host "    ${Width}x${Height}, steps $Steps, guidance $GuidanceScale -> $ApiUrl" -ForegroundColor Gray

    # Build the JSON body for the detected API flavour.
    $body = @{}
    switch ($apiType) {
        "A1111" {
            $body = @{
                prompt = $Prompt
                negative_prompt = $NegativePrompt
                width = $Width
                height = $Height
                steps = $Steps
                cfg_scale = $GuidanceScale
                sampler_name = "DPM++ 2M"
                sampler_index = "DPM++ 2M"
                seed = -1
            }
            if ($Seed -ne 0) { $body.seed = $Seed }
            if ($NumOutputs -gt 1) { $body.n_iter = $NumOutputs }
            if ($referenceImageBase64) {
                $ApiUrl = $ApiUrl -replace "/txt2img", "/img2img"
                $body.init_images = @($referenceImageBase64)
                $body.denoising_strength = $ImageStrength
            }
        }
        "ComfyUI" {
            throw "ComfyUI needs a workflow JSON; use the AAMT SD3.5 server or AUTOMATIC1111."
        }
        "SD35Server" {
            $body = @{
                prompt = $Prompt
                negative_prompt = $NegativePrompt
                width = $Width
                height = $Height
                size = "${Width}x${Height}"
                steps = $Steps
                guidance_scale = $GuidanceScale
                n = 1
            }
            if ($Seed -ne 0) { $body.seed = $Seed }
            if ($referenceImageBase64) {
                $body.image = $referenceImageBase64
                $body.strength = $ImageStrength
            }
        }
        default {
            $body = @{
                model = "stable-diffusion-3"
                prompt = $Prompt
                n = $NumOutputs
                size = "${Width}x${Height}"
                quality = "standard"
                response_format = "b64_json"
            }
            if ($NegativePrompt) { $body.negative_prompt = $NegativePrompt }
            if ($Steps -gt 0) { $body.steps = $Steps }
            if ($GuidanceScale -gt 0) { $body.guidance_scale = $GuidanceScale }
            if ($Seed -ne 0) { $body.seed = $Seed }
            if ($referenceImageBase64) {
                $body.image = $referenceImageBase64
                $body.strength = $ImageStrength
            }
        }
    }
    $jsonBody = $body | ConvertTo-Json -Depth 6 -Compress

    # POST. A refused/unreachable connection is retried once after re-detecting the
    # server (covers a restart or a v4/v6 switch); a timeout is NOT retried because the
    # server may still be rendering and the caller can salvage the output from disk.
    $reply = $null
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        $reply = Invoke-SdHttpRequest -Url $ApiUrl -Method "POST" -JsonBody $jsonBody -TimeoutSec $script:SDHttpTimeoutSec
        if ($reply.StatusCode -gt 0 -or $reply.TimedOut) { break }
        if ($attempt -eq 1) {
            Write-Host "    [WARN] Connection failed ($($reply.Error)); re-detecting server and retrying once..." -ForegroundColor Yellow
            Start-Sleep -Seconds 2
            $null = Find-LocalStableDiffusionServer
            if (-not $explicitUrl) { $ApiUrl = [string]$script:StableDiffusionApiUrl }
        }
    }

    if ($reply.TimedOut) {
        throw "Image generation timed out after $($script:SDHttpTimeoutSec)s (set AAMT_SD_HTTP_TIMEOUT_SEC to raise it)."
    }
    if ($reply.StatusCode -eq 0) {
        throw "Image generation failed: could not reach $ApiUrl ($($reply.Error))"
    }
    if (-not $reply.Ok) {
        if ($reply.StatusCode -eq 426) {
            throw "HTTP 426 from ${ApiUrl}: a non-AAMT service owns this port (not the SD3.5 server). Stop it and restart Start-StableDiffusionServer.ps1."
        }
        $snippet = [string]$reply.Body
        if ($snippet.Length -gt 500) { $snippet = $snippet.Substring(0, 500) }
        throw "Image generation failed: HTTP $($reply.StatusCode) from ${ApiUrl}: $snippet"
    }
    $script:SDLastGoodPing = Get-Date

    $images = @(Get-SdImagesFromResponse -Raw $reply.Body -ApiType $apiType)
    Write-Host "  [OK] Generated $($images.Count) image(s)" -ForegroundColor Green
    return $images
}

function Save-StableDiffusionImage {
    <#
    .SYNOPSIS
    Saves a base64 image to disk. Returns the full output path.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Base64Image,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )
    try {
        $target = Resolve-SdOutputPath -Path $OutputPath
        $payload = $Base64Image.Trim()
        if ($payload -match '^data:image/[^;]+;base64,') {
            $payload = $payload.Substring($payload.IndexOf(',') + 1)
        }
        $payload = ($payload -replace '\s', '') -replace '\\/', '/'
        $imageBytes = [Convert]::FromBase64String($payload)
        if ($imageBytes.Length -lt 100) { throw "decoded image is only $($imageBytes.Length) bytes" }
        $outDir = Split-Path -Parent $target
        if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
            New-Item -ItemType Directory -Path $outDir -Force | Out-Null
        }
        [System.IO.File]::WriteAllBytes($target, $imageBytes)
        Write-Host "  [OK] Image saved: $target" -ForegroundColor Green
        return $target
    } catch {
        throw "Failed to save image: $($_.Exception.Message)"
    }
}

function Invoke-SdGenerationViaPython {
    <#
    .SYNOPSIS
    Generates through sd_http_client.py (HTTP/1.1, GPU lock, disk salvage). Returns the output path.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [string]$NegativePrompt = "",
        [int]$Width = 1024,
        [int]$Height = 1024,
        [int]$Steps = 28,
        [double]$GuidanceScale = 7.0,
        [int]$Seed = 0,
        [string]$ApiUrl = "",
        [double]$TimeoutSec = 0,
        [string]$ReferenceImagePath = "",
        [double]$ImageStrength = 0.65
    )
    $pythonClient = Join-Path $PSScriptRoot "sd_http_client.py"
    if (-not (Test-Path -LiteralPath $pythonClient)) { throw "Python SD client not found: $pythonClient" }

    $pythonCmd = $null
    if (Get-Command python -ErrorAction SilentlyContinue) { $pythonCmd = "python" }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $pythonCmd = "python3" }
    else { throw "Python not found in PATH" }

    $target = Resolve-SdOutputPath -Path $OutputPath
    $outDir = Split-Path -Parent $target
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }

    $timeout = [double]$script:SDHttpTimeoutSec
    if ($TimeoutSec -gt 0) { $timeout = $TimeoutSec }
    $pyArgs = @(
        $pythonClient, "--prompt", $Prompt, "--output", $target,
        "--negative-prompt", $NegativePrompt,
        "--width", "$Width", "--height", "$Height",
        "--steps", "$Steps", "--guidance-scale", "$GuidanceScale", "--seed", "$Seed",
        "--timeout", "$timeout"
    )
    if ($ApiUrl) { $pyArgs += @("--api-url", $ApiUrl) }
    if ($ReferenceImagePath) {
        $pyArgs += @("--reference-image", (Resolve-SdOutputPath -Path $ReferenceImagePath), "--image-strength", "$ImageStrength")
    }

    Write-Host "  Using Python SD client (HTTP/1.1, timeout=${timeout}s)..." -ForegroundColor Cyan
    # Out-Host keeps the client's stdout out of this function's return value.
    & $pythonCmd @pyArgs | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Python SD client failed (exit $LASTEXITCODE)" }
    if (-not (Test-Path -LiteralPath $target)) { throw "Python SD client did not create output: $target" }
    return $target
}

function Generate-AssetImageWithSD3 {
    <#
    .SYNOPSIS
    Full workflow: optional Ollama prompt enhancement, generate with SD3.5, save the image.
    Returns the saved path (string), or an array of paths when several images came back.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [string]$NegativePrompt = "",
        [int]$Width = 1024,
        [int]$Height = 1024,
        [int]$Steps = 28,
        [double]$GuidanceScale = 7.0,
        [int]$Seed = 0,
        [switch]$EnhanceWithOllama = $true,
        [switch]$AutoStartServer = $false,
        [string]$ApiUrl = "",
        [string]$ReferenceImagePath = "",
        [double]$ImageStrength = 0.7
    )
    $isVerbose = ($VerbosePreference -eq 'Continue')
    $OutputPath = Resolve-SdOutputPath -Path $OutputPath

    # Enhance ONCE here; downstream calls are told not to enhance again.
    if ($EnhanceWithOllama) { $Prompt = Get-SdEnhancedPrompt -Prompt $Prompt }

    if (-not (Test-StableDiffusionConnection -Verbose:$isVerbose)) {
        if ($AutoStartServer) {
            if (-not (Start-SDServerIfNeeded -Verbose:$isVerbose)) {
                throw "SD server is not running and could not be started."
            }
        } else {
            throw "SD server is not reachable on port $($script:SDPort). Start it or pass -AutoStartServer."
        }
    }
    $setup = $script:ActiveSDSetup

    # Preferred path: Python HTTP/1.1 client (SD3.5 server only).
    $pythonClient = Join-Path $PSScriptRoot "sd_http_client.py"
    if ($setup.Type -eq "SD35Server" -and (Test-Path -LiteralPath $pythonClient)) {
        $pyStarted = Get-Date
        try {
            $pyUrl = $ApiUrl
            if ([string]::IsNullOrWhiteSpace($pyUrl)) { $pyUrl = [string]$script:StableDiffusionApiUrl }
            return (Invoke-SdGenerationViaPython `
                -Prompt $Prompt -OutputPath $OutputPath -NegativePrompt $NegativePrompt `
                -Width $Width -Height $Height -Steps $Steps -GuidanceScale $GuidanceScale -Seed $Seed `
                -ApiUrl $pyUrl -ReferenceImagePath $ReferenceImagePath -ImageStrength $ImageStrength)
        } catch {
            Write-Host "  [WARN] Python SD client failed: $($_.Exception.Message)" -ForegroundColor Yellow
            $salvaged = Get-SalvagedSdOutput -OutputPath $OutputPath -StartedAt $pyStarted -Width $Width -Height $Height
            if ($salvaged) { return $salvaged }
            Write-Host "  [INFO] Falling back to the PowerShell HTTP client..." -ForegroundColor Gray
        }
    }

    # Fallback: PowerShell HTTP client with OOM retry and disk salvage.
    $startedAt = Get-Date
    $images = @()
    try {
        $images = @(Invoke-StableDiffusionGeneration `
            -Prompt $Prompt -NegativePrompt $NegativePrompt -Width $Width -Height $Height `
            -Steps $Steps -GuidanceScale $GuidanceScale -Seed $Seed `
            -EnhanceWithOllama:$false -AutoStartServer:$AutoStartServer `
            -ApiUrl $ApiUrl -ReferenceImagePath $ReferenceImagePath -ImageStrength $ImageStrength)
    } catch {
        $errText = $_.Exception.Message
        $salvaged = Get-SalvagedSdOutput -OutputPath $OutputPath -StartedAt $startedAt -Width $Width -Height $Height
        if ($salvaged) { return $salvaged }

        if (Test-SdOomError -Message $errText) {
            $redW = [Math]::Max(512, [int]($Width * 0.66))
            $redH = [Math]::Max(512, [int]($Height * 0.66))
            $redSteps = [Math]::Max(12, [int]($Steps * 0.6))
            Write-Host "  [SD] CUDA OOM detected; retrying at ${redW}x${redH}@${redSteps}..." -ForegroundColor Yellow
            $startedAt = Get-Date
            try {
                $images = @(Invoke-StableDiffusionGeneration `
                    -Prompt $Prompt -NegativePrompt $NegativePrompt -Width $redW -Height $redH -Steps $redSteps `
                    -GuidanceScale $GuidanceScale -Seed $Seed -EnhanceWithOllama:$false -AutoStartServer:$false `
                    -ApiUrl $ApiUrl -ReferenceImagePath $ReferenceImagePath -ImageStrength $ImageStrength)
            } catch {
                $salvaged = Get-SalvagedSdOutput -OutputPath $OutputPath -StartedAt $startedAt -Width $redW -Height $redH
                if ($salvaged) { return $salvaged }
                throw
            }
        } else {
            throw
        }
    }

    if ($images.Count -eq 0) { throw "No images were generated" }

    $savedPath = Save-StableDiffusionImage -Base64Image ([string]$images[0]) -OutputPath $OutputPath
    if ($images.Count -gt 1) {
        $baseDir = [System.IO.Path]::GetDirectoryName($OutputPath)
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($OutputPath)
        $extension = [System.IO.Path]::GetExtension($OutputPath)
        $paths = @($savedPath)
        for ($i = 1; $i -lt $images.Count; $i++) {
            $extra = Join-Path $baseDir ("{0}_{1}{2}" -f $baseName, $i, $extension)
            $paths += Save-StableDiffusionImage -Base64Image ([string]$images[$i]) -OutputPath $extra
        }
        return $paths
    }
    return $savedPath
}

# ============================================================
# EXPORTS (private helpers above are intentionally NOT exported)
# ============================================================
Export-ModuleMember -Function `
    Find-LocalStableDiffusionServer, `
    Test-StableDiffusionConnection, `
    Start-SDServerIfNeeded, `
    Start-StableDiffusionServerIfNeeded, `
    Stop-StableDiffusionServer, `
    Invoke-StableDiffusionGeneration, `
    Save-StableDiffusionImage, `
    Invoke-SdGenerationViaPython, `
    Generate-AssetImageWithSD3, `
    Get-FreeVramMB, `
    Get-SalvagedSdOutput, `
    Test-SdOomError
