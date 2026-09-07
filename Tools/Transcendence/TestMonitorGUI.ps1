#!/usr/bin/env pwsh
<#
Enhanced GUI Test - Shows actual visual elements and simulated progress
#>

# Ensure STA mode
if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -ne [System.Threading.ApartmentState]::STA) {
    Write-Host "ERROR: Must run in STA mode" -ForegroundColor Red
    Write-Host "Run with: powershell -STA -File TestMonitorGUI.ps1" -ForegroundColor Yellow
    exit 1
}

Add-Type -AssemblyName PresentationFramework, PresentationCore, System.Windows.Forms

Write-Host "Creating test window with visual elements..." -ForegroundColor Cyan

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="Space Whale GUI Test - Visual Elements" Height="600" Width="800"
        WindowStartupLocation="CenterScreen"
        Background="White"
        AllowsTransparency="False">
  <Grid Margin="20" Background="White">
    <Grid.RowDefinitions>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="*"/>
      <RowDefinition Height="Auto"/>
    </Grid.RowDefinitions>
    
    <!-- Header with colored background -->
    <Border Grid.Row="0" Background="#1a2a3a" Padding="15" Margin="0,0,0,15" CornerRadius="5">
      <TextBlock Text="Space Whale GUI Test" 
                 FontSize="20" FontWeight="Bold" 
                 Foreground="White" HorizontalAlignment="Center"/>
    </Border>
    
    <!-- Content with visual elements -->
    <StackPanel Grid.Row="1" VerticalAlignment="Center">
      <TextBlock Text="Visual Elements Test:" 
                 FontSize="16" FontWeight="Bold" 
                 Foreground="#1a2a3a" Margin="0,0,0,20" HorizontalAlignment="Center"/>
      
      <!-- Colored border box -->
      <Border BorderBrush="#66ccff" BorderThickness="3" 
              Background="#1a2a3a" Padding="20" Margin="20" CornerRadius="5">
        <StackPanel>
          <TextBlock Text="Active Tasks:" 
                     FontSize="14" FontWeight="Bold" 
                     Foreground="#66ccff" Margin="0,0,0,15"/>
          
          <!-- Modeling Task -->
          <StackPanel Orientation="Horizontal" Margin="0,0,0,10">
            <TextBlock Text="[RUNNING] " Foreground="Cyan" FontWeight="Bold" Width="90"/>
            <TextBlock Text="Modeling" Width="150" Foreground="White"/>
            <ProgressBar Name="ModelProgress" Value="45" Maximum="100" Width="200" Height="20" 
                        Background="#E0E0E0" Foreground="#66ccff" Margin="10,0"/>
            <TextBlock Text="45%" Foreground="#88ffff" Margin="10,0" Width="50"/>
          </StackPanel>
          
          <!-- Spritesheet Task -->
          <StackPanel Orientation="Horizontal" Margin="0,0,0,10">
            <TextBlock Text="[RUNNING] " Foreground="Cyan" FontWeight="Bold" Width="90"/>
            <TextBlock Text="Spritesheet (120 facings)" Width="150" Foreground="White"/>
            <ProgressBar Name="SpriteProgress" Value="72" Maximum="100" Width="200" Height="20" 
                        Background="#E0E0E0" Foreground="#66ccff" Margin="10,0"/>
            <TextBlock Text="72%" Foreground="#88ffff" Margin="10,0" Width="50"/>
          </StackPanel>
          
          <!-- XML Task -->
          <StackPanel Orientation="Horizontal" Margin="0,0,0,10">
            <TextBlock Text="[WAITING] " Foreground="Yellow" FontWeight="Bold" Width="90"/>
            <TextBlock Text="XML Export" Width="150" Foreground="White"/>
            <ProgressBar Name="XMLProgress" Value="0" Maximum="100" Width="200" Height="20" 
                        Background="#E0E0E0" Foreground="#66ccff" Margin="10,0"/>
            <TextBlock Text="0%" Foreground="#88ffff" Margin="10,0" Width="50"/>
          </StackPanel>
        </StackPanel>
      </Border>
      
      <!-- Status info -->
      <StackPanel Margin="20" Orientation="Horizontal" HorizontalAlignment="Center">
        <TextBlock Text="Files: " FontWeight="Bold" Foreground="#1a2a3a"/>
        <TextBlock Name="FilesText" Text="12" Foreground="#66ccff" FontWeight="Bold" Margin="5,0,20,0"/>
        <TextBlock Text="Threads: " FontWeight="Bold" Foreground="#1a2a3a"/>
        <TextBlock Text="32" Foreground="#66ccff" FontWeight="Bold" Margin="5,0"/>
      </StackPanel>
    </StackPanel>
    
    <!-- Footer -->
    <Border Grid.Row="2" Background="#E0E0E0" Padding="10" Margin="0,15,0,0" CornerRadius="3">
      <TextBlock Text="If you see colors, borders, and progress bars above, the GUI is working!" 
                 FontSize="12" HorizontalAlignment="Center" 
                 Foreground="#666666"/>
    </Border>
  </Grid>
</Window>
"@

try {
    $reader = New-Object System.Xml.XmlNodeReader $xaml
    $window = [Windows.Markup.XamlReader]::Load($reader)
    
    # Get UI elements
    $ModelProgress = $window.FindName("ModelProgress")
    $SpriteProgress = $window.FindName("SpriteProgress")
    $XMLProgress = $window.FindName("XMLProgress")
    $FilesText = $window.FindName("FilesText")
    
    # Ensure window is visible
    $window.Topmost = $true
    $window.WindowState = "Normal"
    $window.ShowInTaskbar = $true
    $window.WindowStartupLocation = "CenterScreen"
    
    Write-Host "Window created successfully!" -ForegroundColor Green
    Write-Host "You should see:" -ForegroundColor Yellow
    Write-Host "  - Dark blue header with white text" -ForegroundColor Gray
    Write-Host "  - Cyan border box with progress bars" -ForegroundColor Gray
    Write-Host "  - Animated progress (Modeling: 45%, Spritesheet: 72%)" -ForegroundColor Gray
    Write-Host "  - Gray footer" -ForegroundColor Gray
    Write-Host ""
    Write-Host "If you only see text, the GUI rendering is not working properly." -ForegroundColor Yellow
    Write-Host ""
    
    # Animate progress bars to show they're working
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromMilliseconds(100)
    $counter = 0
    $timer.Add_Tick({
        $counter++
        if ($ModelProgress) {
            $current = $ModelProgress.Value
            if ($current -lt 90) {
                $ModelProgress.Value = $current + 0.5
            }
        }
        if ($SpriteProgress) {
            $current = $SpriteProgress.Value
            if ($current -lt 95) {
                $SpriteProgress.Value = $current + 0.3
            }
        }
        if ($counter -gt 50 -and $XMLProgress) {
            $XMLProgress.Value = 25
        }
        if ($FilesText) {
            $FilesText.Text = (12 + [math]::Floor($counter / 10)).ToString()
        }
        
        if ($counter -gt 200) {
            $timer.Stop()
        }
    })
    $timer.Start()
    
    $window.Add_Loaded({
        $window.Activate()
        $window.Focus()
        $window.Topmost = $false
    })
    
    Write-Host "Showing window with animated progress..." -ForegroundColor Cyan
    $window.ShowDialog() | Out-Null
    
    Write-Host "Window closed" -ForegroundColor Green
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    Write-Host "Stack: $($_.ScriptStackTrace)" -ForegroundColor Red
    exit 1
}
