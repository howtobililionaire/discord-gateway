import os
import logging
import asyncio
import discord
from discord.ext import commands
import traceback

logger = logging.getLogger(__name__)

class RocketGamblingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Initialize the bot with slash commands enabled and proper intents
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,  # We'll implement our own help command
            description="Rocket Gambling Bot - Play games, win cash, get to the top of the leaderboards!"
        )
        
        self.logger = logging.getLogger('bot')
        
        # Load cogs
        self.initial_extensions = [
            'cogs.economy',
            'cogs.games',
            'cogs.profile',
            'cogs.help'
        ]
    
    async def setup_hook(self):
        """Setup hook that runs before the bot starts."""
        self.logger.info("Loading extensions...")
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                self.logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                self.logger.error(f"Failed to load extension {extension}: {e}")
                traceback.print_exc()
    
    async def on_ready(self):
        """Event triggered when the bot is ready."""
        if self.user:
            self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
            self.logger.info(f"Connected to {len(self.guilds)} guilds")
            await self.change_presence(activity=discord.Game(name="/help for commands"))
            
            # Sync slash commands with Discord (with rate limit handling)
            self.logger.info("Syncing application commands...")
            try:
                # Try to sync, catch rate limits
                try:
                    await self.tree.sync()
                except discord.HTTPException as e:
                    # Check if this is a rate limit error (code 429)
                    if hasattr(e, 'code') and e.code == 429 and hasattr(e, 'retry_after'):
                        wait_time = getattr(e, 'retry_after', 30)  # Default to 30 seconds if retry_after not available
                        self.logger.warning(f"Rate limited, waiting {wait_time:.2f} seconds")
                        await asyncio.sleep(wait_time + 1.0)
                        # Try again with a more conservative approach
                        await self.tree.sync()
                    else:
                        raise
                
                self.logger.info("Application commands synced!")
            except Exception as e:
                self.logger.error(f"Failed to sync application commands: {e}")
        else:
            self.logger.error("Bot user is None in on_ready, something went wrong with login")
    
    async def on_error(self, event_method, *args, **kwargs):
        """Global error handler for bot events."""
        self.logger.error(f"Error in {event_method}: {traceback.format_exc()}")
    
    async def on_command_error(self, ctx, error):
        """Error handler for command errors."""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Bad argument: {error}")
            return
        
        self.logger.error(f"Command error in {ctx.command}: {error}")
        await ctx.send("An error occurred while executing the command.")
