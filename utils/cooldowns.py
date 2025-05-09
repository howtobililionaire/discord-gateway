import time
import asyncio
from functools import wraps
from typing import Dict, Optional
from discord import Interaction
from discord.app_commands import Command
from utils.database import db

# Cooldown durations in seconds
COOLDOWNS = {
    "work": 600,  # 10 minutes
    "daily": 86400,  # 24 hours
    "dig": 60,  # 1 minute
    "coinflip": 5,  # 5 seconds
    "blackjack": 10,  # 10 seconds
}

async def check_cooldown(user_id: str, command: str) -> Optional[float]:
    """
    Check if a command is on cooldown for a user.
    
    Args:
        user_id: The ID of the user
        command: The name of the command
    
    Returns:
        Remaining cooldown time in seconds, or None if not on cooldown
    """
    cooldowns = await db.get_all_cooldowns(user_id)
    if command in cooldowns:
        expiry_time = cooldowns[command]
        current_time = time.time()
        
        if current_time < expiry_time:
            # Command is on cooldown
            return expiry_time - current_time
    
    return None

async def set_cooldown(user_id: str, command: str):
    """
    Set a cooldown for a command for a specific user.
    
    Args:
        user_id: The ID of the user
        command: The name of the command
    """
    if command in COOLDOWNS:
        expiry_time = time.time() + COOLDOWNS[command]
        await db.set_cooldown(user_id, command, expiry_time)

def cooldown(command_name: str):
    """
    Decorator for app commands to apply cooldowns.
    
    Args:
        command_name: The name of the command for cooldown tracking
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: Interaction, *args, **kwargs):
            user_id = str(interaction.user.id)
            remaining = await check_cooldown(user_id, command_name)
            
            if remaining is not None:
                # Command is on cooldown
                return await interaction.response.send_message(
                    f"This command is on cooldown. Try again in {remaining:.1f} seconds.",
                    ephemeral=True
                )
            
            # Execute the command
            await func(self, interaction, *args, **kwargs)
            
            # Apply cooldown after command is executed
            await set_cooldown(user_id, command_name)
            
        return wrapper
    return decorator
