import discord
import logging
from discord import app_commands
from discord.ext import commands
from typing import Optional

logger = logging.getLogger(__name__)

class Help(commands.Cog):
    """Help commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="help", description="Show help information for commands")
    @app_commands.describe(
        command="The specific command to get help for (default: general help)",
        hidden="Send the response only to you (default: True)"
    )
    async def help(
        self, 
        interaction: discord.Interaction, 
        command: Optional[str] = None,
        hidden: Optional[bool] = True
    ):
        """Show help information about the bot's commands"""
        await interaction.response.defer(ephemeral=hidden)
        
        # If a specific command is requested
        if command:
            return await self._show_command_help(interaction, command, hidden)
        
        # Show general help
        embed = discord.Embed(
            title="Rocket Gambling Bot Help",
            description="Welcome to the Rocket Gambling Bot! Here's how to get started:",
            color=discord.Color.blue()
        )
        
        # Getting Started section
        embed.add_field(
            name="Getting Started",
            value="""
            • Use `/profile` to view your profile
            • Use `/coinflip` to flip a coin
            • Use `/blackjack` to play blackjack
            • Use `/work` and `/daily` to earn free money
            • Use `/vote` to earn more money and credit
            """,
            inline=False
        )
        
        # Game Commands section
        embed.add_field(
            name="Game Commands",
            value="""
            • `/coinflip <heads|tails> <bet>` - Bet on a coin flip
            • `/blackjack <bet> [hard]` - Play blackjack with optional hard mode
            """,
            inline=False
        )
        
        # Economy Commands section
        embed.add_field(
            name="Economy Commands",
            value="""
            • `/work` - Work for some cash (every 10 minutes)
            • `/daily` - Get your daily cash reward
            • `/vote` - Vote for the bot to get cash rewards
            • `/cooldowns` - Check when commands will be available again
            """,
            inline=False
        )
        
        # Profile Commands section
        embed.add_field(
            name="Profile Commands",
            value="""
            • `/profile [user]` - View your or another user's profile
            • `/leaderboard [category]` - View the global leaderboard
            """,
            inline=False
        )
        
        # Help Commands section
        embed.add_field(
            name="Help Commands",
            value="""
            • `/help` - Show this general help message
            • `/help <command>` - Show help for a specific command
            """,
            inline=False
        )
        
        # Footer with additional info
        embed.set_footer(text="Use /help <command> for more detailed information about a specific command")
        
        await interaction.followup.send(embed=embed, ephemeral=hidden)
    
    async def _show_command_help(self, interaction, command_name, hidden):
        """Show help for a specific command"""
        command_help = {
            "profile": {
                "usage": "/profile [user] [hidden]",
                "description": "View your profile or another user's profile.",
                "arguments": [
                    {"name": "user", "description": "The user whose profile you want to view (default: yourself)", "required": False},
                    {"name": "hidden", "description": "Send the response only to you (default: False)", "required": False}
                ],
                "examples": [
                    "/profile - View your own profile",
                    "/profile @username - View someone else's profile"
                ]
            },
            "coinflip": {
                "usage": "/coinflip <heads|tails> <bet> [hidden]",
                "description": "Flip a coin and bet on the outcome.",
                "arguments": [
                    {"name": "choice", "description": "Choose heads or tails", "required": True},
                    {"name": "bet", "description": "Amount of cash to bet", "required": True},
                    {"name": "hidden", "description": "Send the response only to you (default: False)", "required": False}
                ],
                "examples": [
                    "/coinflip heads 100 - Bet 100 on heads",
                    "/coinflip tails 1k - Bet 1,000 on tails",
                    "/coinflip heads max - Bet all your cash on heads"
                ]
            },
            "blackjack": {
                "usage": "/blackjack <bet> [hard] [hidden]",
                "description": "Play a game of blackjack.",
                "arguments": [
                    {"name": "bet", "description": "Amount of cash to bet", "required": True},
                    {"name": "hard", "description": "Play in hard mode for better odds (default: False)", "required": False},
                    {"name": "hidden", "description": "Send the response only to you (default: False)", "required": False}
                ],
                "examples": [
                    "/blackjack 100 - Play blackjack with a bet of 100",
                    "/blackjack 1k hard - Play hard mode blackjack with a bet of 1,000",
                    "/blackjack max - Bet all your cash on blackjack"
                ]
            },
            "work": {
                "usage": "/work [hidden]",
                "description": "Work to earn some cash (available every 10 minutes).",
                "arguments": [
                    {"name": "hidden", "description": "Send the response only to you (default: False)", "required": False}
                ],
                "examples": [
                    "/work - Work for some cash"
                ]
            },
            "daily": {
                "usage": "/daily [hidden]",
                "description": "Collect your daily cash reward (resets at midnight).",
                "arguments": [
                    {"name": "hidden", "description": "Send the response only to you (default: False)", "required": False}
                ],
                "examples": [
                    "/daily - Collect your daily reward"
                ]
            },
            "vote": {
                "usage": "/vote",
                "description": "Vote for the bot to earn cash and credit.",
                "arguments": [],
                "examples": [
                    "/vote - Show voting information and links"
                ]
            },
            "cooldowns": {
                "usage": "/cooldowns [hidden]",
                "description": "Check when your commands will be available again.",
                "arguments": [
                    {"name": "hidden", "description": "Send the response only to you (default: True)", "required": False}
                ],
                "examples": [
                    "/cooldowns - Check your command cooldowns"
                ]
            },
            "leaderboard": {
                "usage": "/leaderboard [category] [hidden]",
                "description": "View the global leaderboard.",
                "arguments": [
                    {"name": "category", "description": "The stat to rank players by (default: cash)", "required": False},
                    {"name": "hidden", "description": "Send the response only to you (default: False)", "required": False}
                ],
                "examples": [
                    "/leaderboard - View the cash leaderboard",
                    "/leaderboard level - View the level leaderboard",
                    "/leaderboard wins - View the wins leaderboard",
                    "/leaderboard profit - View the profit leaderboard"
                ]
            },
            "help": {
                "usage": "/help [command] [hidden]",
                "description": "Show help information about the bot's commands.",
                "arguments": [
                    {"name": "command", "description": "The specific command to get help for", "required": False},
                    {"name": "hidden", "description": "Send the response only to you (default: True)", "required": False}
                ],
                "examples": [
                    "/help - Show general help",
                    "/help blackjack - Show help for the blackjack command"
                ]
            }
        }
        
        # Check if we have help for the requested command
        if command_name.lower() not in command_help:
            return await interaction.followup.send(f"No help available for command '{command_name}'. Use `/help` to see all commands.", ephemeral=hidden)
        
        # Get help data for the command
        help_data = command_help[command_name.lower()]
        
        # Create embed
        embed = discord.Embed(
            title=f"Help: /{command_name}",
            description=help_data["description"],
            color=discord.Color.blue()
        )
        
        # Add usage field
        embed.add_field(
            name="Usage",
            value=f"`{help_data['usage']}`",
            inline=False
        )
        
        # Add arguments field if there are any
        if help_data["arguments"]:
            arguments_text = ""
            for arg in help_data["arguments"]:
                required_text = "Required" if arg.get("required", False) else "Optional"
                arguments_text += f"• `{arg['name']}` - {arg['description']} ({required_text})\n"
            
            embed.add_field(
                name="Arguments",
                value=arguments_text,
                inline=False
            )
        
        # Add examples field
        examples_text = ""
        for example in help_data["examples"]:
            examples_text += f"• `{example}`\n"
        
        embed.add_field(
            name="Examples",
            value=examples_text,
            inline=False
        )
        
        # Add additional notes about bet shortcuts
        if command_name.lower() in ["coinflip", "blackjack"]:
            embed.add_field(
                name="Bet Shortcuts",
                value="""
                • `max` or `m` - Bet all your cash
                • `1k` - 1,000
                • `1m` - 1,000,000
                • `1g` - 1,000,000,000
                • `1t` - 1,000,000,000,000
                And more! See `/help` for complete list
                """,
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=hidden)

async def setup(bot):
    await bot.add_cog(Help(bot))
