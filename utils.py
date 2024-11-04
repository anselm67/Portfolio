
def percent(part: float, total: float, default_str: str = "--") -> str :
    if total > 0: 
        return f"{100.0 * part / total:,.2f}" 
    else: 
        return default_str
