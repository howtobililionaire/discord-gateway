import os
import json
import logging
from typing import Dict, Any, Optional, List
import asyncio

logger = logging.getLogger(__name__)

class Database:
    """
    Simple in-memory database with file persistence.
    
    For a production bot, you'd want to use a real database system,
    but this will work for the initial implementation.
    """
    
    def __init__(self, file_path: str = "data.json"):
        self.file_path = file_path
        self.data = {
            "users": {},
            "guilds": {},
            "global_stats": {
                "total_bets": 0,
                "total_cash_won": 0,
                "total_cash_lost": 0
            }
        }
        self.lock = asyncio.Lock()  # Thread-safe operations
        self._load_data()
    
    def _load_data(self):
        """Load data from the JSON file if it exists."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    self.data = json.load(f)
                logger.info(f"Loaded data from {self.file_path}")
            else:
                logger.info(f"No data file found at {self.file_path}, starting fresh")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    async def _save_data(self):
        """Save data to the JSON file."""
        async with self.lock:
            try:
                with open(self.file_path, 'w') as f:
                    json.dump(self.data, f, indent=2)
                logger.debug(f"Saved data to {self.file_path}")
            except Exception as e:
                logger.error(f"Error saving data: {e}")
    
    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user data or create a new user if they don't exist."""
        user_id = str(user_id)  # Ensure ID is a string
        async with self.lock:
            if user_id not in self.data["users"]:
                # Initialize new user with default values
                self.data["users"][user_id] = {
                    "cash": 1000,
                    "level": 0,
                    "xp": 0,
                    "games_played": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_cash_won": 0,
                    "total_cash_lost": 0,
                    "items": [],
                    "boosts": [],
                    "cooldowns": {},
                    "vote_streak": 0,
                    "last_vote": None,
                    "mine": None
                }
                await self._save_data()
            
            return self.data["users"][user_id]
    
    async def update_user(self, user_id: str, data: Dict[str, Any]):
        """Update user data."""
        user_id = str(user_id)  # Ensure ID is a string
        async with self.lock:
            self.data["users"][user_id].update(data)
            await self._save_data()
    
    async def get_leaderboard(self, field: str = "cash", limit: int = 10) -> List[Dict[str, Any]]:
        """Get a sorted leaderboard based on a specific field."""
        async with self.lock:
            # Sort users by the specified field
            sorted_users = sorted(
                [(user_id, user_data) for user_id, user_data in self.data["users"].items()],
                key=lambda x: x[1].get(field, 0),
                reverse=True
            )[:limit]
            
            # Format the leaderboard data
            return [{"id": user_id, **user_data} for user_id, user_data in sorted_users]
    
    async def update_stats(self, bet_amount: int, result: bool):
        """Update global stats for bets."""
        async with self.lock:
            self.data["global_stats"]["total_bets"] += 1
            
            if result:  # Win
                self.data["global_stats"]["total_cash_won"] += bet_amount
            else:  # Loss
                self.data["global_stats"]["total_cash_lost"] += bet_amount
            
            await self._save_data()
    
    async def get_all_cooldowns(self, user_id: str) -> Dict[str, Any]:
        """Get all cooldowns for a user."""
        user = await self.get_user(user_id)
        return user.get("cooldowns", {})
    
    async def set_cooldown(self, user_id: str, command: str, expiry_time: float):
        """Set a cooldown for a specific command."""
        user = await self.get_user(user_id)
        
        if "cooldowns" not in user:
            user["cooldowns"] = {}
        
        user["cooldowns"][command] = expiry_time
        await self.update_user(user_id, user)

# Create a global instance for use throughout the bot
db = Database()
