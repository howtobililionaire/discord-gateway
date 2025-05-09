import os
import sys
import logging
import asyncio
import threading
import time
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, jsonify, redirect, url_for, request, make_response
from flask_cors import CORS
from bot import RocketGamblingBot
from utils.database import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "rocket-gambling-bot-secret")

# Enable CORS for all routes
CORS(app)

# Track bot start time for uptime calculation
bot_start_time = None

# Global variable to store bot instance
bot_instance = None
bot_thread = None
bot_status = "Stopped"

@app.route('/')
def index():
    """Home page route"""
    global bot_status
    return render_template('index.html', bot_status=bot_status)

@app.route('/api/status')
def api_status():
    """API endpoint to get bot status"""
    global bot_status, bot_instance, bot_start_time
    
    connected_guilds = 0
    if bot_instance and hasattr(bot_instance, 'guilds'):
        connected_guilds = len(bot_instance.guilds)
    
    # Calculate uptime if the bot is running
    uptime_str = "N/A"
    if bot_start_time and bot_status == "Running":
        uptime_seconds = time.time() - bot_start_time
        
        # Format uptime
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m"
        elif hours > 0:
            uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        else:
            uptime_str = f"{int(minutes)}m {int(seconds)}s"
    
    status_data = {
        "status": bot_status,
        "connected_guilds": connected_guilds,
        "uptime": uptime_str
    }
    
    response = jsonify(status_data)
    return response

@app.route('/api/stats')
def api_stats():
    """API endpoint to get global stats"""
    global_stats = db.data.get("global_stats", {
        "total_bets": 0,
        "total_cash_won": 0,
        "total_cash_lost": 0
    })
    
    response = jsonify(global_stats)
    return response

@app.route('/api/leaderboard/<category>')
def api_leaderboard(category):
    """API endpoint to get leaderboard data"""
    if category not in ["cash", "level", "wins", "profit"]:
        category = "cash"
    
    field_mapping = {
        "cash": "cash",
        "level": "level",
        "wins": "wins",
        "profit": "total_cash_won"  # We'll handle profit calculation in the frontend
    }
    
    field = field_mapping[category]
    
    # This is a synchronous route handler, but we need to access async code
    # For a proper implementation, we'd use quart or another async-compatible framework
    leaderboard = []
    
    # As a workaround, we'll just access the data directly
    if "users" in db.data:
        # Sort users by the specified field
        sorted_users = sorted(
            [(user_id, user_data) for user_id, user_data in db.data["users"].items()],
            key=lambda x: x[1].get(field, 0),
            reverse=True
        )[:10]
        
        # Format the leaderboard data
        leaderboard = [{"id": user_id, **user_data} for user_id, user_data in sorted_users]
    
    response = jsonify(leaderboard)
    return response

# Helper method to ensure all API responses have proper CORS headers
@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    # Set CORS headers to allow requests from any origin
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

async def run_bot():
    """Run the Discord bot asynchronously"""
    global bot_instance, bot_status
    
    # Get the bot token from environment variables
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        logger.error("No Discord token found. Set the DISCORD_TOKEN environment variable.")
        bot_status = "Error: No Discord token"
        return
    
    # Initialize the bot and add a listener for the ready event
    bot_instance = RocketGamblingBot()
    
    # Add a method to update status when the bot is ready
    original_on_ready = bot_instance.on_ready
    
    async def on_ready_with_status_update():
        global bot_status, bot_start_time
        # Call the original on_ready method
        await original_on_ready()
        # Update the status when the bot is fully ready
        bot_status = "Running"
        # Set the start time for uptime tracking
        bot_start_time = time.time()
        logger.info("Bot status updated to: Running")
    
    # Replace the on_ready method
    bot_instance.on_ready = on_ready_with_status_update
    
    try:
        logger.info("Starting Rocket Gambling Bot...")
        bot_status = "Starting"
        await bot_instance.start(token)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
        bot_status = "Stopped"
        await bot_instance.close()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        bot_status = f"Error: {str(e)}"
        await bot_instance.close()

def bot_thread_function():
    """Function to run the bot in a separate thread"""
    asyncio.run(run_bot())

# Start the bot in a separate thread when the app starts
def start_bot_thread():
    """Start the bot in a background thread"""
    global bot_thread, bot_status
    
    if bot_thread is None or not bot_thread.is_alive():
        bot_thread = threading.Thread(target=bot_thread_function)
        bot_thread.daemon = True
        bot_thread.start()
        bot_status = "Starting"
        return True
    
    return False

# Calculate what mode we're running in
is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
is_bot_execution = 'REPL_WORKFLOW' in os.environ and os.environ.get('REPL_WORKFLOW') == 'bot_execution'

# Start the bot when the module is imported in the right context
if is_gunicorn:
    # Only start the bot thread in the gunicorn process
    logger.info("Running in gunicorn mode, starting bot thread")
    start_bot_thread()

if __name__ == "__main__":
    if is_bot_execution:
        # Just run the Flask app in bot_execution workflow - we don't want the bot running twice
        logger.info("Running in bot_execution workflow mode, bot NOT started")
        # The other workflow will handle the bot
        app.run(host="0.0.0.0", port=8080, debug=True)
    elif len(sys.argv) > 1 and "bot-only" in sys.argv:
        # Run only the bot without the web interface if explicitly requested
        logger.info("Running in explicit bot-only mode")
        asyncio.run(run_bot())
    else:
        # Otherwise run the Flask development server with bot thread
        logger.info("Running Flask development server with bot thread")
        start_bot_thread()
        app.run(host="0.0.0.0", port=8080, debug=True)
