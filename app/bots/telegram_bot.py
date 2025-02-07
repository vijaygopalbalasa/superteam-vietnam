from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List
from ..core.config import settings
from ..core.rag import EnhancedRAGSystem
from .twitter_bot import TwitterManager
from ..core.content_advisor import ContentAdvisor
from ..core.database import AsyncSessionLocal

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SuperteamBot:
    def __init__(self):
        """Initialize the bot with token from settings"""
        self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        self.rag_system = EnhancedRAGSystem()
        self.twitter_manager = TwitterManager(self.rag_system)
        self._setup_handlers()
        
        # Load member database
        self.members_db = self._load_members_db()
        logger.info(f"Loaded {len(self.members_db)} members from database")

    def _load_members_db(self):
        """Load member database from JSON file"""
        try:
            db_path = Path("data/members.json")
            logger.info(f"Loading members from: {db_path.absolute()}")
            if db_path.exists():
                with open(db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            else:
                logger.warning(f"Members database not found at {db_path.absolute()}")
            return []
        except Exception as e:
            logger.error(f"Error loading members database: {e}")
            return []

    def _setup_handlers(self):
        """Set up bot command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("find", self.find_member))
        self.application.add_handler(CommandHandler("upload", self.upload_command))
        
        # Twitter handlers
        self.application.add_handler(CommandHandler("tweet", self.tweet_command))
        self.application.add_handler(CommandHandler("preview", self.preview_command))
        self.application.add_handler(CommandHandler("improve", self.improve_command))
        self.application.add_handler(CommandHandler("update", self.update_command))
        self.application.add_handler(CommandHandler("publish", self.publish_command))
        
        # Content optimization handlers
        self.application.add_handler(CommandHandler("optimize", self.optimize_command))
        self.application.add_handler(CommandHandler("abtest", self.ab_test_command))
        
        # Message handlers for documents and text
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "👋 Welcome to Superteam Vietnam Bot!\n\n"
            "I can help you with:\n"
            "🔍 Finding team members\n"
            "📚 Answering questions about Superteam\n"
            "💡 Getting information about our projects\n\n"
            "Use /help to see available commands!"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("Find Members 🔍", callback_data="find_members"),
                InlineKeyboardButton("Ask Questions ❓", callback_data="ask_questions")
            ],
            [InlineKeyboardButton("Help 📖", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🤖 Available Commands:\n\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/find <skills> - Find team members by skills\n"
            "Example: /find rust defi\n\n"
            "For Admins:\n"
            "/upload - Upload documents to knowledge base\n"
            "/tweet <text> - Create a new tweet draft\n"
            "/preview - View current tweet draft\n"
            "/improve - Get suggestions for current draft\n"
            "/update <text> - Update draft content\n"
            "/publish - Post the tweet\n"
            "/optimize <text> - Optimize content\n"
            "/abtest <text> - Create A/B test variants\n\n"
            "❓ Ask me anything about Superteam Vietnam!\n"
            "Just type your question, and I'll help you find the answer."
        )
        await update.message.reply_text(help_text)

    async def upload_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /upload command"""
        user_id = str(update.effective_user.id)
        if user_id not in settings.admin_ids:
            await update.message.reply_text("⚠️ Sorry, only admins can upload documents.")
            return
        
        await update.message.reply_text(
            "📤 Please send me the document you want to add to the knowledge base.\n"
            "Supported formats: .txt, .md, .pdf"
        )

    async def find_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /find command for member search"""
        if not context.args:
            await update.message.reply_text(
                "Please specify skills to search for.\n"
                "Example: /find rust defi"
            )
            return

        search_skills = [skill.lower() for skill in context.args]
        matches = []

        for member in self.members_db:
            member_skills = [skill.lower() for skill in member.get('skills', [])]
            matching_skills = set(search_skills) & set(member_skills)
            
            if matching_skills:
                matches.append({
                    'member': member,
                    'matching_skills': matching_skills,
                    'match_count': len(matching_skills)
                })

        if not matches:
            all_skills = set()
            for member in self.members_db:
                all_skills.update(skill.lower() for skill in member.get('skills', []))
            
            no_match_message = (
                "❌ No members found with the specified skills.\n\n"
                "Available skills in our database:\n"
                f"🔹 {', '.join(sorted(all_skills))}\n\n"
                "Try searching with one of these skills!"
            )
            await update.message.reply_text(no_match_message)
            return

        matches.sort(key=lambda x: x['match_count'], reverse=True)
        
        response = "🔍 Found matching members:\n\n"
        for idx, match in enumerate(matches[:3], 1):
            member = match['member']
            response += (
                f"{idx}. 👤 {member['name']}\n"
                f"📝 Matching skills: {', '.join(match['matching_skills'])}\n"
                f"🌟 Projects: {', '.join(member['projects'])}\n"
                f"{'✅ Available' if member.get('availability', True) else '❌ Not Available'}\n"
                f"🔗 Telegram: @{member.get('telegram_id', 'N/A')}\n"
                f"🐦 Twitter: {member.get('twitter_handle', 'N/A')}\n\n"
            )

        keyboard = []
        if len(matches) > 3:
            keyboard = [[InlineKeyboardButton(
                "Show More Members 👥", 
                callback_data=f"more_members_{','.join(search_skills)}"
            )]]

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await update.message.reply_text(response, reply_markup=reply_markup)

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads"""
        user_id = str(update.effective_user.id)
        if user_id not in settings.admin_ids:
            await update.message.reply_text("⚠️ Sorry, only admins can upload documents.")
            return

        try:
            document = update.message.document
            file = await document.get_file()
            
            upload_dir = Path("data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = upload_dir / document.file_name
            await file.download_to_drive(str(file_path))
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = {
                "filename": document.file_name,
                "uploaded_by": user_id,
                "date": str(update.message.date)
            }
            
            processing_msg = await update.message.reply_text("Processing document...")
            success = await self.rag_system.add_document(content, metadata)
            
            if success:
                await processing_msg.edit_text(
                    "✅ Document successfully added to the knowledge base!"
                )
            else:
                await processing_msg.edit_text(
                    "❌ Failed to process the document. Please try again."
                )
                
        except Exception as e:
            logger.error(f"Error handling document upload: {e}")
            await update.message.reply_text(
                "❌ Error processing the document. Please make sure it's a valid text file."
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general messages and questions"""
        text = update.message.text
        
        processing_message = await update.message.reply_text(
            "🤔 Processing your question..."
        )
        
        try:
            result = await self.rag_system.query(text)
            answer = result["answer"]
            confidence = result["confidence"]
            
            if confidence >= 0.9:
                confidence_indicator = "🟢 High Confidence"
            elif confidence >= 0.7:
                confidence_indicator = "🟡 Moderate Confidence"
            else:
                confidence_indicator = "🔴 Low Confidence"
            
            response = f"{answer}\n\n{confidence_indicator}"
            await processing_message.edit_text(response)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await processing_message.edit_text(
                "❌ Sorry, I encountered an error. Please try again later."
            )

    async def optimize_message(self, message: str) -> Dict:
        """Optimize a message using ContentAdvisor"""
        try:
            async with AsyncSessionLocal() as session:
                advisor = ContentAdvisor(self.rag_system, session)
                result = await advisor.optimize_content(message, "telegram")
                return result
        except Exception as e:
            logger.error(f"Error optimizing message: {e}")
            return {
                "status": "error",
                "message": "Failed to optimize content"
            }

    async def optimize_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /optimize command"""
        if not context.args:
            await update.message.reply_text(
                "Please provide content to optimize after the /optimize command.\n"
                "Example: /optimize Welcome to Superteam Vietnam!"
            )
            return

        content = " ".join(context.args)
        processing_msg = await update.message.reply_text("🔄 Optimizing content...")
        
        result = await self.optimize_message(content)
        
        if result["status"] == "success":
            response = (
                "✨ Content Optimization Results:\n\n"
                f"Original: {content}\n\n"
                f"Optimized: {result['optimized_content']}\n\n"
                "Suggestions:\n"
            )
            for suggestion in result["suggestions"]:
                response += f"• {suggestion}\n"
                
            if result["tags"]["hashtags"]:
                response += "\nRecommended Hashtags:\n"
                for hashtag in result["tags"]["hashtags"]:
                    response += f"• {hashtag}\n"
                    
            response += f"\nEngagement Score: {result['metrics']['engagement_score']}/100"
            
            await processing_msg.edit_text(response)
        else:
            await processing_msg.edit_text(f"❌ {result['message']}")

    async def ab_test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /abtest command"""
        if not context.args:
            await update.message.reply_text(
                "Please provide content to A/B test after the /abtest command.\n"
                "Example: /abtest Welcome to Superteam Vietnam!"
            )
            return

        content = " ".join(context.args)
        processing_msg = await update.message.reply_text("🔄 Generating A/B test variants...")
        
        try:
            async with AsyncSessionLocal() as session:
                advisor = ContentAdvisor(self.rag_system, session)
                variants = await advisor.get_ab_test_variants(content, "telegram")
                
            response = "🔄 A/B Test Variants:\n\n"
            for variant in variants:
                response += (
                    f"Variant {variant['variant']}:\n"
                    f"{variant['content']}\n"
                    f"Predicted Engagement: {variant['metrics'].get('engagement_score', 'N/A')}/100\n\n"
                )
                
            keyboard = []
            for variant in variants:
                keyboard.append([
                    InlineKeyboardButton(
                        f"Use Variant {variant['variant']}", 
                        callback_data=f"use_variant_{variant['variant']}"
                    )
                ])
                
            reply_markup = InlineKeyboardMarkup(keyboard)
            await processing_msg.edit_text(response, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error generating A/B test variants: {e}")
            await processing_msg.edit_text("❌ Failed to generate A/B test variants")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline buttons"""
        query = update.callback_query
        await query.answer()

        if query.data == "find_members":
            await query.message.reply_text(
                "To find members, use the /find command followed by the skills you're looking for.\n"
                "Example: /find rust defi"
            )
        elif query.data == "ask_questions":
            await query.message.reply_text(
                "Just type your question about Superteam Vietnam, and I'll do my best to help!"
            )
        elif query.data == "help":
            await self.help_command(query, context)
        elif query.data.startswith("more_members_"):
            skills = query.data.replace("more_members_", "").split(',')
            await self.show_more_members(query.message, skills)
        elif query.data.startswith("use_variant_"):
            variant = query.data.replace("use_variant_", "")
            await query.message.reply_text(f"Selected variant {variant}. Use /optimize to continue optimizing this content.")

    async def show_more_members(self, message: Update.message, skills: list):
        """Show additional members for the given skills"""
        matches = []
        for member in self.members_db:
            member_skills = [skill.lower() for skill in member.get('skills', [])]
            matching_skills = set(skills) & set(member_skills)
            
            if matching_skills:
                matches.append({
                    'member': member,
                    'matching_skills': matching_skills,
                    'match_count': len(matching_skills)
                })
        
        matches.sort(key=lambda x: x['match_count'], reverse=True)
        
        if len(matches) <= 3:
            await message.reply_text("No additional members to show.")
            return
        
        response = "📋 Additional matching members:\n\n"
        for idx, match in enumerate(matches[3:6], 4):  # Start from 4th match
            member = match['member']
            response += (
                f"{idx}. 👤 {member['name']}\n"
                f"📝 Matching skills: {', '.join(match['matching_skills'])}\n"
                f"🌟 Projects: {', '.join(member['projects'])}\n"
                f"{'✅ Available' if member.get('availability', True) else '❌ Not Available'}\n"
                f"🔗 Telegram: @{member.get('telegram_id', 'N/A')}\n"
                f"🐦 Twitter: {member.get('twitter_handle', 'N/A')}\n\n"
            )

        await message.reply_text(response)

    async def tweet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tweet command"""
        if not context.args:
            await update.message.reply_text(
                "Please provide the tweet content after the /tweet command.\n"
                "Example: /tweet Excited to announce our new Web3 workshop!"
            )
            return

        user_id = str(update.effective_user.id)
        if user_id not in settings.admin_ids:
            await update.message.reply_text("⚠️ Sorry, only admins can create tweets.")
            return

        content = " ".join(context.args)
        processing_msg = await update.message.reply_text("🔄 Processing your tweet draft...")

        result = await self.twitter_manager.create_draft(user_id, content)
        
        if result['status'] == 'success':
            suggestions = result['suggestions']
            response = (
                "📝 Draft Tweet Created!\n\n"
                f"Content: {content}\n\n"
                "Suggestions for Improvement:\n"
            )
            
            for improvement in suggestions['improvements']:
                response += f"• {improvement}\n"
            
            if 'recommended_hashtags' in suggestions:
                response += "\nRecommended Hashtags:\n"
                for hashtag in suggestions['recommended_hashtags']:
                    response += f"• {hashtag}\n"
            
            response += "\nAvailable Commands:\n"
            response += "/preview - View current draft\n"
            response += "/improve - Get more suggestions\n"
            response += "/update <text> - Update draft content\n"
            response += "/publish - Post the tweet"
            
            await processing_msg.edit_text(response)
        else:
            await processing_msg.edit_text(f"❌ {result['message']}")

    async def preview_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /preview command"""
        user_id = str(update.effective_user.id)
        if user_id not in settings.admin_ids:
            await update.message.reply_text("⚠️ Sorry, only admins can preview tweets.")
            return

        result = await self.twitter_manager.preview_draft(user_id)
        
        if result['status'] == 'success':
            draft = result['draft']
            response = (
                "📝 Current Draft:\n\n"
                f"Content: {draft['content']}\n"
                f"Version: {draft['version']}\n\n"
                "Use /publish to post this tweet or /improve for more suggestions."
            )
            await update.message.reply_text(response)
        else:
            await update.message.reply_text(f"❌ {result['message']}")

    async def improve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /improve command"""
        user_id = str(update.effective_user.id)
        if user_id not in settings.admin_ids:
            await update.message.reply_text("⚠️ Sorry, only admins can use this command.")
            return

        processing_msg = await update.message.reply_text("🔄 Analyzing tweet...")
        
        result = await self.twitter_manager.improve_draft(user_id)

        if result['status'] == 'success':
            suggestions = result['suggestions']
            response = "📊 Tweet Analysis:\n\n"
            
            if suggestions['improvements']:
                response += "Suggestions for Improvement:\n"
                for improvement in suggestions['improvements']:
                    response += f"• {improvement}\n"
            
            if suggestions.get('rag_suggestions'):
                response += f"\nAI Recommendations:\n{suggestions['rag_suggestions']}"
            
            await processing_msg.edit_text(response)
        else:
            await processing_msg.edit_text(f"❌ {result['message']}")

    async def update_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /update command"""
        if not context.args:
            await update.message.reply_text(
                "Please provide the new tweet content after the /update command.\n"
                "Example: /update Updated announcement with more details!"
            )
            return

        user_id = str(update.effective_user.id)
        if user_id not in settings.admin_ids:
            await update.message.reply_text("⚠️ Sorry, only admins can update tweets.")
            return

        new_content = " ".join(context.args)
        processing_msg = await update.message.reply_text("🔄 Updating draft...")
        
        result = await self.twitter_manager.update_draft(user_id, new_content)
        
        if result['status'] == 'success':
            suggestions = result['suggestions']
            response = (
                "✅ Draft Updated!\n\n"
                f"New Content: {new_content}\n\n"
                "Suggestions for Improvement:\n"
            )
            
            for improvement in suggestions['improvements']:
                response += f"• {improvement}\n"
                
            await processing_msg.edit_text(response)
        else:
            await processing_msg.edit_text(f"❌ {result['message']}")

    async def publish_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /publish command"""
        user_id = str(update.effective_user.id)
        if user_id not in settings.admin_ids:
            await update.message.reply_text("⚠️ Sorry, only admins can publish tweets.")
            return

        processing_msg = await update.message.reply_text("🔄 Publishing tweet...")
        
        result = await self.twitter_manager.publish_draft(user_id)
        
        if result['status'] == 'success':
            response = (
                "🎉 Tweet Published Successfully!\n\n"
                f"Content: {result['content']}\n\n"
                "Create a new draft using /tweet command."
            )
            await processing_msg.edit_text(response)
        else:
            await processing_msg.edit_text(f"❌ {result['message']}")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Error occurred: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Sorry, something went wrong. Please try again later."
            )
        
        # Log detailed error information
        if context.error:
            logger.error("Exception while handling an update:", exc_info=context.error)

    def run(self):
        """Run the bot"""
        logger.info("Starting Superteam Vietnam Bot...")
        try:
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise