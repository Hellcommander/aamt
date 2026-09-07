<#
.SYNOPSIS
  TML Static Analysis Module
  
.DESCRIPTION
  Advanced TLisp code analysis:
  - Detect unused variables
  - Detect unreachable code
  - Warn about expensive operations in frequently-called events
  - Flag deprecated functions
#>

# ============================================================
# TML STATIC ANALYSIS
# ============================================================

# Deprecated functions database
$script:DeprecatedFunctions = @{
    'objGetItems' = @{ 
        Replacement = 'objGetProperty ... ''items'; 
        Severity = 'Warning';
        Description = 'Use objGetProperty with items property'
    }
    'objGetArmorType' = @{ 
        Replacement = 'objGetProperty ... ''armorClass'; 
        Severity = 'Warning';
        Description = 'Use objGetProperty with armorClass property'
    }
    'objSetItemProperty' = @{ 
        Replacement = 'itmSetProperty'; 
        Severity = 'Warning';
        Description = 'Use itmSetProperty instead'
    }
    'shpGetDirection' = @{ 
        Replacement = 'objGetProperty ... ''rotation'; 
        Severity = 'Warning';
        Description = 'Use objGetProperty with rotation property'
    }
    'shpSetController' = @{ 
        Replacement = 'objSetProperty ... ''controller'; 
        Severity = 'Warning';
        Description = 'Use objSetProperty with controller property'
    }
    'sysGetNodes' = @{ 
        Replacement = 'unvGetTopologyNodes'; 
        Severity = 'Warning';
        Description = 'Use unvGetTopologyNodes instead'
    }
    'staGetDockedShips' = @{ 
        Replacement = 'objGetProperty ... ''dockedShips'; 
        Severity = 'Warning';
        Description = 'Use objGetProperty with dockedShips property'
    }
    'objDestroy' = @{ 
        Replacement = 'objDestroy obj objSource'; 
        Severity = 'Error';
        Description = 'API 57 requires source parameter'
    }
    'Register' = @{ 
        Replacement = 'Register obj Registrar'; 
        Severity = 'Error';
        Description = 'API 57 requires Registrar parameter'
    }
}

# Expensive operations (should avoid in frequently-called events)
$script:ExpensiveOperations = @{
    'sysFindObject' = @{ 
        Severity = 'Warning';
        Description = 'Expensive - searches all objects in system'
    }
    'enum' = @{ 
        Severity = 'Info';
        Description = 'Can be expensive with large lists'
    }
    'sysCreateShip' = @{ 
        Severity = 'Warning';
        Description = 'Expensive - creates new object'
    }
    'sysCreateStation' = @{ 
        Severity = 'Warning';
        Description = 'Expensive - creates new object'
    }
    'typGetData' = @{ 
        Severity = 'Info';
        Description = 'Type data access can be slow'
    }
    'typSetData' = @{ 
        Severity = 'Info';
        Description = 'Type data write can be slow'
    }
}

# Frequently-called events (should avoid expensive operations)
$script:FrequentlyCalledEvents = @(
    'OnUpdate',
    'OnDamage',
    'OnDamageArmor',
    'OnDamageShields',
    'OnFireWeapon',
    'OnGlobalObjAttacked',
    'OnGlobalObjDestroyed'
)

function Get-TMLStaticAnalysis {
    param([string[]]$Files)
    
    $issues = [System.Collections.ArrayList]::new()
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Find all TLisp code blocks
        $blocks = Get-TLispBlocks -Text $text -FilePath $file
        
        foreach ($block in $blocks) {
            # Analyze each block
            $blockIssues = Get-BlockAnalysis -Block $block -Text $text
            $issues.AddRange($blockIssues)
        }
    }
    
    return $issues
}

function Get-TLispBlocks {
    param(
        [string]$Text,
        [string]$FilePath
    )
    
    $blocks = [System.Collections.ArrayList]::new()
    $lines = $Text -split "`r?`n"
    $lineNum = 0
    $inBlock = $false
    $blockStart = 0
    $blockName = ''
    $blockContent = [System.Collections.ArrayList]::new()
    
    foreach ($line in $lines) {
        $lineNum++
        
        # Detect block start
        if ($line -match '<(Events|On\w+|Globals|Script)[^>]*>') {
            $inBlock = $true
            $blockStart = $lineNum
            $blockName = $matches[1]
            $blockContent.Clear()
            continue
        }
        
        # Detect block end
        if ($inBlock -and $line -match "</$blockName>") {
            $inBlock = $false
            [void]$blocks.Add([PSCustomObject]@{
                Name = $blockName
                StartLine = $blockStart
                EndLine = $lineNum
                Content = $blockContent -join "`n"
                File = $FilePath
            })
            $blockContent.Clear()
            continue
        }
        
        # Collect block content
        if ($inBlock) {
            [void]$blockContent.Add($line)
        }
    }
    
    return $blocks
}

function Get-BlockAnalysis {
    param(
        [PSCustomObject]$Block,
        [string]$Text
    )
    
    $issues = [System.Collections.ArrayList]::new()
    $content = $Block.Content
    
    # Extract TLisp code (remove comments)
    $code = Remove-TLispComments -Code $content
    
    # 1. Detect unused variables
    $varIssues = Get-UnusedVariables -Code $code -Block $Block
    $issues.AddRange($varIssues)
    
    # 2. Detect unreachable code
    $unreachableIssues = Get-UnreachableCode -Code $code -Block $Block
    $issues.AddRange($unreachableIssues)
    
    # 3. Check for expensive operations in frequently-called events
    if ($script:FrequentlyCalledEvents -contains $Block.Name) {
        $expensiveIssues = Get-ExpensiveOperations -Code $code -Block $Block
        $issues.AddRange($expensiveIssues)
    }
    
    # 4. Flag deprecated functions
    $deprecatedIssues = Get-DeprecatedFunctions -Code $code -Block $Block
    $issues.AddRange($deprecatedIssues)
    
    return $issues
}

function Get-UnusedVariables {
    param(
        [string]$Code,
        [PSCustomObject]$Block
    )
    
    $issues = [System.Collections.ArrayList]::new()
    $variables = @{}
    
    # Find variable definitions: (block (var1 var2) ...) or (setq var value)
    $blockPattern = '\(block\s+\(([^)]+)\)'
    $blockMatches = [regex]::Matches($Code, $blockPattern, 'IgnoreCase')
    
    foreach ($m in $blockMatches) {
        $varList = $m.Groups[1].Value
        $vars = $varList -split '\s+' | Where-Object { $_ -ne 'Nil' -and $_ -ne '' }
        
        foreach ($var in $vars) {
            if (-not $variables.ContainsKey($var)) {
                $variables[$var] = @{
                    Defined = $true
                    Used = $false
                    Line = $Block.StartLine
                }
            }
        }
    }
    
    # Find setq definitions: (setq var value)
    $setqPattern = '\(setq\s+(\w+)\s+'
    $setqMatches = [regex]::Matches($Code, $setqPattern, 'IgnoreCase')
    
    foreach ($m in $setqMatches) {
        $var = $m.Groups[1].Value
        if (-not $variables.ContainsKey($var)) {
            $variables[$var] = @{
                Defined = $true
                Used = $false
                Line = $Block.StartLine
            }
        }
    }
    
    # Find variable usage (excluding definitions)
    foreach ($var in $variables.Keys) {
        # Skip if it's a function name (starts with known prefixes)
        $knownPrefixes = @('obj', 'itm', 'typ', 'sys', 'shp', 'sta', 'unv', 'rpg', 'g')
        $isFunction = $false
        foreach ($prefix in $knownPrefixes) {
            if ($var.StartsWith($prefix)) {
                $isFunction = $true
                break
            }
        }
        
        if ($isFunction) { continue }
        
        # Check if variable is used (not in definition)
        $usagePattern = "\b$var\b"
        $usageMatches = [regex]::Matches($Code, $usagePattern, 'IgnoreCase')
        
        $used = $false
        foreach ($um in $usageMatches) {
            # Check if this is a definition or usage
            $before = $Code.Substring(0, $um.Index)
            $after = $Code.Substring($um.Index + $var.Length)
            
            # Not a definition if not preceded by (block ( or (setq 
            if (-not ($before -match '\(block\s+\([^)]*$' -or $before -match '\(setq\s+$')) {
                $used = $true
                break
            }
        }
        
        if (-not $used) {
            [void]$issues.Add([PSCustomObject]@{
                File = $Block.File
                Line = $variables[$var].Line
                Code = 'UNUSED_VARIABLE'
                Severity = 'Warning'
                Message = "Variable '$var' is defined but never used in <$($Block.Name)>"
                Category = 'TML Static Analysis'
            })
        }
    }
    
    return $issues
}

function Get-UnreachableCode {
    param(
        [string]$Code,
        [PSCustomObject]$Block
    )
    
    $issues = [System.Collections.ArrayList]::new()
    
    # Find if statements with always-false conditions
    # Pattern: (if Nil ...) or (if false ...)
    $ifPattern = '\(if\s+(Nil|false|False)\s+([^)]+)\)'
    $ifMatches = [regex]::Matches($Code, $ifPattern, 'IgnoreCase')
    
    foreach ($m in $ifMatches) {
        $thenCode = $m.Groups[2].Value
        $lineNum = $Block.StartLine + (([regex]::Matches($Code.Substring(0, $m.Index), "`n")).Count)
        
        [void]$issues.Add([PSCustomObject]@{
            File = $Block.File
            Line = $lineNum
            Code = 'UNREACHABLE_CODE'
            Severity = 'Warning'
            Message = "Unreachable code in <$($Block.Name)>: if condition is always false (Nil/false)"
            Category = 'TML Static Analysis'
        })
    }
    
    # Find switch statements with unreachable cases
    # Pattern: (switch value (case1 ...) (case2 ...))
    # This is more complex and would require full parsing
    
    return $issues
}

function Get-ExpensiveOperations {
    param(
        [string]$Code,
        [PSCustomObject]$Block
    )
    
    $issues = [System.Collections.ArrayList]::new()
    
    foreach ($op in $script:ExpensiveOperations.Keys) {
        $pattern = "\($op\s"
        $matches = [regex]::Matches($Code, $pattern, 'IgnoreCase')
        
        foreach ($m in $matches) {
            $lineNum = $Block.StartLine + (([regex]::Matches($Code.Substring(0, $m.Index), "`n")).Count)
            $info = $script:ExpensiveOperations[$op]
            
            [void]$issues.Add([PSCustomObject]@{
                File = $Block.File
                Line = $lineNum
                Code = 'EXPENSIVE_OPERATION'
                Severity = $info.Severity
                Message = "Expensive operation '$op' in frequently-called event <$($Block.Name)>: $($info.Description)"
                Category = 'TML Static Analysis'
            })
        }
    }
    
    return $issues
}

function Get-DeprecatedFunctions {
    param(
        [string]$Code,
        [PSCustomObject]$Block
    )
    
    $issues = [System.Collections.ArrayList]::new()
    
    foreach ($func in $script:DeprecatedFunctions.Keys) {
        $pattern = "\($func\s"
        $matches = [regex]::Matches($Code, $pattern, 'IgnoreCase')
        
        foreach ($m in $matches) {
            $lineNum = $Block.StartLine + (([regex]::Matches($Code.Substring(0, $m.Index), "`n")).Count)
            $info = $script:DeprecatedFunctions[$func]
            
            [void]$issues.Add([PSCustomObject]@{
                File = $Block.File
                Line = $lineNum
                Code = 'DEPRECATED_FUNCTION'
                Severity = $info.Severity
                Message = "Deprecated function '$func' in <$($Block.Name)>: $($info.Description). Consider: $($info.Replacement)"
                Category = 'TML Static Analysis'
            })
        }
    }
    
    return $issues
}

function Remove-TLispComments {
    param([string]$Code)
    
    # Remove TML comments (; ...)
    $lines = $Code -split "`n"
    $cleaned = @()
    
    foreach ($line in $lines) {
        # Find comment position (not in string)
        $commentPos = -1
        $inString = $false
        $inQuote = $false
        
        for ($i = 0; $i -lt $line.Length; $i++) {
            $char = $line[$i]
            
            if ($char -eq '"' -and ($i -eq 0 -or $line[$i-1] -ne '\')) {
                $inString = -not $inString
            }
            elseif ($char -eq "'" -and -not $inString) {
                $inQuote = -not $inQuote
            }
            elseif ($char -eq ';' -and -not $inString -and -not $inQuote) {
                $commentPos = $i
                break
            }
        }
        
        if ($commentPos -ge 0) {
            $cleaned += $line.Substring(0, $commentPos)
        }
        else {
            $cleaned += $line
        }
    }
    
    return $cleaned -join "`n"
}

# Export functions
# Functions are available for dot-sourcing

