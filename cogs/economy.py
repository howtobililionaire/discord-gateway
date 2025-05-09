import discord
import logging
import time
from discord import app_commands
from discord.ext import commands
from typing import Optional
from utils.database import db
from utils.cooldowns import cooldown
from utils.formatting import format_cash, format_time

logger = logging.getLogger(__name__)

class Economy(commands.Cog):
    """Commands for earning and managing cash"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="work", description="Work to earn some cash (every 10 minutes)")
    @app_commands.describe(
        hidden="Send the response only to you (default: False)"
    )
    async def work(self, interaction: discord.Interaction, hidden: bool = False):
        """Work to earn some cash (available every 10 minutes)"""
        await interaction.response.defer(ephemeral=hidden)
        
        user_id = str(interaction.user.id)
        user = await db.get_user(user_id)
        
        # Calculate earnings based on level
        base_earnings = 100
        level_bonus = user['level'] * 50
        earnings = base_earnings + level_bonus
        
        # Update user's cash
        user['cash'] += earnings
        user['total_cash_won'] += earnings
        
        # Add some XP
        xp_gained = 5
        user['xp'] += xp_gained
        
        # Check for level up
        old_level = user['level']
        new_level = int(user['xp'] / 100)  # Simple level formula: 100 XP per level
        
        if new_level > old_level:
            user['level'] = new_level
            level_up_message = f"\n🎉 Level up! You are now level {new_level}!"
        else:
            level_up_message = ""
        
        # Save user data
        await db.update_user(user_id, user)
        
        # Create and send the message
        embed = discord.Embed(
            title="Work Complete!",
            description=f"You worked hard and earned {format_cash(earnings)} cash!{level_up_message}",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Cash", value=format_cash(user['cash']), inline=True)
        embed.add_field(name="Level", value=f"{user['level']} ({user['xp']} XP)", inline=True)
        embed.set_footer(text="You can work again in 10 minutes")
        
        await interaction.followup.send(embed=embed, ephemeral=hidden)
    
    @app_commands.command(name="daily", description="Collect your daily cash reward")
    @app_commands.describe(
        hidden="Send the response only to you (default: False)"
    )
    async def daily(self, interaction: discord.Interaction, hidden: bool = False):
        """Collect your daily cash reward"""
        await interaction.response.defer(ephemeral=hidden)
        
        user_id = str(interaction.user.id)
        user = await db.get_user(user_id)
        
        # Calculate earnings based on level
        base_earnings = 1000
        level_bonus = user['level'] * 500
        earnings = base_earnings + level_bonus
        
        # Update user's cash
        user['cash'] += earnings
        user['total_cash_won'] += earnings
        
        # Add some XP
        xp_gained = 20
        user['xp'] += xp_gained
        
        # Check for level up
        old_level = user['level']
        new_level = int(user['xp'] / 100)  # Simple level formula: 100 XP per level
        
        if new_level > old_level:
            user['level'] = new_level
            level_up_message = f"\n🎉 Level up! You are now level {new_level}!"
        else:
            level_up_message = ""
        
        # Save user data
        await db.update_user(user_id, user)
        
        # Create and send the message
        embed = discord.Embed(
            title="Daily Reward Collected!",
            description=f"You received your daily reward of {format_cash(earnings)} cash!{level_up_message}",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="Cash", value=format_cash(user['cash']), inline=True)
        embed.add_field(name="Level", value=f"{user['level']} ({user['xp']} XP)", inline=True)
        embed.set_footer(text="You can collect your daily reward again tomorrow")
        
        await interaction.followup.send(embed=embed, ephemeral=hidden)
    
    @app_commands.command(name="vote", description="Vote for the bot to earn cash and credit")
    async def vote(self, interaction: discord.Interaction):
        """Vote for the bot to earn cash and credit"""
        user_id = str(interaction.user.id)
        user = await db.get_user(user_id)
        
        # Calculate potential earnings based on level and vote streak
        base_amount = 100000
        level_multiplier = max(1, user['level'])
        streak_multiplier = min(4, max(1, user['vote_streak'] // 21))
        
        # Every 21st vote is a 3x multiplier
        triple_bonus = 3 if (user['vote_streak'] + 1) % 21 == 0 else 1
        
        potential_reward = base_amount * level_multiplier * streak_multiplier * triple_bonus
        
        embed = discord.Embed(
            title="Vote for Rocket Gambling Bot",
            description="Vote for the bot to earn cash and credit!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Voting Reward",
            value=f"You'll receive {format_cash(potential_reward)} cash for voting",
            inline=False
        )
        
        embed.add_field(
            name="Current Vote Streak",
            value=f"{user['vote_streak']} votes",
            inline=True
        )
        
        embed.add_field(
            name="Reward Multiplier",
            value=f"{streak_multiplier}x" + (f" (3x bonus on next vote!)" if (user['vote_streak'] + 1) % 21 == 0 else ""),
            inline=True
        )
        
        embed.add_field(
            name="Vote Link",
            value="[Click here to vote](https://top.gg/bot/yourbotid/vote)",
            inline=False
        )
        
        embed.set_footer(text="Vote every 12 hours to maintain your streak!")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="cooldowns", description="Check your command cooldowns")
    @app_commands.describe(
        hidden="Send the response only to you (default: True)"
    )
    async def cooldowns(self, interaction: discord.Interaction, hidden: bool = True):
        """Check when your commands will be available again"""
        await interaction.response.defer(ephemeral=hidden)
        
        user_id = str(interaction.user.id)
        cooldowns = await db.get_all_cooldowns(user_id)
        
        embed = discord.Embed(
            title="Your Command Cooldowns",
            description="Here's when you can use commands again:",
            color=discord.Color.blue()
        )
        
        current_time = time.time()
        
        if not cooldowns:
            embed.add_field(name="All Commands Ready", value="You have no active cooldowns! 🎉", inline=False)
        else:
            for command, expiry_time in cooldowns.items():
                time_left = expiry_time - current_time
                
                if time_left <= 0:
                    status = "✅ Ready now!"
                else:
                    status = f"⏳ Ready in {format_time(time_left)}"
                
                embed.add_field(name=f"/{command}", value=status, inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=hidden)

async def setup(bot):
    await bot.add_cog(Economy(bot))
