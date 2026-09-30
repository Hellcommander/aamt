# Tools/Soulash2/SkillCreator/unlock_fixer.py

def force_unlock_all(defs):
    """
    defs = dictionary of loaded JSON definitions:
    {
        "skills": [...],
        "abilities": [...],
        "amplifiers": [...],
        "stackers": [...],
        "milestones": [...],
        ...
    }
    """

    for category, items in defs.items():
        if not isinstance(items, list):
            continue

        for item in items:
            # Remove any lock flags the game might use
            if "locked" in item:
                item["locked"] = False

            if "unlock" in item:
                item["unlock"] = True

            if "unlock_state" in item:
                item["unlock_state"] = "unlocked"

            # Some mods use custom lock fields
            if "is_locked" in item:
                item["is_locked"] = False

            # Some abilities hide behind milestones
            if "required_milestone" in item:
                item["required_milestone"] = None

            # Some amplifiers hide behind skill levels
            if "required_skill_level" in item:
                item["required_skill_level"] = 0

    return defs
