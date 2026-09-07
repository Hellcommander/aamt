# Prompt pack: Mutation

Before writing mutation code:

1. Check mutation XML hits for `Class=` (maps to `XRL.World.Parts.Mutation.<Class>`).
2. Query `/type?name=XRL.World.Parts.Mutation.BaseMutation` and `/mutations?q=…`.
3. Subclass `BaseMutation`; implement `Mutate` / `Unmutate` carefully (abilities + cleanup).
4. Match activated-ability patterns from `/abilities` when adding commands.
5. Never invent mutation class names — use Class from Mutations.xml or indexed types.
