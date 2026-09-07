# Transcendence Mod Tools - Quick Reference

## 🚀 Quick Start

1. **Double-click** `TranscendenceModTools.bat`
2. **XML Checker** tab → Enter path → Click **Scan**
3. Review issues → Double-click to open in VS Code
4. Click **Auto-Fix** for fixable issues

## 📋 Common Issues & Fixes

### "content expected" Error
**Cause**: Raw `>` character in element content  
**Fix**: Replace `>` with `&gt;` in comments/code  
**Example**: `; if count > 1` → `; if count &gt; 1`

### "Mismatched quote" Error
**Cause**: Unescaped `<` or `>` in string literals  
**Fix**: Escape XML tags in strings  
**Example**: `xmlCreate "<Tag>"` → `xmlCreate "&lt;Tag&gt;"`

### "Identifiers must not use single quote"
**Cause**: Symbol literal has trailing quote  
**Fix**: Remove trailing quote  
**Example**: `type:'symbol'` → `type:'symbol`

### Unclosed Tag
**Cause**: Missing closing tag  
**Fix**: Add matching closing tag  
**Example**: `<ItemType>` needs `</ItemType>`

### Duplicate UNID
**Cause**: Same UNID used twice  
**Fix**: Change one UNID to unique value

### Unbalanced Parentheses
**Cause**: Mismatched `(` and `)` in TLisp  
**Fix**: Count and balance parentheses

## 🎯 Tool Features

### XML Checker Tab
- ✅ Scans for common issues
- ✅ Shows line numbers
- ✅ Color-coded severity
- ✅ Double-click to open in VS Code
- ✅ Auto-fix with backups

### Error Helper Tab
- ✅ Paste error messages
- ✅ Get diagnosis and solutions
- ✅ Auto-fix suggestions

### Project Health Tab
- ✅ Scan entire mod folder
- ✅ Comprehensive report
- ✅ Per-file status
- ✅ Summary statistics

## 🔧 Keyboard Shortcuts

- **Double-click issue** → Open in VS Code
- **Ctrl+C** → Copy error message
- **Ctrl+V** → Paste in Error Helper

## 📝 Best Practices

1. **Always scan before testing** - Catch issues early
2. **Use Auto-Fix carefully** - Review `.bak` backups
3. **Check Project Health** - For large mods
4. **Fix errors first** - Then warnings
5. **Verify after auto-fix** - Rescan to confirm

## 🆘 Troubleshooting

**Tool won't start?**
- Check PowerShell 7+ is installed
- Run: `pwsh --version`

**No issues found but mod crashes?**
- Check Error Helper tab
- Paste the exact error message
- Check Project Health for hidden issues

**Auto-fix didn't work?**
- Check `.bak` backup file
- Some issues require manual fixing
- Rescan after manual changes

## 📚 Element Quick Reference

### Common Elements

**TranscendenceExtension**
```xml
<TranscendenceExtension UNID="&unidExtension;" apiVersion="57" version="1.0" name="My Mod">
```

**ItemType**
```xml
<ItemType UNID="&itMyItem;" name="My Item" level="5">
```

**ShipClass**
```xml
<ShipClass UNID="&scMyShip;" name="My Ship" class="fighter" level="5">
```

**StationType**
```xml
<StationType UNID="&stMyStation;" name="My Station" level="5">
```

**Events**
```xml
<Events>
    <OnCreate>
        (block Nil
            (objSetData gSource 'myData true)
        )
    </OnCreate>
</Events>
```

**Device (self-closing)**
```xml
<Device deviceID="primaryWeapon" item="&itLaserCannon;"/>
```

## 🎨 UNID Ranges

- **Items**: `0x00004000` - `0x00004FFF` (base game)
- **Ships**: `0x00002000` - `0x00002FFF` (base game)
- **Stations**: `0x00008000` - `0x00008FFF` (base game)
- **Mods**: Use your assigned range (e.g., `0xE1270000`+)

## ⚡ Pro Tips

1. **Use Project Health** for large mods - See all issues at once
2. **Fix errors first** - Warnings can wait
3. **Check UNID duplicates** - Use Project Health tab
4. **Validate TLisp** - Check parentheses balance
5. **Scan regularly** - Before each test run

## 🔗 Related Files

- `README_Checker.txt` - Detailed documentation
- `FEATURES.md` - Complete feature list
- `TranscendenceModTools.ps1` - Main tool
- `TranscendenceModTools_Advanced.ps1` - Advanced features

