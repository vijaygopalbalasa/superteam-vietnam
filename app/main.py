from app.bots.telegram_bot import SuperteamBot
import logging

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        # Initialize and run the bot
        logger.info("Starting Superteam Vietnam Bot...")
        bot = SuperteamBot()
        bot.run()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    main()