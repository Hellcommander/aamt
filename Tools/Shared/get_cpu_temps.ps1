# PowerShell script to get per-core CPU temperatures on Windows
# Uses WMI to query thermal zone temperatures

param(
    [switch]$Json
)

$ErrorActionPreference = "Stop"

try {
    # Query WMI for thermal zone temperatures
    $thermalZones = Get-WmiObject -Namespace "root\wmi" -Class "MSAcpi_ThermalZoneTemperature" -ErrorAction SilentlyContinue
    
    if (-not $thermalZones) {
        # Fallback: Try alternative WMI class
        $thermalZones = Get-WmiObject -Class "Win32_TemperatureProbe" -ErrorAction SilentlyContinue
    }
    
    if ($thermalZones) {
        $results = @()
        $index = 0
        
        foreach ($zone in $thermalZones) {
            if ($zone.CurrentTemperature) {
                # Temperature is in 10th of Kelvin, convert to Celsius
                $tempKelvin = $zone.CurrentTemperature / 10.0
                $tempCelsius = $tempKelvin - 273.15
                
                $result = @{
                    Core = $index
                    Temperature = [math]::Round($tempCelsius, 2)
                    Label = if ($zone.InstanceName) { $zone.InstanceName } else { "Core $index" }
                }
                $results += $result
                $index++
            }
        }
        
        if ($Json) {
            $results | ConvertTo-Json -Compress
        } else {
            # Output as key-value pairs for easy parsing
            foreach ($r in $results) {
                Write-Output "$($r.Core):$($r.Temperature)"
            }
        }
    } else {
        # No thermal zones found, return empty
        if ($Json) {
            Write-Output "[]"
        }
    }
} catch {
    Write-Error "Failed to get CPU temperatures: $_"
    exit 1
}
