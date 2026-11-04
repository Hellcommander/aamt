<#
.SYNOPSIS
    SD3.5-only Stable Diffusion integration for AI-Assisted Modding Tools (AAMT).

.DESCRIPTION
    One server (SD3.5 Medium, default port 1338), one endpoint (/v1/images/generations),
    one payload shape. No AUTOMATIC1111 / ComfyUI / InvokeAI / legacy-server code paths.

    Request payload (exactly these keys, in this order):
        model, prompt, negative_prompt, size, width, height, steps, guidance_scale,
        response_format, seed, image, strength, n

    NOTE ON width/height: the AAMT server (sd35_server.py) reads width and height and
    ignores "size". Without them every image is generated at 512x512. They are therefore
    sent alongside "size". If your server really rejects them, delete the two lines
    marked WIDTH-HEIGHT in Invoke-StableDiffusionGeneration.

    Strict mode (default ON; AAMT_SD_STRICT=0 or -Strict:$false turns it off):
      - any SD error aborts; there is no fallback of any kind
      - a PNG whose size differs from the requested size is an error (else a warning)
      - the server must identify as the AAMT SD3.5 server (aamt-1338*) unless
        AAMT_SD_ACCEPT_FOREIGN=1 is set
    These checks are errors in BOTH modes: HTTP status other than 200, missing data or
    b64_json, undecodable base64, not a PNG, empty PNG, all-white / all-black /
    fully-transparent / single-colour image, and /ping reporting cuda=false.

    Logging: pass -Verbose (or set AAMT_SD_VERBOSE=1) to log the exact payload (the image
    field is shown as a length, not megabytes of base64), the response (truncated), CUDA
    and pipeline status, decoded PNG size and the output path.

    IPv4 and IPv6 loopback (127.0.0.1 and [::1]) are both probed. Overrides:
    AAMT_SD_HOST, AAMT_SD_IPV6=0, AAMT_SD_PORT.

    File is plain ASCII, UTF-8 without BOM. Keep it that way for Windows PowerShell 5.1.
#>

# ============================================================
# CONFIGURATION
# ============================================================

$script:SDPort = 1338
$parsedPort = 0
if ($env:AAMT_SD_PORT -and [int]::TryParse($env:AAMT_SD_PORT, [ref]$parsedPort) -and $parsedPort -gt 0 -and $parsedPort -lt 65536) {
    $script:SDPort = $parsedPort
}

$script:SDApiPath = "/v1/images/generations"      # the ONLY generation endpoint
$script:SDModelName = "stable-diffusion-3-medium"
$script:SDStrictDefault = ($env:AAMT_SD_STRICT -ne '0')
$script:SDAcceptForeign = ($env:AAMT_SD_ACCEPT_FOREIGN -eq '1')
$script:ServerStartupScript = "Start-StableDiffusionServer.ps1"
$script:DefaultNegativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark, simple, basic"

$script:SDPreferredHost = $null      # loopback host that answered last (127.0.0.1 or ::1)
$script:SDLastGoodPing = $null       # [datetime] of the last successful /ping

# /ping can be slow while torch loads or renders: generous timeout, one retry.
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

# Finite read timeout; SD3.5 Medium with CPU offload can take many minutes per image.
$script:SDHttpTimeoutSec = 3600
$parsedTimeout = 0
if ($env:AAMT_SD_HTTP_TIMEOUT_SEC -and [int]::TryParse($env:AAMT_SD_HTTP_TIMEOUT_SEC, [ref]$parsedTimeout) -and $parsedTimeout -gt 0) {
    $script:SDHttpTimeoutSec = $parsedTimeout
}

# ============================================================
# PRIVATE HELPERS (not exported)
# ============================================================

function Write-SdLog {
    param([string]$Message)
    if ($env:AAMT_SD_VERBOSE -eq '1') {
        Write-Host "  [SD] $Message" -ForegroundColor DarkGray
    } else {
        Write-Verbose "[SD] $Message"
    }
}

function Get-SdNoCudaMessage {
    # Exact required text; the dash is built from a code point so this file stays ASCII.
    return ("SD3.5 server is running without CUDA " + [char]0x2014 + " image generation aborted.")
}

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
    param([string]$HostName, [int]$Port, [bool]$Responding = $false)
    return @{
        Name = "SD3.5 API Server"
        Host = $HostName
        Port = $Port
        BaseUrl = (Get-SdBaseUrl -HostName $HostName -Port $Port)
        ApiEndpoint = $script:SDApiPath
        HealthEndpoint = "/ping"
        Type = "SD35Server"
        Responding = $Responding
        Loaded = $false
        Loading = $false
        Version = ""
        HasCuda = $false      # does /ping report a "cuda" field at all?
        Cuda = $false
        DeviceCount = -1
        ProcessFound = $false
        ProcessId = 0
    }
}

function Set-SdActiveSetup {
    param([hashtable]$Setup)
    $script:ActiveSDSetup = $Setup
    $script:StableDiffusionUrl = [string]$Setup.BaseUrl
    $script:StableDiffusionApiUrl = ([string]$Setup.BaseUrl) + $script:SDApiPath
    if ($Setup.Host) { $script:SDPreferredHost = [string]$Setup.Host }
}

function Resolve-SdOutputPath {
    param([string]$Path)
    return $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}

function Get-SdMember {
    # Reads a member from either a PSCustomObject or a dictionary (5.1 big-JSON fallback).
    param($Object, [string]$Name)
    if ($null -eq $Object) { return $null }
    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
        return $null
    }
    $prop = $Object.PSObject.Properties[$Name]
    if ($prop) { return $prop.Value }
    return $null
}

function ConvertFrom-SdJson {
    # Windows PowerShell 5.1 ConvertFrom-Json fails above 2 MB; fall back to a serializer
    # without a length cap.
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

function Test-SdTcpPort {
    # True if any address of HostName accepts a TCP connection (IPv4, IPv6 or DNS name).
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
    # The single place that builds an HTTP/1.1 request. Never throws. Returns a hashtable:
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
        try { $handler.UseProxy = $false } catch { }   # loopback never goes through a proxy
        $client = [System.Net.Http.HttpClient]::new($handler)
        $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSec)
        $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::new($Method), $Url)
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
            if ($ex.GetType().Name -match 'TaskCanceled|OperationCanceled|Timeout') { $result.TimedOut = $true }
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
                HasCuda = $false
                Cuda = $false
                DeviceCount = -1
                IsAamt = $false
                Accepted = $false
                Raw = [string]$r.Body
            }
            if ($r.StatusCode -eq 200 -and $r.Body) {
                try {
                    $data = $r.Body | ConvertFrom-Json
                    $names = @($data.PSObject.Properties.Name)
                    if ($names -contains 'version' -and $data.version) { $probe.Version = [string]$data.version }
                    if ($names -contains 'loaded') { $probe.Loaded = [bool]$data.loaded }
                    if ($names -contains 'loading') { $probe.Loading = [bool]$data.loading }
                    if ($names -contains 'generating') { $probe.Generating = [bool]$data.generating }
                    if ($names -contains 'cuda') {
                        $probe.HasCuda = $true
                        $probe.Cuda = ($data.cuda -eq $true)
                    }
                    if ($names -contains 'device_count') { $probe.DeviceCount = [int]$data.device_count }
                } catch {
                    # not JSON: stays unaccepted
                }
            }
            $probe.IsAamt = $probe.Version.StartsWith("aamt-1338")
            $probe.Accepted = ($probe.IsAamt -or ($script:SDAcceptForeign -and $r.StatusCode -eq 200))
            return $probe
        }
        if ($r.Refused) { return $null }   # nothing listening on this family
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
    # The AAMT server.py python process (not sd_server.py of other tools).
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
    # A server that is not answering /ping right now is still "up" when its port accepts
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
        Write-Host "  [SD] /ping not answering but the SD3.5 process owns the port; treating server as busy" -ForegroundColor Yellow
        return $true
    }
    return $false
}

function Assert-SdCuda {
    # Aborts when the server reports it is not running on CUDA. A server that does not
    # report a "cuda" field at all (the AAMT server today) cannot be checked: warn only.
    param([hashtable]$Setup)
    Write-SdLog ("pipeline status: loaded=" + $Setup.Loaded + " loading=" + $Setup.Loading + " version=" + $Setup.Version)
    if ($Setup.HasCuda) {
        Write-SdLog ("CUDA status: cuda=" + $Setup.Cuda + " device_count=" + $Setup.DeviceCount)
        if (-not $Setup.Cuda) { throw (Get-SdNoCudaMessage) }
        if ($Setup.DeviceCount -ge 0 -and $Setup.DeviceCount -lt 1) { throw (Get-SdNoCudaMessage) }
    } else {
        Write-Host "  [WARN] /ping has no 'cuda' field; CUDA status cannot be confirmed (the server itself refuses to load without CUDA)." -ForegroundColor Yellow
    }
    if (-not $Setup.Loaded) {
        Write-Host "  [SD] Pipeline is not loaded yet; the first request will wait for the model to load." -ForegroundColor Gray
    }
}

function Test-SdPngBytes {
    # Validates decoded image bytes. Returns @{ Valid; Reason; Width; Height; Warning }.
    param([byte[]]$Bytes, [int]$Width = 0, [int]$Height = 0, [bool]$Strict = $true)
    $r = @{ Valid = $false; Reason = ""; Width = 0; Height = 0; Warning = "" }
    if ($null -eq $Bytes -or $Bytes.Length -eq 0) { $r.Reason = "PNG is empty (0 bytes)"; return $r }
    if ($Bytes.Length -lt 67) { $r.Reason = "data is $($Bytes.Length) bytes, too small to be a PNG"; return $r }
    $sig = @(0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)
    for ($i = 0; $i -lt 8; $i++) {
        if ($Bytes[$i] -ne $sig[$i]) { $r.Reason = "data does not start with the PNG signature"; return $r }
    }

    $stream = $null
    $bmp = $null
    try {
        try {
            Add-Type -AssemblyName System.Drawing -ErrorAction Stop
        } catch {
            $r.Reason = "System.Drawing is unavailable, so the image content cannot be validated"
            return $r
        }
        $stream = [System.IO.MemoryStream]::new($Bytes)
        $bmp = [System.Drawing.Bitmap]::new($stream)
        $r.Width = $bmp.Width
        $r.Height = $bmp.Height

        # Sample a grid of pixels.
        $cols = [Math]::Min(48, $bmp.Width)
        $rows = [Math]::Min(48, $bmp.Height)
        $opaque = 0
        $white = 0
        $black = 0
        $minLum = 255.0
        $maxLum = 0.0
        for ($yi = 0; $yi -lt $rows; $yi++) {
            $y = [int][Math]::Min($bmp.Height - 1, [Math]::Floor(($yi + 0.5) * $bmp.Height / $rows))
            for ($xi = 0; $xi -lt $cols; $xi++) {
                $x = [int][Math]::Min($bmp.Width - 1, [Math]::Floor(($xi + 0.5) * $bmp.Width / $cols))
                $px = $bmp.GetPixel($x, $y)
                if ($px.A -lt 16) { continue }
                $opaque++
                if ($px.R -ge 250 -and $px.G -ge 250 -and $px.B -ge 250) { $white++ }
                if ($px.R -le 5 -and $px.G -le 5 -and $px.B -le 5) { $black++ }
                $lum = (0.299 * $px.R) + (0.587 * $px.G) + (0.114 * $px.B)
                if ($lum -lt $minLum) { $minLum = $lum }
                if ($lum -gt $maxLum) { $maxLum = $lum }
            }
        }
        if ($opaque -eq 0) { $r.Reason = "image is fully transparent"; return $r }
        if ($white -eq $opaque) { $r.Reason = "image is all white"; return $r }
        if ($black -eq $opaque) { $r.Reason = "image is all black"; return $r }
        if (($maxLum - $minLum) -lt 2) { $r.Reason = "image is a single flat colour"; return $r }

        if ($Width -gt 0 -and $Height -gt 0 -and ($bmp.Width -ne $Width -or $bmp.Height -ne $Height)) {
            $msg = "image is $($bmp.Width)x$($bmp.Height) but $($Width)x$($Height) was requested"
            if ($Strict) { $r.Reason = $msg; return $r }
            $r.Warning = $msg
        }
        $r.Valid = $true
        return $r
    } catch {
        $r.Reason = "PNG could not be decoded: $($_.Exception.Message)"
        return $r
    } finally {
        if ($bmp) { $bmp.Dispose() }
        if ($stream) { $stream.Dispose() }
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

# ------------------------------------------------------------
# Module state. ActiveSDSetup is ALWAYS a hashtable; the URLs are ALWAYS strings.
# ------------------------------------------------------------
$script:ActiveSDSetup = New-SdSetup -HostName "127.0.0.1" -Port $script:SDPort -Responding $false
$script:StableDiffusionUrl = [string]$script:ActiveSDSetup.BaseUrl
$script:StableDiffusionApiUrl = [string]$script:ActiveSDSetup.BaseUrl + $script:SDApiPath

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
        if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) { return $null }
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

function Find-LocalStableDiffusionServer {
    <#
    .SYNOPSIS
    Finds the local SD3.5 server: /ping on IPv4 then IPv6, then the SD3.5 python process.
    Returns the setup hashtable, or $null when there is none. Updates the active setup.
    #>
    [CmdletBinding()]
    param()
    $port = $script:SDPort
    Write-SdLog "scanning for the SD3.5 server on port $port"

    $foreign = $null
    foreach ($h in @(Get-SdHostCandidates)) {
        Write-SdLog ("GET " + (Get-SdBaseUrl -HostName $h -Port $port) + "/ping")
        $probe = Get-SdPingProbe -HostName $h -Port $port
        if ($null -eq $probe) { continue }
        if ($probe.Accepted) {
            $setup = New-SdSetup -HostName $h -Port $port -Responding $true
            $setup.Loaded = [bool]$probe.Loaded
            $setup.Loading = [bool]$probe.Loading
            $setup.Version = [string]$probe.Version
            $setup.HasCuda = [bool]$probe.HasCuda
            $setup.Cuda = [bool]$probe.Cuda
            $setup.DeviceCount = [int]$probe.DeviceCount
            Set-SdActiveSetup -Setup $setup
            $script:SDLastGoodPing = Get-Date
            Write-SdLog ("/ping response: " + $probe.Raw)
            return $setup
        }
        if (-not $foreign) { $foreign = $probe }
    }
    if ($foreign) {
        Write-Host "  [WARN] Port $port answers but is not the AAMT SD3.5 server (HTTP $($foreign.StatusCode), version '$($foreign.Version)'). Set AAMT_SD_ACCEPT_FOREIGN=1 to accept it." -ForegroundColor Yellow
        return $null
    }

    $proc = Find-SdServerProcess -Port $port
    if ($proc) {
        $h = "127.0.0.1"
        if ($script:SDPreferredHost) { $h = [string]$script:SDPreferredHost }
        $setup = New-SdSetup -HostName $h -Port $port -Responding $false
        $setup.ProcessFound = $true
        $setup.ProcessId = [int]$proc.ProcessId
        Set-SdActiveSetup -Setup $setup
        Write-SdLog "SD3.5 process found (PID $($proc.ProcessId)) but /ping did not answer"
        return $setup
    }
    Write-SdLog "no SD3.5 server detected"
    return $null
}

function Test-StableDiffusionConnection {
    <#
    .SYNOPSIS
    $true when the SD3.5 server can take requests, otherwise $false. Always a [bool].
    Without -Url the server is auto-detected (IPv4 and IPv6).
    #>
    [CmdletBinding()]
    param([string]$Url = "")

    if ([string]::IsNullOrWhiteSpace($Url)) {
        $setup = Find-LocalStableDiffusionServer
        if ($setup -is [hashtable]) {
            if ($setup.Responding) { return $true }
            return [bool](Test-SdBusyGrace -Setup $setup)
        }
        return $false
    }

    $uri = $null
    if (-not [System.Uri]::TryCreate($Url, [System.UriKind]::Absolute, [ref]$uri)) {
        Write-SdLog "not a valid URL: $Url"
        return $false
    }
    $probe = Get-SdPingProbe -HostName $uri.DnsSafeHost -Port $uri.Port
    return [bool]($probe -and $probe.Accepted)
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
    Makes sure the SD3.5 server is running and starts it when it is not. Returns [bool].
    -NoStart only checks. -TimeoutSec is how long to wait for /ping after launching.
    #>
    [CmdletBinding()]
    param(
        [string]$ToolsRoot = $PSScriptRoot,
        [int]$TimeoutSec = 300,
        [switch]$NoStart
    )
    $port = $script:SDPort
    if ([string]::IsNullOrWhiteSpace($ToolsRoot)) { $ToolsRoot = $PSScriptRoot }
    Write-Host "`n  Checking SD3.5 server status..." -ForegroundColor Cyan

    if (Test-StableDiffusionConnection) {
        Write-Host "  [OK] SD server is running ($($script:ActiveSDSetup.BaseUrl))" -ForegroundColor Green
        return $true
    }

    # Is the port held by a foreign HTTP server (for example Starfield sd_server.py)?
    $foreign = $null
    foreach ($h in @(Get-SdHostCandidates)) {
        $probe = Get-SdPingProbe -HostName $h -Port $port -Attempts 1
        if ($probe -and -not $probe.Accepted) { $foreign = $probe; break }
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
        $procName = "unknown"
        try { $procName = (Get-Process -Id $ownerPid -ErrorAction Stop).ProcessName } catch { }
        Write-Host "  Port $port is held by PID $ownerPid ($procName) but /ping is not answering; waiting up to 20s..." -ForegroundColor Yellow
        for ($i = 0; $i -lt 10; $i++) {
            Start-Sleep -Seconds 2
            if (Test-StableDiffusionConnection) {
                Write-Host "  [OK] Server is now responding" -ForegroundColor Green
                return $true
            }
        }
        Write-Host "  [ERROR] Port $port is blocked by PID $ownerPid ($procName). Stop it: Stop-Process -Id $ownerPid -Force" -ForegroundColor Red
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
    $root = $ToolsRoot
    if ([string]::IsNullOrWhiteSpace($root)) { $root = $PSScriptRoot }
    try {
        Write-SdLog "Start-SDServerIfNeeded -> Start-StableDiffusionServerIfNeeded"
        $ok = Start-StableDiffusionServerIfNeeded -ToolsRoot $root -TimeoutSec $TimeoutSec -NoStart:$NoStart
        return [bool]($ok | Select-Object -Last 1)
    } catch {
        Write-Host "  [ERROR] Start-StableDiffusionServerIfNeeded failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Invoke-StableDiffusionGeneration {
    <#
    .SYNOPSIS
    Generates ONE image through POST /v1/images/generations and returns it as a validated
    base64 PNG string. Throws on any problem; never returns an unvalidated image.
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
        [string]$ReferenceImagePath = "",
        [double]$ImageStrength = 0.7,
        [switch]$AutoStartServer,
        [switch]$EnhanceWithOllama,
        [bool]$Strict = $script:SDStrictDefault
    )

    if ($EnhanceWithOllama) { $Prompt = Get-SdEnhancedPrompt -Prompt $Prompt }
    if ([string]::IsNullOrWhiteSpace($NegativePrompt)) { $NegativePrompt = $script:DefaultNegativePrompt }

    # 1) Server reachable?
    if (-not (Test-StableDiffusionConnection)) {
        if ($AutoStartServer) {
            if (-not (Start-SDServerIfNeeded)) { throw "SD3.5 server is not running and could not be started." }
        } else {
            throw "SD3.5 server is not reachable on port $($script:SDPort). Run Start-StableDiffusionServer.ps1 or pass -AutoStartServer."
        }
    }
    $setup = $script:ActiveSDSetup

    # 2) CUDA + pipeline status
    Assert-SdCuda -Setup $setup

    # 3) Optional reference image (img2img uses the same endpoint)
    $imageValue = $null
    $strengthValue = $null
    if (-not [string]::IsNullOrWhiteSpace($ReferenceImagePath)) {
        $refPath = Resolve-SdOutputPath -Path $ReferenceImagePath
        if (-not (Test-Path -LiteralPath $refPath -PathType Leaf)) { throw "Reference image not found: $refPath" }
        $imageValue = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($refPath))
        $strengthValue = $ImageStrength
    }
    $seedValue = $null
    if ($Seed -ne 0) { $seedValue = $Seed }

    # 4) Payload: exactly this shape
    $payload = [ordered]@{
        model           = $script:SDModelName
        prompt          = $Prompt
        negative_prompt = $NegativePrompt
        size            = "$($Width)x$($Height)"
        width           = $Width                  # WIDTH-HEIGHT: server ignores "size" (see header)
        height          = $Height                 # WIDTH-HEIGHT
        steps           = $Steps
        guidance_scale  = $GuidanceScale
        response_format = "b64_json"
        seed            = $seedValue
        image           = $imageValue
        strength        = $strengthValue
        n               = 1
    }
    $jsonBody = $payload | ConvertTo-Json -Depth 4 -Compress

    $apiUrl = ([string]$setup.BaseUrl) + $script:SDApiPath
    $logPayload = [ordered]@{}
    foreach ($k in $payload.Keys) { $logPayload[$k] = $payload[$k] }
    if ($null -ne $imageValue) { $logPayload['image'] = "<base64, $($imageValue.Length) chars>" }
    Write-SdLog "POST $apiUrl"
    Write-SdLog ("payload: " + ($logPayload | ConvertTo-Json -Depth 4 -Compress))
    Write-Host "  Generating $($Width)x$($Height), steps $Steps, guidance $GuidanceScale (strict=$Strict)..." -ForegroundColor Cyan

    # 5) Send. No retry, no fallback: any failure stops here.
    $reply = Invoke-SdHttpRequest -Url $apiUrl -Method "POST" -JsonBody $jsonBody -TimeoutSec $script:SDHttpTimeoutSec
    if ($reply.TimedOut) {
        throw "SD server did not answer within $($script:SDHttpTimeoutSec)s (AAMT_SD_HTTP_TIMEOUT_SEC)."
    }
    if ($reply.StatusCode -eq 0) {
        throw "Could not reach the SD server at ${apiUrl}: $($reply.Error)"
    }
    $preview = [string]$reply.Body
    if ($preview.Length -gt 300) { $preview = $preview.Substring(0, 300) + "... [$($reply.Body.Length) chars total]" }
    Write-SdLog "response: HTTP $($reply.StatusCode) $preview"
    if ($reply.StatusCode -ne 200) {
        $detail = "SD server error $($reply.StatusCode): $($reply.Body)"
        Write-Host "  [ERROR] $detail" -ForegroundColor Red
        throw $detail
    }
    $script:SDLastGoodPing = Get-Date

    # 6) Response structure
    $result = $null
    try {
        $result = ConvertFrom-SdJson -Raw ([string]$reply.Body)
    } catch {
        throw "SD3.5 returned a response that is not valid JSON: $($_.Exception.Message)"
    }
    $data = Get-SdMember -Object $result -Name "data"
    if ($null -eq $data -or @($data).Count -eq 0) {
        throw "SD3.5 returned no image data."
    }
    $imgB64 = [string](Get-SdMember -Object (@($data)[0]) -Name "b64_json")
    if ([string]::IsNullOrWhiteSpace($imgB64)) {
        throw "SD3.5 returned empty b64_json."
    }
    if ($imgB64 -match '^data:image/[^;]+;base64,') { $imgB64 = $imgB64.Substring($imgB64.IndexOf(',') + 1) }
    $imgB64 = ($imgB64 -replace '\s', '') -replace '\\/', '/'

    # 7) Decode + validate
    $pngBytes = $null
    try {
        $pngBytes = [Convert]::FromBase64String($imgB64)
    } catch {
        throw "Failed to decode SD3.5 PNG: $($_.Exception.Message)"
    }
    Write-SdLog "decoded PNG: $($pngBytes.Length) bytes"
    $check = Test-SdPngBytes -Bytes $pngBytes -Width $Width -Height $Height -Strict $Strict
    if (-not $check.Valid) {
        throw "SD3.5 returned an unusable image: $($check.Reason)."
    }
    if ($check.Warning) { Write-Host "  [WARN] $($check.Warning)" -ForegroundColor Yellow }
    Write-SdLog "PNG ok: $($check.Width)x$($check.Height)"
    return [string]$imgB64
}

function Save-StableDiffusionImage {
    <#
    .SYNOPSIS
    Validates and saves a base64 PNG. Nothing is written unless the image is valid, and an
    existing file is only replaced by a complete, valid PNG (temp file + move).
    Returns the full output path.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Base64Image,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [int]$Width = 0,
        [int]$Height = 0,
        [bool]$Strict = $script:SDStrictDefault
    )
    $target = Resolve-SdOutputPath -Path $OutputPath
    $payload = $Base64Image.Trim()
    if ($payload -match '^data:image/[^;]+;base64,') { $payload = $payload.Substring($payload.IndexOf(',') + 1) }
    $payload = ($payload -replace '\s', '') -replace '\\/', '/'

    $pngBytes = $null
    try {
        $pngBytes = [Convert]::FromBase64String($payload)
    } catch {
        throw "Failed to decode SD3.5 PNG: $($_.Exception.Message)"
    }
    $check = Test-SdPngBytes -Bytes $pngBytes -Width $Width -Height $Height -Strict $Strict
    if (-not $check.Valid) {
        throw "Refusing to save $target : $($check.Reason)."
    }

    $outDir = Split-Path -Parent $target
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }
    $tmp = $target + ".sdtmp"
    try {
        [System.IO.File]::WriteAllBytes($tmp, $pngBytes)
        Move-Item -LiteralPath $tmp -Destination $target -Force
    } finally {
        if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
    }
    Write-SdLog "saved $($pngBytes.Length) bytes ($($check.Width)x$($check.Height)) -> $target"
    Write-Host "  [OK] Image saved: $target" -ForegroundColor Green
    return $target
}

function Generate-AssetImageWithSD3 {
    <#
    .SYNOPSIS
    Optional Ollama prompt enhancement, generate with SD3.5, validate, save.
    Returns the saved path (string). Throws on any failure; nothing is saved on failure.
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
        [string]$ReferenceImagePath = "",
        [double]$ImageStrength = 0.7,
        [bool]$Strict = $script:SDStrictDefault
    )
    $OutputPath = Resolve-SdOutputPath -Path $OutputPath
    Write-SdLog "output path: $OutputPath"

    $b64 = Invoke-StableDiffusionGeneration `
        -Prompt $Prompt -NegativePrompt $NegativePrompt -Width $Width -Height $Height `
        -Steps $Steps -GuidanceScale $GuidanceScale -Seed $Seed `
        -ReferenceImagePath $ReferenceImagePath -ImageStrength $ImageStrength `
        -EnhanceWithOllama:$EnhanceWithOllama -AutoStartServer:$AutoStartServer -Strict $Strict

    return (Save-StableDiffusionImage -Base64Image ([string]$b64) -OutputPath $OutputPath -Width $Width -Height $Height -Strict $Strict)
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
    Generate-AssetImageWithSD3, `
    Get-FreeVramMB
