import discord
import logging
from discord import app_commands
from discord.ext import commands
from typing import Optional, Literal
from utils.database import db
from utils.formatting import format_cash

logger = logging.getLogger(__name__)

class Profile(commands.Cog):
    """Commands for viewing profiles and statistics"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="profile", description="View your or another user's profile")
    @app_commands.describe(
        user="The user whose profile you want to view (default: yourself)",
        hidden="Send the response only to you (default: False)"
    )
    async def profile(
        self, 
        interaction: discord.Interaction, 
        user: Optional[discord.User] = None,
        hidden: bool = False
    ):
        """View your or another user's profile"""
        await interaction.response.defer(ephemeral=hidden)
        
        # If no user is specified, use the command invoker
        target_user = user or interaction.user
        target_id = str(target_user.id)
        
        # Get user data
        user_data = await db.get_user(target_id)
        
        # Create embed
        embed = discord.Embed(
            title=f"{target_user.display_name}'s Profile",
            color=discord.Color.blue()
        )
        
        # Set user avatar as thumbnail
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Add stats fields
        embed.add_field(
            name="Cash",
            value=format_cash(user_data['cash']),
            inline=True
        )
        
        embed.add_field(
            name="Level",
            value=f"{user_data['level']} ({user_data['xp']} XP)",
            inline=True
        )
        
        embed.add_field(
            name="Games Played",
            value=format_cash(user_data['games_played']),
            inline=True
        )
        
        # Win/loss ratio
        if user_data['losses'] > 0:
            win_ratio = user_data['wins'] / (user_data['wins'] + user_data['losses']) * 100
            ratio_text = f"{win_ratio:.1f}%"
        else:
            if user_data['wins'] > 0:
                ratio_text = "100%"
            else:
                ratio_text = "N/A"
        
        embed.add_field(
            name="Win/Loss",
            value=f"{format_cash(user_data['wins'])}/{format_cash(user_data['losses'])} ({ratio_text})",
            inline=True
        )
        
        embed.add_field(
            name="Cash Won",
            value=format_cash(user_data['total_cash_won']),
            inline=True
        )
        
        embed.add_field(
            name="Cash Lost",
            value=format_cash(user_data['total_cash_lost']),
            inline=True
        )
        
        # Calculate overall profit
        profit = user_data['total_cash_won'] - user_data['total_cash_lost']
        profit_str = f"+{format_cash(profit)}" if profit >= 0 else f"-{format_cash(abs(profit))}"
        
        embed.add_field(
            name="Profit",
            value=profit_str,
            inline=True
        )
        
        # Show vote streak if any
        if user_data['vote_streak'] > 0:
            embed.add_field(
                name="Vote Streak",
                value=f"{user_data['vote_streak']} votes",
                inline=True
            )
        
        await interaction.followup.send(embed=embed, ephemeral=hidden)
    
    @app_commands.command(name="leaderboard", description="View the global leaderboard")
    @app_commands.describe(
        category="The stat to rank players by (default: cash)",
        hidden="Send the response only to you (default: False)"
    )
    async def leaderboard(
        self, 
        interaction: discord.Interaction, 
        category: Literal["cash", "level", "wins", "profit"] = "cash",
        hidden: bool = False
    ):
        """View the global leaderboard"""
        await interaction.response.defer(ephemeral=hidden)
        
        field_mapping = {
            "cash": "cash",
            "level": "level",
            "wins": "wins",
            "profit": "total_cash_won"  # We'll handle the profit calculation separately
        }
        
        field = field_mapping[category]
        
        # Get leaderboard data
        leaderboard = await db.get_leaderboard(field, 10)
        
        if not leaderboard:
            return await interaction.followup.send("No users found for the leaderboard!", ephemeral=hidden)
        
        # Create embed
        category_title = category.capitalize() if category else "Cash"
        embed = discord.Embed(
            title=f"Global {category_title} Leaderboard",
            description="Top 10 players:",
            color=discord.Color.gold()
        )
        
        # Add leaderboard entries
        for i, entry in enumerate(leaderboard, 1):
            user_id = entry['id']
            value_str = ""
            
            try:
                user = await self.bot.fetch_user(int(user_id))
                username = user.display_name
            except:
                username = f"User {user_id}"
            
            if category == "profit":
                value = entry['total_cash_won'] - entry['total_cash_lost']
                value_str = f"{format_cash(value)}"
            elif category == "cash":
                value_str = f"{format_cash(entry['cash'])}"
            elif category == "level":
                value_str = f"Level {entry['level']} ({entry['xp']} XP)"
            elif category == "wins":
                value_str = f"{format_cash(entry['wins'])}"
            
            embed.add_field(
                name=f"{i}. {username}",
                value=value_str,
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=hidden)

async def setup(bot):
    await bot.add_cog(Profile(bot))
