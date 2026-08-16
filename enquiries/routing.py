def normalise_postcode(value):
    return "".join(character for character in (value or "").strip() if character.isdigit())


def route_postcode(value):
    """Return a location code or None for out-of-area postcodes."""
    postcode = normalise_postcode(value)
    if postcode.startswith("3"):
        return "southland"
    if postcode.startswith("26") or postcode.startswith("29"):
        return "canberra"
    return None
