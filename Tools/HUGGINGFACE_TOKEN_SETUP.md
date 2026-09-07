# How to Create a Hugging Face Token

## Step-by-Step Instructions

### 1. Create/Login to Hugging Face Account
- Go to: https://huggingface.co/
- Sign up for a free account (if you don't have one) or log in

### 2. Accept model licenses
- SD images: https://huggingface.co/stabilityai/stable-diffusion-3.5-medium → **Agree and access repository**
- Stable Audio 3 SFX: https://huggingface.co/stabilityai/stable-audio-3-medium → **Agree and access repository**
- Optional lighter SFX model: https://huggingface.co/stabilityai/stable-audio-3-small-sfx
- Gated repos return 401/403 until you accept each page and your token can read them.

### 3. Create an Access Token
- Go to: https://huggingface.co/settings/tokens
- Or navigate: Settings → Access Tokens (from your profile menu)

### 4. Generate New Token
- Click **"New token"** button
- Prefer a classic **Read** token (covers all models you have accepted)
- If using **fine-grained**, explicitly grant read on each gated model you need (SD3.5 **and** Stable Audio Open, etc.)
- Give it a name (e.g., "AAMT Models")
- Click **"Generate a token"**

### 5. Copy the Token
- **IMPORTANT**: Copy the token immediately - you won't be able to see it again!
- It will look like: `hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- Save it somewhere safe (password manager, text file, etc.)

### 6. Login with the Token
Open PowerShell and run:
```powershell
hf auth login
```

When prompted:
- Paste your token
- Press Enter

You should see: `Login successful`

### 7. Verify Authentication
Test that it worked:
```powershell
huggingface-cli whoami
```

You should see your username.

### 8. Download the Model
Now you can download the SD3.5 model:
```powershell
cd "E:\tools\sd3.5\sd3.5"
python download_model.py
```

Or use the setup script:
```powershell
cd "d:\games\Steam\steamapps\common\Transcendence\Tools"
.\Setup-SD35Server.ps1
```

## Cache location (important on Windows)

- **Token / login**: leave default (`%USERPROFILE%\.cache\huggingface`) — do **not** set `HF_HOME` elsewhere or auth breaks.
- **Model weights**: `E:\tools\stable-audio\hub` via `HUGGINGFACE_HUB_CACHE` / `HF_HUB_CACHE`.

`Setup-StableAudio.ps1` and generators set the hub cache on E: automatically.

## Auto token profiles (AAMT)

Tools switch by **token display name** (from `hf auth login` / stored_tokens), never by embedding secrets:

| Profile | Token name | Used for |
|---------|------------|----------|
| `media` | `SD3.5 Token` | SD3.5 + Stable Audio downloads |
| `training` | `Custom Modul for creation` | Primordialis / LoRA / PEFT training |

```powershell
Import-Module .\Shared\HfTokenSwitch.psm1
Use-AamtHfToken -Profile media
Use-AamtHfToken -Profile training
```

Python:
```python
from hf_token_switch import use_media_token, use_training_token
use_media_token()
use_training_token()
```

Optional rename overrides (names only): copy `HfTokenProfiles.example.ps1` → `HfTokenProfiles.local.ps1` (gitignored).

## Troubleshooting

### "Token not found" error
- Make sure you copied the entire token (starts with `hf_`)
- Try logging in again: `huggingface-cli login`

### "401 Unauthorized" error
- Make sure you accepted the license at: https://huggingface.co/stabilityai/stable-diffusion-3.5-medium
- Verify your token is valid at: https://huggingface.co/settings/tokens

### "Cannot access gated repo" error
- You must accept the license agreement first
- Visit the model page and click "Agree and access repository"

## Security Notes

- **Never share your token** - it gives access to your account
- **Don't commit tokens to Git** - they will be visible in your repository
- **Use Read tokens** for downloading models (safer than Write tokens)
- If a token is compromised, revoke it immediately and create a new one
