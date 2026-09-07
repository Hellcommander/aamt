<#
.SYNOPSIS
    Toolset Information Module
    
.DESCRIPTION
    Provides toolset name and branding information for AI-Assisted Modding Tools (AAMT)
#>

# Toolset Information
$script:ToolsetName = "AI-Assisted Modding Tools"
$script:ToolsetAcronym = "AAMT"
$script:ToolsetVersion = "1.0"
$script:ToolsetDescription = "Multi-game modding toolkit with AI-assisted asset generation using Ollama and Stable Diffusion 3"

function Get-ToolsetName {
    <#
    .SYNOPSIS
    Returns the toolset name.
    #>
    return $script:ToolsetName
}

function Get-ToolsetAcronym {
    <#
    .SYNOPSIS
    Returns the toolset acronym.
    #>
    return $script:ToolsetAcronym
}

function Get-ToolsetInfo {
    <#
    .SYNOPSIS
    Returns full toolset information.
    #>
    return @{
        Name = $script:ToolsetName
        Acronym = $script:ToolsetAcronym
        Version = $script:ToolsetVersion
        Description = $script:ToolsetDescription
    }
}

Export-ModuleMember -Function Get-ToolsetName, Get-ToolsetAcronym, Get-ToolsetInfo
