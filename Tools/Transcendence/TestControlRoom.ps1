#!/usr/bin/env pwsh
<#
Quick test to verify Control Room can launch
#>

param(
    [switch]$Simple
)

Add-Type -AssemblyName PresentationFramework, PresentationCore, System.Windows.Forms, System.Drawing

if ($Simple) {
    # Simple test window
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Control Room Test"
    $form.Size = New-Object System.Drawing.Size(400, 300)
    $form.StartPosition = "CenterScreen"
    
    $label = New-Object System.Windows.Forms.Label
    $label.Text = "Control Room Test - If you see this, GUI works!"
    $label.Location = New-Object System.Drawing.Point(20, 20)
    $label.Size = New-Object System.Drawing.Size(360, 200)
    $label.Font = New-Object System.Drawing.Font("Segoe UI", 12)
    $form.Controls.Add($label)
    
    $button = New-Object System.Windows.Forms.Button
    $button.Text = "Close"
    $button.Location = New-Object System.Drawing.Point(150, 200)
    $button.Size = New-Object System.Drawing.Size(100, 30)
    $button.Add_Click({ $form.Close() })
    $form.Controls.Add($button)
    
    [System.Windows.Forms.Application]::Run($form)
    exit 0
}

# Test WPF XAML loading
Write-Host "Testing WPF XAML loading..." -ForegroundColor Cyan

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="Control Room Test" Height="300" Width="500"
        WindowStartupLocation="CenterScreen">
  <Grid Margin="20">
    <StackPanel>
      <TextBlock Text="Control Room WPF Test" FontSize="18" FontWeight="Bold" Margin="0,0,0,20"/>
      <TextBlock Text="If you see this window, WPF is working correctly!" FontSize="12" Margin="0,0,0,20"/>
      <Button Name="CloseButton" Content="Close" Width="100" Height="30" HorizontalAlignment="Left"/>
    </StackPanel>
  </Grid>
</Window>
"@

try {
    $reader = New-Object System.Xml.XmlNodeReader $xaml
    $window = [Windows.Markup.XamlReader]::Load($reader)
    
    $closeBtn = $window.FindName("CloseButton")
    $closeBtn.Add_Click({ $window.Close() })
    
    Write-Host "WPF window created successfully!" -ForegroundColor Green
    Write-Host "Showing window..." -ForegroundColor Cyan
    
    $window.ShowDialog() | Out-Null
    
    Write-Host "Window closed." -ForegroundColor Green
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    Write-Host "Stack: $($_.ScriptStackTrace)" -ForegroundColor Red
    exit 1
}

