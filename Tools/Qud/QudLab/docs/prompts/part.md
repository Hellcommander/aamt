# Prompt pack: Part

Before writing any C# part:

1. Prefer real types from search hits / cache (`XRL.World.IPart`, event handler APIs).
2. Query mentally (or via assistant): `/type?name=XRL.World.IPart`, `/search?q=WantEvent`.
3. Emit a `[Serializable]` class inheriting `IPart` in `XRL.World.Parts` unless told otherwise.
4. Prefer `WantEvent` / typed `HandleEvent` patterns used by current Qud — do not invent obsolete `HandleEvent(Event E)` overrides unless hits show them.
5. Never invent type or event names not present in the provided metadata.
