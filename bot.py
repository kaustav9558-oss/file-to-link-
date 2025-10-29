import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from urllib.parse import quote_plus

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Get your bot token from BotFather
BOT_TOKEN = "8284124222:AAEi9DoR5ygBa382Z7b6ho-xmNQjl2RCm3s"
# The base URL of the Vercel streaming service
VERCEL_BASE_URL = "https://telegram-file-streamer-vercel.vercel.app"
# The base URL for the Telegram Bot API file download (optional, but good for clarity)
TELEGRAM_FILE_BASE_URL = "https://api.telegram.org/file/bot"

# --- Utility Functions ---

def get_telegram_file_url(file_path: str) -> str:
    """Constructs the full Telegram file download URL."""
    if not BOT_TOKEN:
        return ""
    return f"{TELEGRAM_FILE_BASE_URL}{BOT_TOKEN}/{file_path}"

def generate_vercel_links(file_name: str, telegram_file_url: str) -> tuple[str, str]:
    """Generates the Vercel streaming and download links."""
    # URL-encode the full Telegram file URL
    encoded_telegram_url = quote_plus(telegram_file_url)
    
    # URL-encode the file name for the path part
    encoded_file_name = quote_plus(file_name)

    # Streaming Link
    streaming_link = (
        f"{VERCEL_BASE_URL}/watch/{encoded_file_name}"
        f"?file_url={encoded_telegram_url}"
    )

    # Download Link
    download_link = (
        f"{VERCEL_BASE_URL}/download/{encoded_file_name}"
        f"?file_url={encoded_telegram_url}"
    )
    
    return streaming_link, download_link

# --- Telegram Handlers ---

async def start(update: Update, context) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Hello! Send me a file (video, document, audio) and I will generate "
        "streaming and direct download links for you using the Vercel service."
    )

async def handle_file(update: Update, context) -> None:
    """Handles incoming files (documents, videos, audio)."""
    message = update.message
    
    # 1. Identify the file object and name
    file_object = None
    file_name = "file" # Default name
    
    if message.document:
        file_object = message.document
        file_name = file_object.file_name or "document"
    elif message.video:
        file_object = message.video
        file_name = file_object.file_name or "video.mp4"
    elif message.audio:
        file_object = message.audio
        file_name = file_object.file_name or "audio.mp3"
    
    if not file_object:
        # Should not happen if the filter is set correctly, but good for safety
        await message.reply_text("I received a message, but it doesn't seem to contain a supported file.")
        return

    await message.reply_text("Processing file... Please wait.")

    try:
        # 2. Get the file path from Telegram API
        # get_file() returns a File object which contains the file_path
        telegram_file = await context.bot.get_file(file_object.file_id)
        
        if not telegram_file.file_path:
            await message.reply_text("Could not retrieve file path from Telegram. Please try again.")
            return

        # 3. Construct the full Telegram file URL
        telegram_file_url = get_telegram_file_url(telegram_file.file_path)
        
        if not telegram_file_url:
            await message.reply_text("Bot token is not configured. Cannot generate links.")
            return

        # 4. Generate Vercel links
        streaming_link, download_link = generate_vercel_links(file_name, telegram_file_url)

        # 5. Send the links back to the user
        keyboard = [
            [InlineKeyboardButton("🔗 Stream File", url=streaming_link)],
            [InlineKeyboardButton("⬇️ Download File", url=download_link)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_text(
            f"✅ **Links Generated for:** `{file_name}`\n\n"
            "Use the buttons below to stream or download your file.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await message.reply_text(
            "An error occurred while generating the links. "
            "Please check the bot token and ensure the file is accessible."
        )

async def error_handler(update: Update, context) -> None:
    """Log the error and send a message to the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    # Note: In a production environment, you might want a more user-friendly error message
    # or a way to notify the developer.

def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("Cannot start bot: BOT_TOKEN is missing.")
        return

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    
    # Message handler for files (documents, videos, audio)
    # We use ~filters.COMMAND to ensure it doesn't process /start as a file
    file_filter = filters.ATTACHMENT | filters.VIDEO | filters.AUDIO
    application.add_handler(MessageHandler(file_filter & ~filters.COMMAND, handle_file))

    # Error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    # For Render, we typically use webhook, but for simplicity and common
    # use cases, we'll stick to long polling which is easier for simple
    # deployments unless a specific webhook setup is requested.
    # For Render, the user will need to configure the environment to run this
    # script, likely using a 'web service' with a simple start command.
    logger.info("Starting bot in polling mode...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()    
