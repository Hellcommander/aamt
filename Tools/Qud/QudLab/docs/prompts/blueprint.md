# Prompt pack: Blueprint

Before writing ObjectBlueprint XML:

1. Use `/blueprint?name=` and `/search?kind=blueprint&q=` for inheritance chains.
2. Parts must match real part class names from the type graph when possible.
3. Prefer inheriting an existing vanilla object; do not invent root blueprints.
4. Stats/tags should mirror patterns from similar blueprints in the cache.
5. Never embed or invent game asset binary paths beyond names already in metadata.
