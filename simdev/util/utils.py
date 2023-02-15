def truncate(source: str, max_len: int = 40, stop="..."):
    return (source[:max_len - len(stop)] + stop)[:min(len(source), max_len)]
