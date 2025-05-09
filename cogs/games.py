import discord
import random
import asyncio
import logging
from discord import app_commands
from discord.ext import commands
from enum import Enum
from typing import Optional, Literal
from utils.database import db
from utils.cooldowns import cooldown
from utils.formatting import format_cash, parse_bet_amount

logger = logging.getLogger(__name__)

class CoinSide(Enum):
    HEADS = "heads"
    TAILS = "tails"

class BlackjackAction(Enum):
    HIT = "hit"
    STAND = "stand"
    DOUBLE = "double"

class Games(commands.Cog):
    """Casino games to play and win cash"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
    
    @app_commands.command(name="coinflip", description="Flip a coin and bet on the outcome")
    @app_commands.describe(
        choice="Choose heads or tails",
        bet="Amount of cash to bet",
        hidden="Send the response only to you (default: False)"
    )
    async def coinflip(
        self, 
        interaction: discord.Interaction, 
        choice: Literal["heads", "tails"],
        bet: str,
        hidden: Optional[bool] = False
    ):
        """Flip a coin and bet on the outcome"""
        await interaction.response.defer(ephemeral=hidden)
        
        user_id = str(interaction.user.id)
        user = await db.get_user(user_id)
        
        # Parse the bet amount
        bet_amount = parse_bet_amount(bet, user['cash'])
        
        # Validate the bet
        if bet_amount <= 0:
            return await interaction.followup.send("You need to bet at least 1 cash!", ephemeral=True)
        
        if bet_amount > user['cash']:
            return await interaction.followup.send(f"You don't have enough cash! You have {format_cash(user['cash'])}.", ephemeral=True)
        
        # Flip the coin
        result = random.choice(["heads", "tails"])
        won = choice == result
        
        # Calculate winnings
        winnings = bet_amount if won else -bet_amount
        
        # Update user cash
        user['cash'] += winnings
        user['games_played'] += 1
        
        if won:
            user['wins'] += 1
            user['total_cash_won'] += bet_amount
        else:
            user['losses'] += 1
            user['total_cash_lost'] += bet_amount
        
        # Add XP
        xp_gained = 1
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
        
        # Update global stats
        await db.update_stats(bet_amount, won)
        
        # Create the embed
        if won:
            color = discord.Color.green()
            title = "You Won!"
            description = f"The coin landed on **{result}**. You won {format_cash(bet_amount)} cash!{level_up_message}"
        else:
            color = discord.Color.red()
            title = "You Lost!"
            description = f"The coin landed on **{result}**. You lost {format_cash(bet_amount)} cash!{level_up_message}"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        
        embed.add_field(name="Your Choice", value=choice.capitalize(), inline=True)
        embed.add_field(name="Result", value=result.capitalize(), inline=True)
        embed.add_field(name="Cash", value=format_cash(user['cash']), inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=hidden)
    
    @app_commands.command(name="blackjack", description="Play a game of blackjack")
    @app_commands.describe(
        bet="Amount of cash to bet",
        hard="Play in hard mode for better odds (default: False)",
        hidden="Send the response only to you (default: False)"
    )
    async def blackjack(
        self, 
        interaction: discord.Interaction, 
        bet: str,
        hard: Optional[bool] = False,
        hidden: Optional[bool] = False
    ):
        """Play a game of blackjack"""
        user_id = str(interaction.user.id)
        
        # Check if the user already has an active game
        if user_id in self.active_games:
            return await interaction.response.send_message(
                "You already have an active blackjack game! Finish it before starting a new one.",
                ephemeral=True
            )
        
        user = await db.get_user(user_id)
        
        # Parse the bet amount
        bet_amount = parse_bet_amount(bet, user['cash'])
        
        # Validate the bet
        if bet_amount <= 0:
            return await interaction.response.send_message("You need to bet at least 1 cash!", ephemeral=True)
        
        if bet_amount > user['cash']:
            return await interaction.response.send_message(
                f"You don't have enough cash! You have {format_cash(user['cash'])}.",
                ephemeral=True
            )
        
        # Mark this user as having an active game
        self.active_games[user_id] = True
        
        await interaction.response.defer(ephemeral=hidden)
        
        # Initialize game state
        suits = ["♠️", "♥️", "♦️", "♣️"]
        ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        
        # Create deck and shuffle
        deck = [(rank, suit) for suit in suits for rank in ranks]
        random.shuffle(deck)
        
        # Deal initial cards
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        
        # Game state flags
        game_over = False
        player_busted = False
        player_blackjack = False
        dealer_blackjack = False
        result_message = ""
        winnings = 0
        
        # Calculate hand value function
        def calculate_hand_value(hand):
            value = 0
            aces = 0
            
            for rank, _ in hand:
                if rank in ["J", "Q", "K"]:
                    value += 10
                elif rank == "A":
                    aces += 1
                    value += 11
                else:
                    value += int(rank)
            
            # Adjust for aces
            while value > 21 and aces > 0:
                value -= 10
                aces -= 1
            
            return value
        
        # Format hand function
        def format_hand(hand, hide_second=False):
            if hide_second and len(hand) > 1:
                return f"{hand[0][0]}{hand[0][1]} ??"
            return " ".join(f"{rank}{suit}" for rank, suit in hand)
        
        # Check for initial blackjack
        player_value = calculate_hand_value(player_hand)
        dealer_value = calculate_hand_value(dealer_hand)
        
        if player_value == 21:
            player_blackjack = True
            
        if dealer_value == 21:
            dealer_blackjack = True
        
        # Create initial game embed
        async def create_game_embed():
            embed = discord.Embed(
                title=f"Blackjack - {'Hard Mode' if hard else 'Normal Mode'}",
                description=f"Bet: {format_cash(bet_amount)}",
                color=discord.Color.gold()
            )
            
            # Show dealer's hand (hiding second card if game not over)
            if game_over:
                embed.add_field(
                    name=f"Dealer's Hand ({calculate_hand_value(dealer_hand)})",
                    value=format_hand(dealer_hand),
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"Dealer's Hand ({calculate_hand_value([dealer_hand[0]])}+?)",
                    value=format_hand(dealer_hand, hide_second=True),
                    inline=False
                )
            
            # Show player's hand
            embed.add_field(
                name=f"Your Hand ({calculate_hand_value(player_hand)})",
                value=format_hand(player_hand),
                inline=False
            )
            
            # Add result message if game is over
            if game_over:
                embed.add_field(name="Result", value=result_message, inline=False)
                embed.add_field(name="Cash", value=format_cash(user['cash'] + winnings), inline=True)
            
            return embed
        
        # Create action row with buttons
        async def create_action_row():
            hit_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Hit", custom_id="hit")
            stand_button = discord.ui.Button(style=discord.ButtonStyle.success, label="Stand", custom_id="stand")
            double_button = discord.ui.Button(
                style=discord.ButtonStyle.danger, 
                label="Double Down", 
                custom_id="double",
                disabled=(len(player_hand) > 2 or bet_amount > user['cash'])
            )
            
            view = discord.ui.View()
            view.add_item(hit_button)
            view.add_item(stand_button)
            view.add_item(double_button)
            
            return view
        
        # Send initial game state
        embed = await create_game_embed()
        
        # Check for immediate blackjack
        if player_blackjack or dealer_blackjack:
            game_over = True
            
            if player_blackjack and dealer_blackjack:
                result_message = "Push! Both had blackjack. Your bet is returned."
                winnings = 0
            elif player_blackjack:
                result_message = "Blackjack! You win 1.5x your bet!"
                winnings = int(bet_amount * 1.5)
            elif dealer_blackjack:
                result_message = "Dealer has blackjack! You lose your bet."
                winnings = -bet_amount
            
            embed = await create_game_embed()
            await interaction.followup.send(embed=embed, ephemeral=hidden)
            
            # Update user stats
            if winnings > 0:
                user['wins'] += 1
                user['total_cash_won'] += winnings
            elif winnings < 0:
                user['losses'] += 1
                user['total_cash_lost'] += abs(winnings)
            
            user['cash'] += winnings
            user['games_played'] += 1
            user['xp'] += 5
            
            # Check for level up
            old_level = user['level']
            new_level = int(user['xp'] / 100)
            
            if new_level > old_level:
                user['level'] = new_level
                await interaction.followup.send(f"🎉 Level up! You are now level {new_level}!", ephemeral=hidden)
            
            await db.update_user(user_id, user)
            await db.update_stats(bet_amount, winnings > 0)
            
            # Remove active game flag
            del self.active_games[user_id]
            return
        
        # Create view with buttons
        view = await create_action_row()
        message = await interaction.followup.send(embed=embed, view=view, ephemeral=hidden)
        
        # Wait for button clicks
        def check(i):
            return i.user.id == interaction.user.id and i.message.id == message.id
        
        try:
            while not game_over:
                button_interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
                action = button_interaction.data["custom_id"]
                
                # Handle different actions
                if action == "hit":
                    # Deal a card to the player
                    player_hand.append(deck.pop())
                    player_value = calculate_hand_value(player_hand)
                    
                    if player_value > 21:
                        game_over = True
                        player_busted = True
                        result_message = "Bust! You went over 21 and lost your bet."
                        winnings = -bet_amount
                    
                    embed = await create_game_embed()
                    
                    if game_over:
                        await button_interaction.response.edit_message(embed=embed, view=None)
                    else:
                        view = await create_action_row()
                        await button_interaction.response.edit_message(embed=embed, view=view)
                
                elif action == "stand":
                    game_over = True
                    
                    # Dealer plays
                    dealer_value = calculate_hand_value(dealer_hand)
                    
                    # In hard mode, dealer hits on soft 17
                    dealer_stand_value = 17
                    if hard and dealer_value == 17:
                        for rank, _ in dealer_hand:
                            if rank == "A":
                                dealer_stand_value = 18
                                break
                    
                    while dealer_value < dealer_stand_value:
                        dealer_hand.append(deck.pop())
                        dealer_value = calculate_hand_value(dealer_hand)
                    
                    player_value = calculate_hand_value(player_hand)
                    
                    # Determine winner
                    if dealer_value > 21:
                        result_message = "Dealer busts! You win your bet!"
                        winnings = bet_amount
                    elif dealer_value > player_value:
                        result_message = f"Dealer wins with {dealer_value} against your {player_value}. You lose your bet."
                        winnings = -bet_amount
                    elif dealer_value < player_value:
                        result_message = f"You win with {player_value} against dealer's {dealer_value}! You win your bet!"
                        winnings = bet_amount
                    else:
                        result_message = f"Push! Both have {player_value}. Your bet is returned."
                        winnings = 0
                    
                    embed = await create_game_embed()
                    await button_interaction.response.edit_message(embed=embed, view=None)
                
                elif action == "double":
                    game_over = True
                    
                    # Double the bet and get one card
                    bet_amount *= 2
                    player_hand.append(deck.pop())
                    player_value = calculate_hand_value(player_hand)
                    
                    if player_value > 21:
                        player_busted = True
                        result_message = "Bust! You went over 21 and lost your doubled bet."
                        winnings = -bet_amount
                    else:
                        # Dealer plays
                        dealer_value = calculate_hand_value(dealer_hand)
                        
                        # In hard mode, dealer hits on soft 17
                        dealer_stand_value = 17
                        if hard and dealer_value == 17:
                            for rank, _ in dealer_hand:
                                if rank == "A":
                                    dealer_stand_value = 18
                                    break
                        
                        while dealer_value < dealer_stand_value:
                            dealer_hand.append(deck.pop())
                            dealer_value = calculate_hand_value(dealer_hand)
                        
                        # Determine winner
                        if dealer_value > 21:
                            result_message = "Dealer busts! You win your doubled bet!"
                            winnings = bet_amount
                        elif dealer_value > player_value:
                            result_message = f"Dealer wins with {dealer_value} against your {player_value}. You lose your doubled bet."
                            winnings = -bet_amount
                        elif dealer_value < player_value:
                            result_message = f"You win with {player_value} against dealer's {dealer_value}! You win your doubled bet!"
                            winnings = bet_amount
                        else:
                            result_message = f"Push! Both have {player_value}. Your doubled bet is returned."
                            winnings = 0
                    
                    embed = await create_game_embed()
                    await button_interaction.response.edit_message(embed=embed, view=None)
            
            # Game is over, update stats
            user = await db.get_user(user_id)  # Get fresh user data
            
            if winnings > 0:
                user['wins'] += 1
                user['total_cash_won'] += winnings
            elif winnings < 0:
                user['losses'] += 1
                user['total_cash_lost'] += abs(winnings)
            
            user['cash'] += winnings
            user['games_played'] += 1
            
            # Add XP (more for blackjack since it's more complex)
            xp_gained = 5
            user['xp'] += xp_gained
            
            # Check for level up
            old_level = user['level']
            new_level = int(user['xp'] / 100)
            
            if new_level > old_level:
                user['level'] = new_level
                await interaction.followup.send(f"🎉 Level up! You are now level {new_level}!", ephemeral=hidden)
            
            await db.update_user(user_id, user)
            await db.update_stats(bet_amount, winnings > 0)
        
        except asyncio.TimeoutError:
            # If the player doesn't respond in time, they forfeit
            if not game_over:
                game_over = True
                result_message = "Timed out! You didn't make a move in time and forfeit your bet."
                winnings = -bet_amount
                
                # Update user stats
                user = await db.get_user(user_id)
                user['losses'] += 1
                user['total_cash_lost'] += bet_amount
                user['cash'] -= bet_amount
                user['games_played'] += 1
                
                await db.update_user(user_id, user)
                await db.update_stats(bet_amount, False)
                
                embed = await create_game_embed()
                await message.edit(embed=embed, view=None)
        
        finally:
            # Always remove the active game flag
            if user_id in self.active_games:
                del self.active_games[user_id]

    @app_commands.command(name="slots", description="Try your luck in the slots!")
    @app_commands.describe(bet="The amount to bet. Use `m` for max and `a` for all in")
    async def slots(self, interaction: discord.Interaction, bet: str):
        """Try your luck in the slots!"""
        await interaction.response.defer()

        user_id = str(interaction.user.id)
        user = await db.get_user(user_id)

        # Parse the bet amount
        bet_amount = parse_bet_amount(bet, user['cash'])

        # Validate the bet
        if bet_amount <= 0:
            return await interaction.followup.send("You need to bet at least 1 cash!", ephemeral=True)

        if bet_amount > user['cash']:
            return await interaction.followup.send(f"You don't have enough cash! You have {format_cash(user['cash'])}.", ephemeral=True)

        # Define slot machine items and their probabilities
        slot_items = {
            "sseven": {"emoji": "https://thebotdev.co.uk/images/emoji/sseven.png", "weight": 1},
            "sdiamond": {"emoji": "https://thebotdev.co.uk/images/emoji/sdiamond.png", "weight": 2},
            "sbar": {"emoji": "https://thebotdev.co.uk/images/emoji/sbar.png", "weight": 4},
            "sbell": {"emoji": "https://thebotdev.co.uk/images/emoji/sbell.png", "weight": 6},
            "sshoe": {"emoji": "https://thebotdev.co.uk/images/emoji/sshoe.png", "weight": 8},
            "slemon": {"emoji": "https://thebotdev.co.uk/images/emoji/slemon.png", "weight": 10},
            "smelon": {"emoji": "https://thebotdev.co.uk/images/emoji/smelon.png", "weight": 12},
            "sheart": {"emoji": "https://thebotdev.co.uk/images/emoji/sheart.png", "weight": 14},
            "scherry": {"emoji": "https://thebotdev.co.uk/images/emoji/scherry.png", "weight": 16},
        }

        # Generate slot result
        items = list(slot_items.keys())
        weights = [slot_items[item]["weight"] for item in items]
        slot_result = random.choices(items, weights, k=3)

        # Calculate payout
        def calculate_payout(result):
            counts = {}
            for item in result:
                counts[item] = counts.get(item, 0) + 1

            payouts = {
                "sseven": {3: 500, 2: 25},
                "sdiamond": {3: 25, 2: 10},
                "sbar": {3: 5, 2: 3},
                "sbell": {3: 3, 2: 2},
                "sshoe": {3: 2, 2: 1},
                "slemon": {3: 1, 2: 1},
                "smelon": {3: 0.75, 2: 1},
                "sheart": {3: 0.5, 2: 0.75},
                "scherry": {3: 0.5, 2: 0.25},
            }

            best_payout = 0
            for item, count in counts.items():
                if item in payouts and count in payouts[item]:
                    payout = payouts[item][count]
                    if payout > best_payout:
                        best_payout = payout

            return best_payout * bet_amount

        payout = calculate_payout(slot_result)

        # Update user cash
        user['cash'] += payout
        user['games_played'] += 1
        if payout > 0:
            user['wins'] += 1
            user['total_cash_won'] += payout
        else:
            user['losses'] += 1
            user['total_cash_lost'] += bet_amount

        # Add XP
        xp_gained = 3
        user['xp'] += xp_gained

        # Check for level up
        old_level = user['level']
        new_level = int(user['xp'] / 100)

        if new_level > old_level:
            user['level'] = new_level
            level_up_message = f"\n🎉 Level up! You are now level {new_level}!"
        else:
            level_up_message = ""

        # Save user data
        await db.update_user(user_id, user)

        # Update global stats
        await db.update_stats(bet_amount, payout > 0)

        # Create embed
        embed = discord.Embed(title="Slot Machine", color=discord.Color.purple())
        slot_emojis = [slot_items[item]["emoji"] for item in slot_result]
        embed.add_field(name="Result", value=" ".join(slot_emojis), inline=False)

        if payout > 0:
            embed.add_field(name="Payout", value=f"You won {format_cash(payout)} cash!{level_up_message}", inline=False)
        else:
            embed.add_field(name="Payout", value=f"You lost {format_cash(bet_amount)} cash!{level_up_message}", inline=False)

        embed.add_field(name="Cash", value=format_cash(user['cash']), inline=False)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Games(bot))
