import logging
import os
import time
from typing import Dict, Optional, Tuple

import redis
from jinja2 import Environment, FileSystemLoader
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, NetworkError, TelegramError, TimedOut, Unauthorized

from src.config.constants import TelegramCallbackAction
from src.config.settings import get_config
from src.models.ticket import Ticket

logger = logging.getLogger(__name__)


class MessengerError(Exception):
    """Base exception for messenger operations."""


class RateLimitExceededError(MessengerError):
    """Raised when rate limit is exceeded."""


class WebhookVerificationError(MessengerError):
    """Raised when webhook verification fails."""


class MessengerService:
    """Service layer responsible for Telegram messaging operations."""

    def __init__(self, config=None):
        self.config = config or get_config()
        self.bot_token = self.config.TELEGRAM_BOT_TOKEN
        self.webhook_secret = self.config.TELEGRAM_WEBHOOK_SECRET
        self.primary_channel = getattr(
            self.config, "TELEGRAM_PRIMARY_CHANNEL", None
        ) or self.config.TELEGRAM_ESCALATION_CHANNEL
        self.escalation_channel = self.config.TELEGRAM_ESCALATION_CHANNEL
        self.retry_attempts = self.config.TELEGRAM_RETRY_ATTEMPTS
        self.retry_delay = self.config.TELEGRAM_RETRY_DELAY
        self.rate_limit_max = getattr(self.config, "TELEGRAM_RATE_LIMIT_MAX", 10)

        # Initialize Telegram bot
        self.bot = None
        if self.bot_token:
            try:
                self.bot = Bot(token=self.bot_token)
                # Verify token by getting bot info
                bot_info = self.bot.get_me()
                logger.info(
                    "Telegram bot initialized successfully",
                    extra={
                        "context": {
                            "bot_username": bot_info.username,
                            "bot_id": bot_info.id,
                        }
                    },
                )
            except Exception as exc:
                logger.warning("Failed to initialize Telegram bot: %s", exc)
                self.bot = None

        # Initialize Redis client for rate limiting
        try:
            self.redis_client = redis.from_url(
                self.config.REDIS_URL, decode_responses=True
            )
        except redis.RedisError as exc:
            logger.warning("Redis connection failed for rate limiting: %s", exc)
            self.redis_client = None

        # Initialize Jinja2 environment for templates
        base_dir = os.path.dirname(os.path.dirname(__file__))  # Two levels up to reach backend/src
        template_dir = os.path.join(base_dir, "templates", "telegram")
        try:
            # Enable autoescape for HTML to prevent XSS and malformed messages
            self.jinja_env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=True,  # Automatically escape HTML in template variables
            )
        except Exception as exc:
            logger.warning("Failed to initialize Jinja2 environment: %s", exc)
            self.jinja_env = None

    def send_alert(
        self,
        ticket: Ticket,
        image_path: Optional[str] = None,
        audio_path: Optional[str] = None,
    ) -> Tuple[bool, Optional[Exception]]:
        """Send alert to primary channel with ticket details and optional media."""
        if not self.bot:
            return False, MessengerError("Telegram bot not initialized")

        try:
            # Check rate limit
            if not self._check_rate_limit(self.primary_channel):
                logger.warning(
                    "Rate limit exceeded for primary channel",
                    extra={"context": {"channel_id": self.primary_channel}},
                )
                return False, RateLimitExceededError("Rate limit exceeded")

            # Render alert message
            message = self._render_alert_template(ticket, template_name="alert")
            if not message:
                return False, MessengerError("Failed to render alert template")

            # Create inline keyboard with acknowledge button
            keyboard = self._create_inline_keyboard(ticket.id)

            # Send message with retry
            success, error = self._send_message_with_retry(
                channel_id=self.primary_channel,
                text=message,
                reply_markup=keyboard,
                image_path=image_path,
                audio_path=audio_path,
            )

            if success:
                # Increment rate limit counter
                self._increment_rate_limit(self.primary_channel)
                logger.info(
                    "Alert sent successfully",
                    extra={
                        "context": {
                            "ticket_id": ticket.id,
                            "channel_id": self.primary_channel,
                            "has_image": bool(image_path),
                            "has_audio": bool(audio_path),
                        }
                    },
                )
                return True, None
            else:
                logger.error(
                    "Failed to send alert",
                    extra={
                        "context": {
                            "ticket_id": ticket.id,
                            "channel_id": self.primary_channel,
                            "error": str(error) if error else "Unknown error",
                        }
                    },
                )
                return False, error

        except Exception as exc:
            logger.exception(
                "Unexpected error sending alert",
                extra={
                    "context": {
                        "ticket_id": ticket.id,
                        "channel_id": self.primary_channel,
                        "error": str(exc),
                    }
                },
            )
            return False, exc

    def send_escalation_alert(
        self,
        ticket: Ticket,
        image_path: Optional[str] = None,
        audio_path: Optional[str] = None,
    ) -> Tuple[bool, Optional[Exception]]:
        """Send escalation alert to secondary channel with optional media."""
        if not self.bot:
            return False, MessengerError("Telegram bot not initialized")

        try:
            # Check rate limit
            if not self._check_rate_limit(self.escalation_channel):
                logger.warning(
                    "Rate limit exceeded for escalation channel",
                    extra={"context": {"channel_id": self.escalation_channel}},
                )
                return False, RateLimitExceededError("Rate limit exceeded")

            # Render escalation message
            message = self._render_alert_template(ticket, template_name="escalation")
            if not message:
                return False, MessengerError("Failed to render escalation template")

            # Create inline keyboard with acknowledge button
            keyboard = self._create_inline_keyboard(ticket.id)

            # Send message with retry
            success, error = self._send_message_with_retry(
                channel_id=self.escalation_channel,
                text=message,
                reply_markup=keyboard,
                image_path=image_path,
                audio_path=audio_path,
            )

            if success:
                # Increment rate limit counter
                self._increment_rate_limit(self.escalation_channel)
                logger.info(
                    "Escalation alert sent successfully",
                    extra={
                        "context": {
                            "ticket_id": ticket.id,
                            "channel_id": self.escalation_channel,
                        }
                    },
                )
                return True, None
            else:
                logger.error(
                    "Failed to send escalation alert",
                    extra={
                        "context": {
                            "ticket_id": ticket.id,
                            "channel_id": self.escalation_channel,
                            "error": str(error) if error else "Unknown error",
                        }
                    },
                )
                return False, error

        except Exception as exc:
            logger.exception(
                "Unexpected error sending escalation alert",
                extra={
                    "context": {
                        "ticket_id": ticket.id,
                        "channel_id": self.escalation_channel,
                        "error": str(exc),
                    }
                },
            )
            return False, exc

    def _send_message_with_retry(
        self,
        channel_id: str,
        text: str,
        reply_markup=None,
        image_path: Optional[str] = None,
        audio_path: Optional[str] = None,
    ) -> Tuple[bool, Optional[Exception]]:
        """Send message with exponential backoff retry mechanism.
        
        Performs self.retry_attempts retries in addition to the initial attempt.
        Delays: 2s, 4s, 8s for attempts 1, 2, 3 (when retry_attempts=3).
        """
        last_error = None

        # Truncate text for media captions (Telegram limit: 1024 characters)
        if (image_path or audio_path) and len(text) > 1024:
            text = text[:1021] + "..."

        for attempt in range(self.retry_attempts + 1):  # +1 to include initial attempt
            try:
                if image_path and os.path.exists(image_path):
                    with open(image_path, "rb") as photo:
                        self.bot.send_photo(
                            chat_id=channel_id,
                            photo=photo,
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode="HTML",
                        )
                elif audio_path and os.path.exists(audio_path):
                    with open(audio_path, "rb") as audio:
                        self.bot.send_audio(
                            chat_id=channel_id,
                            audio=audio,
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode="HTML",
                        )
                else:
                    self.bot.send_message(
                        chat_id=channel_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode="HTML",
                    )

                # Success
                return True, None

            except (NetworkError, TimedOut) as exc:
                last_error = exc
                if attempt < self.retry_attempts:  # attempt is 0-indexed, retry if not last
                    # Delay before retry: 2s, 4s, 8s for attempts 1, 2, 3
                    # attempt 1 -> delay = 2 * (2^0) = 2s
                    # attempt 2 -> delay = 2 * (2^1) = 4s
                    # attempt 3 -> delay = 2 * (2^2) = 8s
                    if attempt > 0:  # Only sleep before retries, not before initial attempt
                        delay = self.retry_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Telegram send failed, retrying in %ds (attempt %d/%d)",
                            delay,
                            attempt + 1,
                            self.retry_attempts + 1,
                            extra={
                                "context": {
                                    "channel_id": channel_id,
                                    "attempt": attempt + 1,
                                    "error": str(exc),
                                }
                            },
                        )
                        time.sleep(delay)
                    else:
                        logger.warning(
                            "Telegram send failed, retrying immediately (attempt %d/%d)",
                            attempt + 1,
                            self.retry_attempts + 1,
                            extra={
                                "context": {
                                    "channel_id": channel_id,
                                    "attempt": attempt + 1,
                                    "error": str(exc),
                                }
                            },
                        )
                else:
                    logger.error(
                        "Telegram send failed after all retries",
                        extra={
                            "context": {
                                "channel_id": channel_id,
                                "attempts": self.retry_attempts + 1,
                                "error": str(exc),
                            }
                        },
                    )

            except (Unauthorized, BadRequest) as exc:
                # Permanent errors, don't retry
                logger.error(
                    "Telegram send failed with permanent error",
                    extra={
                        "context": {
                            "channel_id": channel_id,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        }
                    },
                )
                return False, exc

            except TelegramError as exc:
                last_error = exc
                if attempt < self.retry_attempts:  # attempt is 0-indexed, retry if not last
                    # Delay before retry: 2s, 4s, 8s for attempts 1, 2, 3
                    # attempt 1 -> delay = 2 * (2^0) = 2s
                    # attempt 2 -> delay = 2 * (2^1) = 4s
                    # attempt 3 -> delay = 2 * (2^2) = 8s
                    if attempt > 0:  # Only sleep before retries, not before initial attempt
                        delay = self.retry_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Telegram send failed, retrying in %ds (attempt %d/%d)",
                            delay,
                            attempt + 1,
                            self.retry_attempts + 1,
                            extra={
                                "context": {
                                    "channel_id": channel_id,
                                    "attempt": attempt + 1,
                                    "error": str(exc),
                                }
                            },
                        )
                        time.sleep(delay)
                    else:
                        logger.warning(
                            "Telegram send failed, retrying immediately (attempt %d/%d)",
                            attempt + 1,
                            self.retry_attempts + 1,
                            extra={
                                "context": {
                                    "channel_id": channel_id,
                                    "attempt": attempt + 1,
                                    "error": str(exc),
                                }
                            },
                        )
                else:
                    logger.error(
                        "Telegram send failed after all retries",
                        extra={
                            "context": {
                                "channel_id": channel_id,
                                "attempts": self.retry_attempts + 1,
                                "error": str(exc),
                            }
                        },
                    )

            except Exception as exc:
                # Unexpected errors
                logger.exception(
                    "Unexpected error sending Telegram message",
                    extra={
                        "context": {
                            "channel_id": channel_id,
                            "attempt": attempt + 1,
                            "error": str(exc),
                        }
                    },
                )
                return False, exc

        # All retries exhausted
        return False, last_error

    def _check_rate_limit(self, channel_id: str) -> bool:
        """Check if rate limit is exceeded for channel."""
        if not self.redis_client:
            # If Redis unavailable, skip rate limiting (graceful degradation)
            logger.warning("Redis unavailable, skipping rate limit check")
            return True

        try:
            key = f"telegram:rate_limit:{channel_id}"
            count = self.redis_client.get(key)

            if count is None:
                return True  # No limit yet

            if int(count) >= self.rate_limit_max:
                return False  # Rate limit exceeded

            return True  # Within limit

        except Exception as exc:
            logger.warning(
                "Error checking rate limit, allowing send",
                extra={"context": {"channel_id": channel_id, "error": str(exc)}},
            )
            return True  # Graceful degradation

    def _increment_rate_limit(self, channel_id: str) -> None:
        """Increment rate limit counter for channel."""
        if not self.redis_client:
            return

        try:
            key = f"telegram:rate_limit:{channel_id}"
            self.redis_client.incr(key)

            # Set expiry if new key (TTL -1 means key doesn't exist or has no expiry)
            if self.redis_client.ttl(key) == -1:
                self.redis_client.expire(key, 60)  # 60 seconds

        except Exception as exc:
            logger.warning(
                "Error incrementing rate limit",
                extra={"context": {"channel_id": channel_id, "error": str(exc)}},
            )

    def _render_alert_template(
        self, ticket: Ticket, template_name: str
    ) -> Optional[str]:
        """Render alert template with ticket data.
        
        Note: Currently using a single template (alert.html) for all threat levels.
        The template dynamically displays threat level information via context variables.
        If distinct templates per threat level are needed in the future, implement
        a mapping here (e.g., alert_critical.html, alert_high.html, etc.).
        """
        if not self.jinja_env:
            logger.error("Jinja2 environment not initialized")
            return None

        try:
            template = self.jinja_env.get_template(f"{template_name}.html")

            # Get threat level emoji
            threat_level = ticket.threat_level or "medium"
            emoji_map = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "⚡",
                "low": "ℹ️",
            }
            emoji = emoji_map.get(threat_level.lower(), "⚡")

            # Get evidence count
            evidence_count = len(ticket.evidence) if hasattr(ticket, "evidence") else 0

            # Get person count
            person_count = (
                len(ticket.persons_of_interest) if hasattr(ticket, "persons_of_interest") and ticket.persons_of_interest else 0
            )

            # Calculate time elapsed for escalation template
            time_elapsed = None
            if template_name == "escalation" and ticket.created_at:
                elapsed = (time.time() - ticket.created_at.timestamp()) / 60
                time_elapsed = int(elapsed)

            # Prepare context
            context = {
                "ticket": ticket,
                "emoji": emoji,
                "threat_level": threat_level,
                "evidence_count": evidence_count,
                "person_count": person_count,
                "time_elapsed": time_elapsed,
            }

            message = template.render(**context)
            return message

        except Exception as exc:
            logger.exception(
                "Error rendering alert template",
                extra={
                    "context": {
                        "template_name": template_name,
                        "ticket_id": ticket.id,
                        "error": str(exc),
                    }
                },
            )
            return None

    def _create_inline_keyboard(self, ticket_id: str) -> InlineKeyboardMarkup:
        """Create inline keyboard with acknowledge button."""
        button = InlineKeyboardButton(
            text="✅ Acknowledge", callback_data=f"{TelegramCallbackAction.ACKNOWLEDGE}:{ticket_id}"
        )
        keyboard = InlineKeyboardMarkup([[button]])
        return keyboard

    def handle_callback(
        self, callback_query_data: str, user_info: Dict
    ) -> Tuple[bool, Optional[Exception]]:
        """Handle callback from Telegram button click."""
        try:
            # Parse callback data: action:ticket_id
            parts = callback_query_data.split(":", 1)
            if len(parts) != 2:
                return False, MessengerError(f"Invalid callback data format: {callback_query_data}")

            action, ticket_id = parts

            if action == TelegramCallbackAction.ACKNOWLEDGE:
                # Import here to avoid circular import
                from src.services.ticket_service import TicketService

                ticket_service = TicketService()
                ticket, error = ticket_service.acknowledge_ticket(
                    ticket_id, user_id=None
                )  # System acknowledgment

                if error:
                    logger.error(
                        "Failed to acknowledge ticket from callback",
                        extra={
                            "context": {
                                "ticket_id": ticket_id,
                                "user_info": user_info,
                                "error": str(error),
                            }
                        },
                    )
                    return False, error

                logger.info(
                    "Ticket acknowledged from Telegram callback",
                    extra={
                        "context": {
                            "ticket_id": ticket_id,
                            "user_info": user_info,
                        }
                    },
                )
                return True, None
            else:
                return False, MessengerError(f"Unknown callback action: {action}")

        except Exception as exc:
            logger.exception(
                "Error handling callback",
                extra={
                    "context": {
                        "callback_data": callback_query_data,
                        "user_info": user_info,
                        "error": str(exc),
                    }
                },
            )
            return False, exc

