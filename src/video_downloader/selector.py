def choose(candidates):
    """
    Select the strongest media candidate.

    Priority:
    1. Known video/stream
    2. Resolution
    3. Width
    4. FPS
    5. Bitrate
    6. Existing candidate score
    """

    if not candidates:
        return None

    usable = [
        c for c in candidates
        if getattr(c, "extension", "")
        or getattr(c, "mime_type", "")
    ]

    if not usable:
        return None

    return max(
        usable,
        key=lambda c: (
            getattr(c, "height", None) or 0,
            getattr(c, "width", None) or 0,
            getattr(c, "fps", None) or 0,
            getattr(c, "bitrate", None) or 0,
            getattr(c, "score", 0),
        )
    )
