from typing import Union

def format_cash(amount: Union[int, float]) -> str:
    """
    Format a cash amount with commas and make it look nice.
    
    Args:
        amount: The cash amount to format
    
    Returns:
        A formatted string representing the cash amount
    """
    if isinstance(amount, float):
        # Round down to nearest integer
        amount = int(amount)
    
    return f"{amount:,}"

def parse_bet_amount(bet_str: str, max_cash: int) -> int:
    """
    Parse a bet amount string, handling shortcuts like 'k', 'm', etc.
    
    Args:
        bet_str: The bet amount as a string
        max_cash: The maximum cash the user has
    
    Returns:
        The parsed bet amount as an integer
    """
    bet_str = bet_str.lower().strip()
    
    # Handle max/all/allin bets
    if bet_str in ['max', 'm', 'all', 'allin']:
        return max_cash
    
    # Handle shortcuts
    multipliers = {
        'k': 1_000,                  # thousand
        'm': 1_000_000,              # million
        'g': 1_000_000_000,          # billion (giga)
        't': 1_000_000_000_000,      # trillion
        'p': 1_000_000_000_000_000,  # quadrillion (peta)
        'e': 1_000_000_000_000_000_000,  # quintillion (exa)
        'z': 1_000_000_000_000_000_000_000,  # sextillion (zetta)
        'y': 1_000_000_000_000_000_000_000_000  # septillion (yotta)
    }
    
    # Check if the bet ends with one of our multipliers
    if bet_str[-1] in multipliers:
        # Extract the number and multiplier
        number_part = bet_str[:-1]
        multiplier = multipliers[bet_str[-1]]
        
        try:
            # Convert the number part to a float and multiply
            amount = int(float(number_part) * multiplier)
            return min(amount, max_cash)  # Cap at max cash
        except ValueError:
            # If conversion fails, return 0
            return 0
    
    # Try to convert to an integer directly
    try:
        amount = int(float(bet_str))
        return min(amount, max_cash)  # Cap at max cash
    except ValueError:
        return 0

def format_time(seconds: float) -> str:
    """
    Format a time duration in seconds to a human-readable format.
    
    Args:
        seconds: The time duration in seconds
    
    Returns:
        A formatted string representing the time duration
    """
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} minutes"
    
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f} hours"
    
    days = hours / 24
    return f"{days:.1f} days"
