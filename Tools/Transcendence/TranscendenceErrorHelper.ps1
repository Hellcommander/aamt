<#
.SYNOPSIS
  Transcendence Error Helper - Parse and diagnose Transcendence error messages.

.DESCRIPTION
  Paste Transcendence error messages and get suggestions for fixing them.
  Based on error patterns from the Transcendence engine source code.

.EXAMPLE
  pwsh -File TranscendenceErrorHelper.ps1
#>

[CmdletBinding()]
param(
    [string]$ErrorMessage,
    [string]$FilePath,
    [switch]$NoGui
)

# ============================================================
# ERROR PATTERN DATABASE
# Based on TranscendenceDev-integration-API57/Alchemy/XMLUtil/Parser.cpp
# and Alchemy/CodeChain/Link.cpp
# ============================================================

$ErrorPatterns = @(
    # XML Parser Errors
    @{
        Pattern = 'content expected'
        Code = 'XML_CONTENT_EXPECTED'
        Cause = "A literal '>' character was found in element content (outside of tags). Transcendence's XMLUtil parser treats this as a tag close token."
        Solution = "Replace the '>' character with '&gt;' in your code/comments."
        Example = "; if (gr x 5) ; comment with >1 items`n; Fix: if (gr x 5) ; comment with &gt;1 items"
        AutoFix = $true
    },
    @{
        Pattern = 'close tag </(\w+)> does not match open <(\w+)>'
        Code = 'XML_TAG_MISMATCH'
        Cause = "The closing tag name doesn't match the opening tag name."
        Solution = "Check the line numbers in the error and fix the mismatched tag names."
        Example = "<MyTag>...</MyOtherTag> should be <MyTag>...</MyTag>"
        AutoFix = $false
    },
    @{
        Pattern = 'element tag expected'
        Code = 'XML_ELEMENT_EXPECTED'
        Cause = "The parser expected an element tag name but found something else."
        Solution = "Check for malformed XML near the reported line. Look for unclosed tags or invalid characters."
        AutoFix = $false
    },
    @{
        Pattern = 'root element expected'
        Code = 'XML_ROOT_EXPECTED'
        Cause = "The parser couldn't find the root element of the XML document."
        Solution = "Ensure your file starts with <?xml?> and has a proper root element like <TranscendenceExtension>."
        AutoFix = $false
    },
    @{
        Pattern = '<\?XML prologue expected'
        Code = 'XML_PROLOGUE_EXPECTED'
        Cause = "The parser expected the XML prologue (<?xml version='1.0'?>) but found something else. This often means there's a BOM or whitespace before the first '<'."
        Solution = "Remove any BOM (byte order mark) or whitespace before the first '<' in the file."
        AutoFix = $true
    },
    @{
        Pattern = 'attribute value must be quoted'
        Code = 'XML_ATTR_QUOTE'
        Cause = "An attribute value was not enclosed in quotes."
        Solution = 'Ensure all attribute values are quoted: attribute="value" or attribute=''value'''
        Example = 'UNID=0x12345678 should be UNID="0x12345678"'
        AutoFix = $false
    },
    @{
        Pattern = 'mismatched attribute quote'
        Code = 'XML_ATTR_QUOTE_MISMATCH'
        Cause = "An attribute's opening and closing quotes don't match."
        Solution = 'Ensure quotes match: use "..." or ''...'' but not mixed.'
        AutoFix = $false
    },
    @{
        Pattern = 'DOCTYPE: \] expected'
        Code = 'DOCTYPE_BRACKET'
        Cause = "The DOCTYPE internal subset is not properly closed."
        Solution = "Check that the DOCTYPE declaration ends with ]> and all ENTITY definitions are valid."
        AutoFix = $false
    },
    
    # TLisp/CodeChain Errors
    @{
        Pattern = 'Mismatched quote'
        Code = 'TLISP_QUOTE_MISMATCH'
        Cause = "A string literal has an opening quote but no matching closing quote. This often happens when < or > characters inside a string are interpreted as XML tags."
        Solution = @"
1. Check for unescaped < or > in strings (use &lt; and &gt;)
2. Check for missing closing quotes
3. If using xmlCreate, escape the XML: xmlCreate "&lt;Tag&gt;...&lt;/Tag&gt;"
"@
        Example = '(xmlCreate "<Tag>") should be (xmlCreate "&lt;Tag&gt;")'
        AutoFix = $true
    },
    @{
        Pattern = 'Identifiers must not use single quote characters: (\w+)'
        Code = 'TLISP_INVALID_SYMBOL'
        Cause = "A symbol literal has a trailing single quote. In TLisp, symbols use ONLY a leading quote (e.g., 'symbol), not a trailing one."
        Solution = "Remove the trailing quote from the symbol."
        Example = "type:'rebuild' should be type:'rebuild (no trailing quote)"
        AutoFix = $true
    },
    @{
        Pattern = 'Mismatched close parenthesis'
        Code = 'TLISP_PAREN_CLOSE'
        Cause = "A closing parenthesis ')' was found without a matching opening '('."
        Solution = "Check parentheses balance. Count '(' and ')' - they should match."
        AutoFix = $false
    },
    @{
        Pattern = 'Mismatched close brace'
        Code = 'TLISP_BRACE_CLOSE'
        Cause = "A closing brace '}' was found without a matching opening '{'."
        Solution = "Check brace balance for struct literals. { and } should match."
        AutoFix = $false
    },
    @{
        Pattern = "':' character must appear inside quotes"
        Code = 'TLISP_COLON'
        Cause = "A colon was found outside of a string or struct definition."
        Solution = "Colons should only appear in struct definitions like { key:value } or inside quoted strings."
        AutoFix = $false
    },
    @{
        Pattern = 'Unexpected character'
        Code = 'TLISP_UNEXPECTED_CHAR'
        Cause = "An unexpected character was encountered during parsing."
        Solution = "Check for typos, invalid characters, or encoding issues near the reported line."
        AutoFix = $false
    },
    
    # UNID and Entity Errors
    @{
        Pattern = 'Reference to undeclared entity'
        Code = 'ENTITY_UNDECLARED'
        Cause = "An entity reference like &entityName; was used but the entity was not defined in the DOCTYPE."
        Solution = "1. Add the missing entity to your DOCTYPE section`n2. Check spelling of entity name`n3. If the entity is from another mod/library, ensure it loads first"
        AutoFix = $false
    },
    @{
        Pattern = 'duplicate UNID'
        Code = 'UNID_DUPLICATE'
        Cause = "Two or more items are using the same UNID."
        Solution = "Change one of the UNIDs to a unique value. Use a UNID in your assigned range."
        AutoFix = $false
    }
)

function Parse-TranscendenceError {
    param([string]$ErrorText)
    
    $results = @()
    
    # Extract line number if present
    $lineMatch = [regex]::Match($ErrorText, 'Line[:\s]*\(?(\d+)\)?')
    $lineNumber = if ($lineMatch.Success) { [int]$lineMatch.Groups[1].Value } else { 0 }
    
    # Extract file path if present
    $fileMatch = [regex]::Match($ErrorText, '([\w\\/\.\-_]+\.xml)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $filePath = if ($fileMatch.Success) { $fileMatch.Groups[1].Value } else { '' }
    
    # Match against known patterns
    foreach ($pattern in $ErrorPatterns) {
        if ($ErrorText -match $pattern.Pattern) {
            $result = [PSCustomObject]@{
                Code = $pattern.Code
                Cause = $pattern.Cause
                Solution = $pattern.Solution
                Example = $pattern.Example
                LineNumber = $lineNumber
                FilePath = $filePath
                CanAutoFix = $pattern.AutoFix
                MatchedText = $Matches[0]
            }
            $results += $result
        }
    }
    
    if ($results.Count -eq 0) {
        $results += [PSCustomObject]@{
            Code = 'UNKNOWN'
            Cause = "This error pattern is not in the database."
            Solution = "Check the Transcendence forums or modding wiki for help with this specific error."
            Example = $null
            LineNumber = $lineNumber
            FilePath = $filePath
            CanAutoFix = $false
            MatchedText = $ErrorText
        }
    }
    
    return $results
}

function Show-ErrorAnalysis {
    param([array]$Results)
    
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host "ERROR ANALYSIS" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    
    foreach ($r in $Results) {
        Write-Host "`n[$($r.Code)]" -ForegroundColor Yellow
        if ($r.FilePath) { Write-Host "  File: $($r.FilePath)" -ForegroundColor Gray }
        if ($r.LineNumber -gt 0) { Write-Host "  Line: $($r.LineNumber)" -ForegroundColor Gray }
        Write-Host "`n  CAUSE:" -ForegroundColor White
        Write-Host "    $($r.Cause)" -ForegroundColor Gray
        Write-Host "`n  SOLUTION:" -ForegroundColor Green
        $r.Solution -split "`n" | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        if ($r.Example) {
            Write-Host "`n  EXAMPLE:" -ForegroundColor Cyan
            $r.Example -split "`n" | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkCyan }
        }
        if ($r.CanAutoFix) {
            Write-Host "`n  [This issue can potentially be auto-fixed]" -ForegroundColor Green
        }
    }
    Write-Host "`n============================================================" -ForegroundColor Cyan
}

function Test-IsInteractiveConsole {
    try {
        if (-not [Environment]::UserInteractive) { return $false }
        if ([Console]::IsInputRedirected) { return $false }
        return $true
    } catch { return $false }
}

function Run-InteractiveMode {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Transcendence Error Helper" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    # Guard: without an interactive console, Read-Host returns empty forever and
    # this would spin in a tight infinite loop. Print usage and exit instead.
    if (-not (Test-IsInteractiveConsole)) {
        Write-Host "Non-interactive console detected; interactive paste mode is unavailable." -ForegroundColor Yellow
        Write-Host "Pass an error via -ErrorMessage '<text>' (or -FilePath) to analyze unattended." -ForegroundColor Gray
        return
    }

    Write-Host "Paste your Transcendence error message below and press Enter twice:" -ForegroundColor White
    Write-Host "(Type 'quit' to exit)" -ForegroundColor Gray
    Write-Host ""
    
    while ($true) {
        $lines = @()
        $emptyCount = 0
        
        while ($emptyCount -lt 1) {
            $input = Read-Host
            if ($input -eq 'quit' -or $input -eq 'exit') { return }
            if ([string]::IsNullOrWhiteSpace($input)) {
                $emptyCount++
            }
            else {
                $emptyCount = 0
                $lines += $input
            }
        }
        
        if ($lines.Count -gt 0) {
            $errorText = $lines -join "`n"
            $results = Parse-TranscendenceError -ErrorText $errorText
            Show-ErrorAnalysis -Results $results
            
            Write-Host "`nPaste another error or type 'quit' to exit:" -ForegroundColor White
        }
    }
}

function Run-GuiMode {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    
    [System.Windows.Forms.Application]::EnableVisualStyles()
    
    $form = [System.Windows.Forms.Form]::new()
    $form.Text = 'Transcendence Error Helper'
    $form.Width = 900
    $form.Height = 700
    $form.StartPosition = 'CenterScreen'
    $form.BackColor = [System.Drawing.Color]::FromArgb(30, 30, 35)
    $form.ForeColor = [System.Drawing.Color]::White
    
    # Input label
    $lblInput = [System.Windows.Forms.Label]::new()
    $lblInput.Text = 'Paste Transcendence error message:'
    $lblInput.Location = [System.Drawing.Point]::new(10, 10)
    $lblInput.Size = [System.Drawing.Size]::new(300, 20)
    $lblInput.ForeColor = [System.Drawing.Color]::White
    $form.Controls.Add($lblInput)
    
    # Input textbox
    $txtInput = [System.Windows.Forms.TextBox]::new()
    $txtInput.Multiline = $true
    $txtInput.ScrollBars = 'Vertical'
    $txtInput.Location = [System.Drawing.Point]::new(10, 35)
    $txtInput.Size = [System.Drawing.Size]::new(860, 150)
    $txtInput.BackColor = [System.Drawing.Color]::FromArgb(45, 45, 50)
    $txtInput.ForeColor = [System.Drawing.Color]::White
    $txtInput.Font = [System.Drawing.Font]::new('Consolas', 10)
    $form.Controls.Add($txtInput)
    
    # Analyze button
    $btnAnalyze = [System.Windows.Forms.Button]::new()
    $btnAnalyze.Text = 'Analyze Error'
    $btnAnalyze.Location = [System.Drawing.Point]::new(10, 195)
    $btnAnalyze.Size = [System.Drawing.Size]::new(120, 30)
    $btnAnalyze.BackColor = [System.Drawing.Color]::FromArgb(60, 120, 60)
    $btnAnalyze.ForeColor = [System.Drawing.Color]::White
    $btnAnalyze.FlatStyle = 'Flat'
    $form.Controls.Add($btnAnalyze)
    
    # Clear button
    $btnClear = [System.Windows.Forms.Button]::new()
    $btnClear.Text = 'Clear'
    $btnClear.Location = [System.Drawing.Point]::new(140, 195)
    $btnClear.Size = [System.Drawing.Size]::new(80, 30)
    $btnClear.BackColor = [System.Drawing.Color]::FromArgb(80, 80, 85)
    $btnClear.ForeColor = [System.Drawing.Color]::White
    $btnClear.FlatStyle = 'Flat'
    $form.Controls.Add($btnClear)
    
    # Output label
    $lblOutput = [System.Windows.Forms.Label]::new()
    $lblOutput.Text = 'Analysis:'
    $lblOutput.Location = [System.Drawing.Point]::new(10, 235)
    $lblOutput.Size = [System.Drawing.Size]::new(300, 20)
    $lblOutput.ForeColor = [System.Drawing.Color]::White
    $form.Controls.Add($lblOutput)
    
    # Output textbox
    $txtOutput = [System.Windows.Forms.RichTextBox]::new()
    $txtOutput.Location = [System.Drawing.Point]::new(10, 260)
    $txtOutput.Size = [System.Drawing.Size]::new(860, 390)
    $txtOutput.BackColor = [System.Drawing.Color]::FromArgb(25, 25, 30)
    $txtOutput.ForeColor = [System.Drawing.Color]::White
    $txtOutput.Font = [System.Drawing.Font]::new('Consolas', 10)
    $txtOutput.ReadOnly = $true
    $form.Controls.Add($txtOutput)
    
    # Button handlers
    $btnAnalyze.Add_Click({
        $errorText = $txtInput.Text
        if ([string]::IsNullOrWhiteSpace($errorText)) {
            $txtOutput.Text = "Please paste an error message to analyze."
            return
        }
        
        $results = Parse-TranscendenceError -ErrorText $errorText
        
        $output = @()
        $output += "============================================================"
        $output += "ERROR ANALYSIS"
        $output += "============================================================"
        
        foreach ($r in $results) {
            $output += ""
            $output += "[$($r.Code)]"
            if ($r.FilePath) { $output += "  File: $($r.FilePath)" }
            if ($r.LineNumber -gt 0) { $output += "  Line: $($r.LineNumber)" }
            $output += ""
            $output += "CAUSE:"
            $output += "  $($r.Cause)"
            $output += ""
            $output += "SOLUTION:"
            $r.Solution -split "`n" | ForEach-Object { $output += "  $_" }
            if ($r.Example) {
                $output += ""
                $output += "EXAMPLE:"
                $r.Example -split "`n" | ForEach-Object { $output += "  $_" }
            }
            if ($r.CanAutoFix) {
                $output += ""
                $output += "[This issue can potentially be auto-fixed by the XML Checker tool]"
            }
        }
        
        $output += ""
        $output += "============================================================"
        
        $txtOutput.Text = $output -join "`r`n"
    })
    
    $btnClear.Add_Click({
        $txtInput.Text = ''
        $txtOutput.Text = ''
    })
    
    # Pre-fill if error message was provided
    if ($ErrorMessage) {
        $txtInput.Text = $ErrorMessage
    }
    
    [void]$form.ShowDialog()
}

# Main
if ($ErrorMessage) {
    $results = Parse-TranscendenceError -ErrorText $ErrorMessage
    Show-ErrorAnalysis -Results $results
}
elseif ($NoGui) {
    Run-InteractiveMode
}
elseif (-not (Test-IsInteractiveConsole)) {
    # Never launch a blocking GUI dialog on an unattended/non-interactive run.
    Write-Host "Transcendence Error Helper" -ForegroundColor Cyan
    Write-Host "No error supplied and no interactive console; nothing to do." -ForegroundColor Yellow
    Write-Host "Usage: TranscendenceErrorHelper.ps1 -ErrorMessage '<text>' [-FilePath <path>] [-NoGui]" -ForegroundColor Gray
}
else {
    Run-GuiMode
}

