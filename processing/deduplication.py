def deduplicate(items):
    unique = []
    seen = set()

    for item in items:
        name = item.get("equipment_name")

        if name and name not in seen:
            seen.add(name)
            unique.append(item)

    return unique
