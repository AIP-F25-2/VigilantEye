"""Telegram notification service."""

import asyncio
from pathlib import Path
from typing import Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TelegramService:
    """Service for sending Telegram notifications."""

    def __init__(self):
        """Initialize Telegram bot."""
        self.bot_token = settings.telegram_bot_token
        self.primary_chat_id = settings.telegram_primary_chat_id
        self.escalation_chat_id = settings.telegram_escalation_chat_id
        
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            self.bot = None
            return
        
        self.bot = Bot(token=self.bot_token)
        logger.info("Telegram bot initialized")

    async def send_threat_alert(
        self,
        ticket_number: str,
        threat_description: str,
        threat_level: str,
        image_path: Optional[str] = None,
        video_id: int = None,
        frame_timestamp_ms: int = None,
        ticket_id: int = None,
    ) -> Optional[str]:
        """
        Send threat alert to primary Telegram group.
        
        Args:
            ticket_number: Ticket number
            threat_description: Threat description
            threat_level: Threat level
            image_path: Path to threat image
            video_id: Video ID
            frame_timestamp_ms: Frame timestamp
            ticket_id: Ticket ID
            
        Returns:
            Message ID if sent successfully
        """
        if not self.bot:
            logger.warning("Telegram bot not configured, skipping notification")
            return None
        
        try:
            # Format message
            message = self._format_threat_message(
                ticket_number,
                threat_description,
                threat_level,
                video_id,
                frame_timestamp_ms
            )
            
            # Create acknowledge button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "✅ Acknowledge",
                    callback_data=f"ack_{ticket_id}"
                )],
                [InlineKeyboardButton(
                    "📝 Add Note",
                    callback_data=f"note_{ticket_id}"
                )],
                [InlineKeyboardButton(
                    "🔒 Close",
                    callback_data=f"close_{ticket_id}"
                )]
            ])
            
            # Send message with image
            if image_path and Path(image_path).exists():
                with open(image_path, 'rb') as photo:
                    msg = await self.bot.send_photo(
                        chat_id=self.primary_chat_id,
                        photo=photo,
                        caption=message,
                        reply_markup=keyboard,
                        parse_mode='HTML'
                    )
            else:
                msg = await self.bot.send_message(
                    chat_id=self.primary_chat_id,
                    text=message,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            
            logger.info(f"Threat alert sent to Telegram: {ticket_number}")
            return str(msg.message_id)
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}", exc_info=True)
            return None

    async def send_escalation_alert(
        self,
        ticket_number: str,
        threat_description: str,
        threat_level: str,
        minutes_elapsed: int,
        original_message_link: Optional[str] = None,
        ticket_id: int = None,
    ) -> Optional[str]:
        """
        Send escalation alert to escalation Telegram group.
        
        Args:
            ticket_number: Ticket number
            threat_description: Threat description
            threat_level: Threat level
            minutes_elapsed: Minutes since original alert
            original_message_link: Link to original message
            ticket_id: Ticket ID
            
        Returns:
            Message ID if sent successfully
        """
        if not self.bot:
            return None
        
        try:
            # Format escalation message
            message = (
                f"🚨 <b>ESCALATED THREAT - NO ACKNOWLEDGMENT</b> 🚨\n\n"
                f"<b>Ticket:</b> {ticket_number}\n"
                f"<b>Level:</b> {threat_level}\n"
                f"<b>Time Elapsed:</b> {minutes_elapsed} minutes\n\n"
                f"<b>Description:</b>\n{threat_description}\n\n"
                f"⚠️ <i>Original alert was not acknowledged</i>"
            )
            
            if original_message_link:
                message += f"\n\n<a href='{original_message_link}'>View Original Message</a>"
            
            # Create urgent acknowledge button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔴 URGENT ACKNOWLEDGE",
                    callback_data=f"ack_{ticket_id}"
                )],
                [InlineKeyboardButton(
                    "🔒 Close Ticket",
                    callback_data=f"close_{ticket_id}"
                )]
            ])
            
            msg = await self.bot.send_message(
                chat_id=self.escalation_chat_id,
                text=message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            logger.info(f"Escalation alert sent: {ticket_number}")
            return str(msg.message_id)
            
        except Exception as e:
            logger.error(f"Failed to send escalation alert: {e}", exc_info=True)
            return None

    async def update_message_status(
        self,
        chat_id: str,
        message_id: str,
        new_status: str,
        acknowledged_by: Optional[str] = None
    ) -> bool:
        """
        Update message to show new status.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID
            new_status: New status
            acknowledged_by: User who acknowledged
            
        Returns:
            True if updated successfully
        """
        if not self.bot:
            return False
        
        try:
            status_emoji = {
                'ACKNOWLEDGED': '✅',
                'ESCALATED': '🚨',
                'CLOSED': '🔒',
                'AUTO_CLOSED': '⏰'
            }
            
            emoji = status_emoji.get(new_status, '📍')
            
            status_text = f"\n\n{emoji} <b>Status: {new_status}</b>"
            if acknowledged_by:
                status_text += f"\n<i>By: {acknowledged_by}</i>"
            
            # Remove keyboard buttons
            await self.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=int(message_id),
                reply_markup=None
            )
            
            logger.info(f"Updated Telegram message status: {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update message status: {e}")
            return False

    def _format_threat_message(
        self,
        ticket_number: str,
        description: str,
        level: str,
        video_id: Optional[int],
        timestamp_ms: Optional[int]
    ) -> str:
        """Format threat message for Telegram."""
        level_emoji = {
            'LOW': '🟡',
            'MEDIUM': '🟠',
            'HIGH': '🔴',
            'CRITICAL': '🚨'
        }
        
        emoji = level_emoji.get(level, '⚠️')
        
        message = (
            f"{emoji} <b>THREAT DETECTED</b> {emoji}\n\n"
            f"<b>Ticket:</b> {ticket_number}\n"
            f"<b>Level:</b> {level}\n"
        )
        
        if video_id:
            message += f"<b>Video ID:</b> {video_id}\n"
        
        if timestamp_ms:
            seconds = timestamp_ms / 1000
            message += f"<b>Timestamp:</b> {seconds:.2f}s\n"
        
        message += f"\n<b>Description:</b>\n{description}\n\n"
        message += "⚡️ <i>Please acknowledge or close this ticket</i>"
        
        return message


# Global Telegram service instance
_telegram_service: Optional[TelegramService] = None


def get_telegram_service() -> TelegramService:
    """Get global Telegram service instance."""
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramService()
    return _telegram_service


async def handle_telegram_callback(update: Update, context) -> None:
    """
    Handle Telegram callback button presses.
    
    This function should be registered with the Telegram bot.
    """
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user = query.from_user
    
    logger.info(f"Telegram callback: {callback_data} from {user.username}")
    
    # Parse callback data
    action, ticket_id = callback_data.split('_', 1)
    
    # Import here to avoid circular dependency
    from src.services.ticket_service import get_ticket_service
    from src.database.session import DatabaseSession
    
    # Process action
    db = DatabaseSession()
    async with db.get_session() as session:
        ticket_service = get_ticket_service(session)
        
        if action == 'ack':
            # Acknowledge ticket
            await ticket_service.acknowledge_ticket(
                int(ticket_id),
                acknowledged_by=user.username or user.first_name
            )
            await query.edit_message_text(
                text=query.message.text + f"\n\n✅ <b>ACKNOWLEDGED</b> by {user.first_name}",
                parse_mode='HTML'
            )
            
        elif action == 'close':
            # Close ticket
            await ticket_service.close_ticket(
                int(ticket_id),
                closed_by=user.username or user.first_name,
                notes="Closed via Telegram"
            )
            await query.edit_message_text(
                text=query.message.text + f"\n\n🔒 <b>CLOSED</b> by {user.first_name}",
                parse_mode='HTML'
            )
        
        elif action == 'note':
            # Prompt for note
            await query.edit_message_text(
                text=query.message.text + f"\n\n📝 Please reply to this message with your note",
                parse_mode='HTML'
            )


def start_telegram_bot() -> None:
    """Start Telegram bot to listen for callbacks."""
    settings = get_settings()
    
    if not settings.telegram_bot_token:
        logger.warning("Telegram bot token not configured")
        return
    
    try:
        application = Application.builder().token(settings.telegram_bot_token).build()
        
        # Register callback handler
        application.add_handler(CallbackQueryHandler(handle_telegram_callback))
        
        # Start bot
        application.run_polling()
        
        logger.info("Telegram bot started")
        
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}", exc_info=True)
