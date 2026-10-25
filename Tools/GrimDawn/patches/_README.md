# uTXTp patches (re-applied on every build)

Drop `*.txt` files here in the GD-DPS "User Text Patch" format. Every update / merge build
re-extracts fresh game + mod data and re-applies these, so tweaks survive game patches and
mod updates. Top-level files only (sub-folders are ignored, like GD-DPS).

Also applied automatically: `mods\GD-DPS*\User Text Patch\*.txt` (GD-DPS's own folder).
Its `Example` sub-folder is not applied -- copy the ones you want up a level or here.

```
[
	<File  = Database\records\creatures\pc\playerlevels.dbr>
	<Entry = maxDevotionPoints>
	<Data  = 200>
]
```

`Database\records\...` = the build's record (pulled from the newest official layer if the
build doesn't override it). `Source\GDX3\database\...` = a specific official layer.
`Source\MODs\<mod folder>\database\records\...` = that mod's record.
Optional sections: `<Priority = 7000>` (text compare, higher wins), `<Type = U|I|R>`,
`<AppendAsMultiRecord = -1>`; Data `NULL` deletes the entry.

Check without building:
`python utxtp.py --mod-db "<game>\mods\<build>\database" --dry-run`
