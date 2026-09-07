# HfTokenProfiles.example.ps1
# Copy to HfTokenProfiles.local.ps1 (gitignored) only if you rename tokens on this machine.
# Tools default to these display names from `hf auth login` stored_tokens:
#
#   media / sd / stable-audio  ->  "SD3.5 Token"
#   training / primordialis    ->  "Custom Modul for creation"
#
# Example local overrides (names only — never put hf_... secrets here):

# $env:AAMT_HF_TOKEN_MEDIA = "SD3.5 Token"
# $env:AAMT_HF_TOKEN_TRAINING = "Custom Modul for creation"
