$ErrorActionPreference = 'Continue'
Write-Host '=== nvidia ==='
& nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,utilization.memory --format=csv
Write-Host '=== ollama ps ==='
try {
  $ps = Invoke-RestMethod http://127.0.0.1:11434/api/ps -TimeoutSec 8
  if (-not $ps.models) { 'no models loaded' }
  else {
    foreach ($m in $ps.models) {
      'name={0} size={1:N2}GB vram={2:N2}GB pct_vram={3:N0}%' -f $m.name, ($m.size/1GB), ($m.size_vram/1GB), (100.0 * $m.size_vram / [Math]::Max($m.size,1))
    }
  }
} catch { $_.Exception.Message }
Write-Host '=== env ==='
'AAMT_OLLAMA_NUM_GPU=' + $env:AAMT_OLLAMA_NUM_GPU
'AAMT_OLLAMA_GPU_LAYER_FRACTION=' + $env:AAMT_OLLAMA_GPU_LAYER_FRACTION
Write-Host '=== auto num_gpu ==='
& E:\tools\miniconda3\python.exe -c "import sys; sys.path.insert(0,r'D:\games\Steam\steamapps\common\Transcendence\Tools\Shared'); from ollama_integration import get_num_gpu_layers; print(get_num_gpu_layers('wizardlm-uncensored:latest'))"
Write-Host '=== ollama version / gpu ==='
& ollama --version 2>&1
try {
  $c = Invoke-RestMethod http://127.0.0.1:11434/api/version -TimeoutSec 3
  $c | ConvertTo-Json -Compress
} catch {}
# quick generate with num_gpu and check if vram stays
Write-Host '=== probe generate num_gpu=26 ==='
& E:\tools\miniconda3\python.exe -c @"
import requests, time
r = requests.post('http://127.0.0.1:11434/api/generate', json={
  'model':'wizardlm-uncensored:latest','prompt':'hi','stream':False,'keep_alive':'5m',
  'options':{'num_predict':8,'temperature':0,'num_gpu':26}
}, timeout=180)
print('status', r.status_code, 'len', len((r.json() or {}).get('response','')))
ps = requests.get('http://127.0.0.1:11434/api/ps', timeout=5).json()
for m in ps.get('models') or []:
  print('after: size=%.2fGB vram=%.2fGB' % (m['size']/1e9, m.get('size_vram',0)/1e9))
"@
