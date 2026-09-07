#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Asset Generator Control Room - Live Preview Monitor
    Shows per-job cards with live spritesheet previews, progress, and logs as builds complete.
    
.DESCRIPTION
    WPF-based monitoring tool that:
    - Shows per-job cards (Visual Language, FX, Audio, Textures, Spritesheet)
    - Displays live spritesheet previews as files are written
    - Updates progress and logs in real-time
    - Monitors multithreaded generation processes
    - Can be launched independently while generation runs
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$WatchDirectory = "Output",
    
    [Parameter(Mandatory=$false)]
    [int]$MaxCores = 32
)

# Ensure STA mode for WPF
if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -ne [System.Threading.ApartmentState]::STA) {
    Write-Host "ERROR: Must run in STA mode for GUI" -ForegroundColor Red
    Write-Host "Run with: powershell -STA -File AssetGeneratorControlRoom_Monitor.ps1" -ForegroundColor Yellow
    exit 1
}

$ErrorActionPreference = "Continue"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Load WPF assemblies
Add-Type -AssemblyName PresentationFramework, PresentationCore, System.Windows.Forms, System.Drawing, System.Xaml

# --- ViewModel class ---
Add-Type -Language CSharp -TypeDefinition @"
using System;
using System.Windows.Input;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Media.Imaging;

public class RelayCommand : ICommand {
    private readonly Action<object> _execute;
    public RelayCommand(Action<object> exec){ _execute = exec; }
    public bool CanExecute(object parameter){ return true; }
    public event EventHandler CanExecuteChanged;
    public void Execute(object parameter){ _execute(parameter); }
}

public class JobViewModel : INotifyPropertyChanged {
    public event PropertyChangedEventHandler PropertyChanged;
    private void Notify([CallerMemberName] string n = null) { PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n)); }
    public void NotifyProperty(string propertyName) { PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName)); }

    public string Name { get; set; }
    private int percent;
    public int Percent { get { return percent; } set { percent = value; Notify(); } }
    private string status;
    public string Status { get { return status; } set { status = value; Notify(); } }
    private string logText = "";
    public string LogText { get { return logText; } set { logText = value; Notify(); } }

    private System.Windows.Media.ImageSource previewImage;
    public System.Windows.Media.ImageSource PreviewImage { get { return previewImage; } set { previewImage = value; Notify(); } }

    public RelayCommand PauseCommand { get; set; }
    public RelayCommand CancelCommand { get; set; }
    public RelayCommand OpenFolderCommand { get; set; }

    public string OutputFolder;
    public System.Threading.CancellationTokenSource Cts;
    public string JobType; // "Visual", "FX", "Audio", "Textures", "Spritesheet"

    public JobViewModel(string name, string jobType) {
        Name = name;
        JobType = jobType;
        Percent = 0;
        Status = "Queued";
        PauseCommand = new RelayCommand((o)=>{ /* implement pause if desired */ });
        CancelCommand = new RelayCommand((o)=>{ if (Cts!=null) Cts.Cancel(); Status = "Cancelled"; });
        OpenFolderCommand = new RelayCommand((o)=>{ 
            if (!string.IsNullOrEmpty(OutputFolder) && System.IO.Directory.Exists(OutputFolder)) {
                System.Diagnostics.Process.Start("explorer.exe", OutputFolder); 
            }
        });
    }

    public void AppendLog(string line) {
        LogText += line + "\r\n";
        Notify(nameof(LogText));
    }
}
"@

# --- XAML UI ---
[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="Space Whale Asset Generator - Control Room Monitor" Height="800" Width="1200"
        WindowStartupLocation="CenterScreen" Background="#FF1a2a3a">
  <Grid Margin="8">
    <Grid.RowDefinitions>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="*"/>
    </Grid.RowDefinitions>

    <!-- Header -->
    <Border Grid.Row="0" Background="#FF1a2a3a" Padding="15" Margin="0,0,0,8" CornerRadius="5">
      <StackPanel Orientation="Horizontal">
        <TextBlock Text="Space Whale Asset Generator" 
                   FontSize="20" FontWeight="Bold" 
                   Foreground="White" VerticalAlignment="Center"/>
        <TextBlock Name="StatusText" Text="Monitoring..." 
                   FontSize="12" Foreground="#FF66ccff" 
                   Margin="20,0,0,0" VerticalAlignment="Center"/>
        <TextBlock Name="ThreadsText" Text="Threads: 32" 
                   FontSize="12" Foreground="#FF88ffff" 
                   Margin="20,0,0,0" VerticalAlignment="Center"/>
      </StackPanel>
    </Border>

    <!-- Jobs List -->
    <ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto">
      <ItemsControl Name="JobsList">
        <ItemsControl.ItemTemplate>
          <DataTemplate>
            <Border Margin="6" Padding="8" BorderBrush="#FF66ccff" BorderThickness="2" CornerRadius="6" Background="#FF2a3a4a">
              <Grid>
                <Grid.ColumnDefinitions>
                  <ColumnDefinition Width="220"/>
                  <ColumnDefinition Width="*"/>
                </Grid.ColumnDefinitions>

                <!-- Left: preview and basic info -->
                <StackPanel Grid.Column="0" Margin="0,0,12,0">
                  <Border BorderBrush="#FF88ffff" BorderThickness="2" Background="#FF1a2a3a" CornerRadius="3" Padding="2" MinHeight="200" MinWidth="200">
                    <Image Width="200" Height="200" Stretch="Uniform" Source="{Binding PreviewImage}" />
                  </Border>
                  <TextBlock Text="{Binding Name}" FontWeight="Bold" Foreground="White" Margin="0,6,0,0" FontSize="14"/>
                  <TextBlock Text="{Binding Status}" Foreground="#FF66ccff" Margin="0,2,0,0"/>
                  <TextBlock Text="{Binding JobType}" Foreground="#FF88ffff" FontSize="10" Margin="0,2,0,0"/>
                  <!-- Progress Bar - Must be visible and functional -->
                  <StackPanel Margin="0,6,0,0">
                    <ProgressBar Name="JobProgressBar" 
                                Value="{Binding Percent}" 
                                Maximum="100" 
                                Minimum="0" 
                                Height="24" 
                                Width="200"
                                Background="#FF0a1a2a" 
                                Foreground="#FF66ccff" 
                                BorderBrush="#FF66ccff"
                                BorderThickness="1"
                                Margin="0,0,0,4"
                                Visibility="Visible"/>
                    <TextBlock Text="{Binding Percent, StringFormat='{}{0}%'}" 
                              Foreground="#FF88ffff" HorizontalAlignment="Center" FontSize="11" FontWeight="Bold"/>
                  </StackPanel>
                </StackPanel>

                <!-- Right: logs and controls -->
                <StackPanel Grid.Column="1">
                  <DockPanel>
                    <TextBlock Text="Logs" FontWeight="Bold" Foreground="White" DockPanel.Dock="Left" FontSize="14"/>
                    <StackPanel Orientation="Horizontal" DockPanel.Dock="Right">
                      <Button Content="Open Folder" Command="{Binding OpenFolderCommand}" Margin="4,0" 
                             Background="#FF66ccff" Foreground="Black" Padding="8,4" BorderThickness="0" Cursor="Hand"/>
                      <Button Content="Cancel" Command="{Binding CancelCommand}" Margin="4,0" 
                             Background="#FFcc6666" Foreground="White" Padding="8,4" BorderThickness="0" Cursor="Hand"/>
                    </StackPanel>
                  </DockPanel>

                  <Expander Header="Console Output" IsExpanded="True" Margin="0,6,0,0" 
                           Foreground="White" Background="#FF1a2a3a">
                    <TextBox Text="{Binding LogText}" AcceptsReturn="True" VerticalScrollBarVisibility="Auto" 
                            Height="220" IsReadOnly="True" TextWrapping="Wrap" 
                            Background="#FF0a1a2a" Foreground="#FF88ffff" 
                            BorderThickness="0" Padding="4" FontFamily="Consolas" FontSize="10"/>
                  </Expander>
                </StackPanel>
              </Grid>
            </Border>
          </DataTemplate>
        </ItemsControl.ItemTemplate>
      </ItemsControl>
    </ScrollViewer>
  </Grid>
</Window>
"@

# Create Application for proper WPF initialization
# Note: ShowDialog() will start the message pump automatically, but we need to ensure Application exists
if (-not [System.Windows.Application]::Current) {
    $script:app = New-Object System.Windows.Application
    # Set application resources if needed
    $script:app.Resources = New-Object System.Windows.ResourceDictionary
}

# Load XAML
try {
    $reader = New-Object System.Xml.XmlNodeReader $xaml
    $window = [Windows.Markup.XamlReader]::Load($reader)
    
    if (-not $window) {
        Write-Host "ERROR: Failed to load XAML window" -ForegroundColor Red
        exit 1
    }
    
    # Ensure window has proper visual properties
    $window.AllowsTransparency = $false
    $window.WindowStyle = "SingleBorderWindow"
    $window.ResizeMode = "CanResize"
    
    Write-Host "XAML window loaded successfully" -ForegroundColor Green
} catch {
    Write-Host "ERROR loading XAML: $_" -ForegroundColor Red
    Write-Host "Stack: $($_.ScriptStackTrace)" -ForegroundColor Red
    exit 1
}

# Get UI elements
$jobsList = $window.FindName('JobsList')
$statusText = $window.FindName('StatusText')
$threadsText = $window.FindName('ThreadsText')

if (-not $jobsList) {
    Write-Host "ERROR: Could not find JobsList element" -ForegroundColor Red
    exit 1
}

# Jobs collection
$jobs = [System.Collections.ObjectModel.ObservableCollection[JobViewModel]]::new()
$jobsList.ItemsSource = $jobs

# Ensure DataContext is set for proper binding
$jobsList.DataContext = $jobs

Write-Host "UI elements initialized" -ForegroundColor Green
Write-Host "  Jobs collection: $($jobs.Count) items" -ForegroundColor Gray
Write-Host "  ItemsSource bound to JobsList" -ForegroundColor Gray

# File watchers
$script:FileWatchers = @{}
$script:WatchDirectory = $WatchDirectory

# Initialize jobs for known generation tasks
function Initialize-Jobs {
    $baseOutput = Join-Path $PSScriptRoot $WatchDirectory
    
    # Check if this is a test samples directory (flat structure)
    $isTestSamples = $WatchDirectory -like "*TestSamples*" -or (Test-Path (Join-Path $baseOutput "test_*.png"))
    
    if ($isTestSamples) {
        # For test samples, create a single job that monitors the directory
        $testJob = New-Object JobViewModel "Test Samples" "Spritesheet"
        $testJob.OutputFolder = $baseOutput
        $jobs.Add($testJob)
        Write-Host "Initialized test samples job" -ForegroundColor Green
    } else {
        # Visual Language job
        $visualJob = New-Object JobViewModel "Visual Language Assets" "Visual"
        $visualJob.OutputFolder = Join-Path $baseOutput "VisualLanguage"
        $jobs.Add($visualJob)
        
        # FX job
        $fxJob = New-Object JobViewModel "FX Assets" "FX"
        $fxJob.OutputFolder = Join-Path $baseOutput "FX"
        $jobs.Add($fxJob)
        
        # Audio job
        $audioJob = New-Object JobViewModel "Audio Assets" "Audio"
        $audioJob.OutputFolder = Join-Path $baseOutput "Audio"
        $jobs.Add($audioJob)
        
        # Textures job
        $textureJob = New-Object JobViewModel "Texture Generation" "Textures"
        $textureJob.OutputFolder = Join-Path $baseOutput "Textures"
        $jobs.Add($textureJob)
        
        # Spritesheet job
        $spriteJob = New-Object JobViewModel "Spritesheet (120 Facings)" "Spritesheet"
        $spriteJob.OutputFolder = Join-Path $baseOutput "Spritesheets"
        $jobs.Add($spriteJob)
        
        Write-Host "Initialized $($jobs.Count) job cards" -ForegroundColor Green
        Write-Host "  Spritesheet job watching: $($spriteJob.OutputFolder)" -ForegroundColor Gray
    }
}

# Load preview image safely
function Load-PreviewImage {
    param($jobVm, $filePath)
    
    if (-not $jobVm) {
        Write-Host "Warning: Load-PreviewImage called with null jobVm" -ForegroundColor Yellow
        return
    }
    
    if (-not $filePath -or -not (Test-Path $filePath)) {
        Write-Host "Warning: Preview image file not found: $filePath" -ForegroundColor Yellow
        return
    }
    
    if (-not $window -or -not $window.Dispatcher) {
        Write-Host "Warning: Window or Dispatcher not available for image loading" -ForegroundColor Yellow
        return
    }
    
    # Load on UI thread to avoid cross-thread issues
    $action = [System.Action]{
        try {
            $fullPath = (Resolve-Path $filePath -ErrorAction Stop).Path
            
            # Create new BitmapImage with proper settings
            $bi = New-Object System.Windows.Media.Imaging.BitmapImage
            $bi.BeginInit()
            $bi.CacheOption = [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad  # Important: allows file to be overwritten later
            $bi.CreateOptions = [System.Windows.Media.Imaging.BitmapCreateOptions]::IgnoreImageCache
            $bi.UriSource = [Uri]::new($fullPath)
            $bi.EndInit()
            
            # Freeze the image for cross-thread safety
            $bi.Freeze()
            
            # Update the view model - the setter automatically calls Notify()
            $jobVm.PreviewImage = $bi
            $jobVm.Status = "Spritesheet ready"
            
            # Force UI update
            [System.Windows.Input.CommandManager]::InvalidateRequerySuggested()
            
            # Verify image was set and get dimensions
            if ($jobVm.PreviewImage -eq $null) {
                Write-Host "  WARNING: PreviewImage is still null after assignment" -ForegroundColor Yellow
            } else {
                $imgDims = "Unknown"
                try {
                    if ($bi.PixelWidth -gt 0 -and $bi.PixelHeight -gt 0) {
                        $imgDims = "$($bi.PixelWidth)x$($bi.PixelHeight)"
                    }
                } catch { }
                Write-Host "  ✓ PreviewImage set successfully (Size: $imgDims)" -ForegroundColor Green
            }
            
            # Calculate file size for logging
            $fileSizeKB = [math]::Round((Get-Item $filePath).Length / 1024, 2)
            Write-Host "✓ Loaded preview: $(Split-Path $filePath -Leaf) ($fileSizeKB KB)" -ForegroundColor Cyan
        } catch {
            $errorMsg = "Failed to load preview image: $_"
            $jobVm.AppendLog($errorMsg)
            Write-Host "✗ $errorMsg" -ForegroundColor Red
            Write-Host "  File: $filePath" -ForegroundColor Gray
            Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Gray
        }
    }
    $window.Dispatcher.Invoke($action, [System.Windows.Threading.DispatcherPriority]::Normal)
}

# Update job progress
function Update-JobProgress {
    param(
        [JobViewModel]$Job,
        [int]$Percent,
        [string]$Status,
        [string]$LogLine = ""
    )
    
    # Ensure percent is in valid range
    if ($Percent -lt 0) { $Percent = 0 }
    if ($Percent -gt 100) { $Percent = 100 }
    
    $window.Dispatcher.Invoke([action]{
        $Job.Percent = $Percent
        $Job.Status = $Status
        if ($LogLine) {
            $Job.AppendLog($LogLine)
        }
        # Force UI update to ensure progress bar refreshes
        [System.Windows.Input.CommandManager]::InvalidateRequerySuggested()
    }, [System.Windows.Threading.DispatcherPriority]::Normal)
}

# Monitor directory for a specific job
function Start-MonitoringJob {
    param(
        [JobViewModel]$Job,
        [string]$Directory
    )
    
    if (-not (Test-Path $Directory)) {
        New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    }
    
    $watcher = New-Object System.IO.FileSystemWatcher
    $watcher.Path = $Directory
    $watcher.Filter = "*.*"
    $watcher.IncludeSubdirectories = $true
    $watcher.EnableRaisingEvents = $true
    
    # Determine file patterns for this job type
    $imagePatterns = switch ($Job.JobType) {
        "Visual" { @("*.png", "*.jpg", "*.jpeg") }
        "FX" { @("*.png", "*.json") }
        "Audio" { @("*.ogg", "*.wav") }
        "Textures" { @("*_diffuse.png", "*_emission.png", "*_normal.png", "*_roughness.png", "*_metallic.png", "test_texture*.png") }
        "Spritesheet" { @("*spritesheet*.png", "*120*.png", "*facing*.png", "*rotation*.png", "test_spritesheet*.png") }
        default { @("*.png", "*.jpg", "*.jpeg") }
    }
    
    $action = {
        param($source, $e)
        $filePath = $e.FullPath
        $fileName = Split-Path $filePath -Leaf
        $ext = [System.IO.Path]::GetExtension($filePath).ToLower()
        
        # Check if this file matches our job's patterns
        $isMatch = $false
        foreach ($pattern in $imagePatterns) {
            if ($fileName -like $pattern) {
                $isMatch = $true
                break
            }
        }
        
        if ($isMatch -or $ext -in @('.png', '.jpg', '.jpeg', '.ogg', '.wav', '.json', '.xml')) {
            # Update job status with progress
            $currentPercent = $Job.Percent
            if ($currentPercent -lt 50) {
                $newPercent = 50
            } elseif ($currentPercent -lt 90) {
                $newPercent = 90
            } else {
                $newPercent = 95
            }
            
            Update-JobProgress -Job $Job -Percent $newPercent -Status "File detected: $fileName" -LogLine "[$(Get-Date -Format 'HH:mm:ss')] Detected: $fileName"
            
            # If it's an image, load as preview
            if ($ext -in @('.png', '.jpg', '.jpeg')) {
                Write-Host "  [DEBUG] Detected image file: $fileName (JobType: $($Job.JobType))" -ForegroundColor Gray
                # Wait a bit for file to be fully written
                Start-Sleep -Milliseconds 500
                
                # Check if file is accessible
                if (Test-Path $filePath) {
                    Write-Host "  [DEBUG] File exists, loading preview..." -ForegroundColor Gray
                    Load-PreviewImage -jobVm $Job -filePath $filePath
                    Update-JobProgress -Job $Job -Percent 95 -Status "Preview loaded" -LogLine "[$(Get-Date -Format 'HH:mm:ss')] Preview loaded: $fileName"
                } else {
                    Write-Host "  [DEBUG] File not accessible yet: $filePath" -ForegroundColor Yellow
                }
            }
            
            # Special handling for spritesheets - ensure image is loaded
            if ($Job.JobType -eq "Spritesheet" -and ($fileName -like "*spritesheet*" -or $fileName -like "*120*" -or $fileName -like "*facing*")) {
                Write-Host "  [DEBUG] Spritesheet detected: $fileName" -ForegroundColor Cyan
                # Ensure image is loaded for spritesheets (in case it wasn't loaded above)
                if ($ext -in @('.png', '.jpg', '.jpeg') -and (Test-Path $filePath)) {
                    Start-Sleep -Milliseconds 300  # Additional wait for file to be fully written
                    if ($Job.PreviewImage -eq $null) {
                        Write-Host "  [DEBUG] Loading spritesheet preview..." -ForegroundColor Gray
                        Load-PreviewImage -jobVm $Job -filePath $filePath
                    }
                }
                Update-JobProgress -Job $Job -Percent 100 -Status "Spritesheet complete!" -LogLine "[$(Get-Date -Format 'HH:mm:ss')] Spritesheet complete: $fileName"
            }
        }
    }
    
    Register-ObjectEvent -InputObject $watcher -EventName "Created" -Action $action | Out-Null
    Register-ObjectEvent -InputObject $watcher -EventName "Changed" -Action $action | Out-Null
    
    $script:FileWatchers[$Job.Name] = $watcher
    
    # Also check for existing files (load them as previews)
    Write-Host "[DEBUG] Checking for existing files in: $Directory" -ForegroundColor Gray
    $existingFiles = Get-ChildItem -Path $Directory -Recurse -File -ErrorAction SilentlyContinue | 
        Where-Object { [System.IO.Path]::GetExtension($_.FullName).ToLower() -in @('.png', '.jpg', '.jpeg') } |
        Sort-Object LastWriteTime -Descending
    
    Write-Host "[DEBUG] Found $($existingFiles.Count) existing image file(s)" -ForegroundColor Gray
    
    if ($existingFiles) {
        # For test samples or spritesheets, prefer spritesheet images
        $preferredImage = $existingFiles | Where-Object { 
            $_.Name -like "*spritesheet*" -or $_.Name -like "*120*" -or $_.Name -like "*facing*"
        } | Select-Object -First 1
        
        # If no preferred image, use the most recent
        if (-not $preferredImage) {
            $preferredImage = $existingFiles | Select-Object -First 1
        }
        
        if ($preferredImage) {
            Write-Host "[DEBUG] Loading existing preview: $($preferredImage.FullName)" -ForegroundColor Cyan
            Write-Host "[DEBUG] File exists: $(Test-Path $preferredImage.FullName)" -ForegroundColor Gray
            Write-Host "[DEBUG] File size: $($preferredImage.Length) bytes" -ForegroundColor Gray
            Load-PreviewImage -jobVm $Job -filePath $preferredImage.FullName
            # Give UI time to update
            Start-Sleep -Milliseconds 200
            Update-JobProgress -Job $Job -Percent 100 -Status "Preview loaded from existing files" -LogLine "[$(Get-Date -Format 'HH:mm:ss')] Found $($existingFiles.Count) existing image(s), loaded: $(Split-Path $preferredImage.FullName -Leaf)"
        } else {
            Write-Host "[DEBUG] No preferred image found, but files exist" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[DEBUG] No existing files found, waiting for new files..." -ForegroundColor Gray
        Update-JobProgress -Job $Job -Percent 0 -Status "Waiting for files..." -LogLine "[$(Get-Date -Format 'HH:mm:ss')] Monitoring directory: $Directory"
    }
    
    Write-Host "Started monitoring: $Directory for job $($Job.Name)" -ForegroundColor Green
}

# Monitor processes
function Start-ProcessMonitoring {
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromSeconds(2)
    $timer.Add_Tick({
        try {
            # Find Python processes
            $pythonProcs = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
                $_.Path -like "*python*"
            }
            
            # Find Blender processes
            $blenderProcs = Get-Process blender -ErrorAction SilentlyContinue
            
            $totalProcs = $pythonProcs.Count + $blenderProcs.Count
            
            if ($window -and $statusText) {
                $window.Dispatcher.Invoke([action]{
                    if ($totalProcs -gt 0) {
                        $statusText.Text = "Active: $totalProcs processes"
                        $statusText.Foreground = [System.Windows.Media.Brushes]::Lime
                    } else {
                        $statusText.Text = "Idle - Waiting for generation..."
                        $statusText.Foreground = [System.Windows.Media.Brushes]::Yellow
                    }
                    $threadsText.Text = "Cores: $MaxCores"
                }, [System.Windows.Threading.DispatcherPriority]::Normal)
            }
        } catch {
            # Ignore errors
        }
    })
    $timer.Start()
    return $timer
}

# Initialize
Write-Host "Initializing Control Room Monitor..." -ForegroundColor Cyan
Initialize-Jobs

# Start monitoring each job
foreach ($job in $jobs) {
    if ($job.OutputFolder) {
        Start-MonitoringJob -Job $job -Directory $job.OutputFolder
    }
}

# Start process monitoring
$processTimer = Start-ProcessMonitoring

# Window event handlers
$window.Add_Loaded({
    $window.Activate()
    $window.Focus()
    $window.Topmost = $false
    $window.WindowState = "Normal"
    Write-Host "Control Room Monitor window opened and activated" -ForegroundColor Green
})

$window.Add_Closing({
    # Cleanup watchers
    foreach ($watcher in $script:FileWatchers.Values) {
        if ($watcher) {
            $watcher.EnableRaisingEvents = $false
            $watcher.Dispose()
        }
    }
    if ($processTimer) {
        $processTimer.Stop()
    }
})

# Ensure window is visible and properly configured
$window.WindowStartupLocation = "CenterScreen"
$window.ShowInTaskbar = $true
$window.Topmost = $false
$window.WindowState = "Normal"

# Force window to be visible and render properly
$window.Visibility = [System.Windows.Visibility]::Visible

# Show window
Write-Host "Showing Control Room Monitor window..." -ForegroundColor Cyan
Write-Host "Each job card will show:" -ForegroundColor Yellow
Write-Host "  - Live spritesheet preview (left panel)" -ForegroundColor Gray
Write-Host "  - Progress bar and status" -ForegroundColor Gray
Write-Host "  - Real-time logs (right panel)" -ForegroundColor Gray
Write-Host "  - Open Folder button to view output" -ForegroundColor Gray
Write-Host ""
Write-Host "If you see COLORS, BORDERS, and IMAGES (not just text), the GUI is working!" -ForegroundColor Cyan
Write-Host ""

# Use ShowDialog for modal window (blocks until closed)
# ShowDialog automatically starts the message pump if Application exists
try {
    $window.ShowDialog() | Out-Null
} catch {
    Write-Host "ERROR showing window: $_" -ForegroundColor Red
    Write-Host "Stack: $($_.ScriptStackTrace)" -ForegroundColor Red
}

Write-Host "Control Room Monitor closed" -ForegroundColor Green
