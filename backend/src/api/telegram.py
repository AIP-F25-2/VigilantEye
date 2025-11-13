import logging
from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from src.config.settings import get_config
from src.services.messenger_service import MessengerError, MessengerService
from src.utils.auth_middleware import admin_only

telegram_bp = Blueprint("telegram", __name__)
config = get_config()
logger = logging.getLogger(__name__)

# Lazy initialization of MessengerService to avoid heavy work at import time
_messenger_service = None


def get_messenger() -> MessengerService:
    """Get or create MessengerService instance (lazy initialization)."""
    global _messenger_service
    if _messenger_service is None:
        _messenger_service = MessengerService()
    return _messenger_service


@telegram_bp.route("/webhook", methods=["POST"])
def webhook():
    """Receive webhook callbacks from Telegram."""
    try:
        # Verify webhook secret
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret != config.TELEGRAM_WEBHOOK_SECRET:
            logger.warning(
                "Webhook verification failed",
                extra={"context": {"provided_secret": bool(secret)}},
            )
            return jsonify({"error": "Unauthorized"}), 403

        # Parse webhook payload
        update = request.get_json()
        if not update:
            logger.warning("Empty webhook payload received")
            return jsonify({"status": "ok"}), 200

        # Handle callback_query (button clicks)
        if "callback_query" in update:
            callback_query = update["callback_query"]
            callback_data = callback_query.get("data")
            user = callback_query.get("from", {})
            user_info = {
                "id": user.get("id"),
                "username": user.get("username"),
                "first_name": user.get("first_name"),
            }

            if not callback_data:
                logger.warning("Callback query missing data")
                return jsonify({"status": "ok"}), 200

            # Handle callback
            messenger_service = get_messenger()
            success, error = messenger_service.handle_callback(callback_data, user_info)

            if success:
                # Answer callback query (show confirmation to user)
                try:
                    messenger_service.bot.answer_callback_query(
                        callback_query["id"],
                        text="✅ Ticket acknowledged successfully!",
                    )

                    # Edit message to remove button (show acknowledged status)
                    message = callback_query.get("message", {})
                    if message:
                        messenger_service.bot.edit_message_reply_markup(
                            chat_id=message["chat"]["id"],
                            message_id=message["message_id"],
                            reply_markup=None,
                        )

                    # Send confirmation message to channel (with rate limiting)
                    channel_id = message.get("chat", {}).get("id")
                    if channel_id:
                        # Rate limit: only send confirmation once per ticket per 60 seconds
                        # to prevent spam on repeated callbacks
                        ticket_id = callback_data.split(":", 1)[1] if ":" in callback_data else None
                        if ticket_id:
                            rate_limit_key = f"telegram:ack_confirmation:{ticket_id}"
                            if messenger_service.redis_client:
                                # Check if confirmation was sent recently
                                if not messenger_service.redis_client.get(rate_limit_key):
                                    username = user_info.get("username", "Unknown")
                                    confirmation_text = f"✅ Ticket acknowledged by @{username}"
                                    try:
                                        messenger_service.bot.send_message(
                                            chat_id=channel_id, text=confirmation_text
                                        )
                                        # Set rate limit (60 seconds)
                                        messenger_service.redis_client.setex(rate_limit_key, 60, "1")
                                    except Exception as exc:
                                        logger.warning(
                                            "Failed to send confirmation message",
                                            extra={"context": {"error": str(exc)}},
                                        )
                            else:
                                # Redis unavailable, send confirmation anyway (graceful degradation)
                                username = user_info.get("username", "Unknown")
                                confirmation_text = f"✅ Ticket acknowledged by @{username}"
                                try:
                                    messenger_service.bot.send_message(
                                        chat_id=channel_id, text=confirmation_text
                                    )
                                except Exception as exc:
                                    logger.warning(
                                        "Failed to send confirmation message",
                                        extra={"context": {"error": str(exc)}},
                                    )

                except Exception as exc:
                    logger.error(
                        "Error sending callback response",
                        extra={
                            "context": {
                                "callback_id": callback_query.get("id"),
                                "error": str(exc),
                            }
                        },
                    )
            else:
                # Answer with error
                try:
                    error_message = str(error) if error else "Unknown error"
                    messenger_service.bot.answer_callback_query(
                        callback_query["id"],
                        text=f"❌ Error: {error_message}",
                        show_alert=True,
                    )
                except Exception as exc:
                    logger.error(
                        "Error sending error callback response",
                        extra={
                            "context": {
                                "callback_id": callback_query.get("id"),
                                "error": str(exc),
                            }
                        },
                    )

        # Always return 200 to Telegram (even on errors)
        return jsonify({"status": "ok"}), 200

    except Exception as exc:
        logger.exception(
            "Error processing webhook",
            extra={"context": {"error": str(exc)}},
        )
        # Always return 200 to Telegram
        return jsonify({"status": "ok"}), 200


@telegram_bp.route("/set-webhook", methods=["POST"])
@admin_only
def set_webhook():
    """Configure webhook URL (admin only)."""
    messenger_service = get_messenger()
    if not messenger_service.bot:
        return jsonify({"error": "Telegram bot not initialized"}), 500

    if not request.is_json:
        return jsonify({"error": "Invalid JSON payload"}), 400

    data = request.get_json() or {}
    webhook_url = (data.get("webhook_url") or "").strip()

    if not webhook_url:
        return jsonify({"error": "webhook_url is required"}), 400

    # Validate webhook URL is HTTPS
    if not webhook_url.startswith("https://"):
        return (
            jsonify({"error": "Invalid webhook URL (must be HTTPS)"}),
            400,
        )

    try:
        # Set webhook using Telegram API
        messenger_service.bot.set_webhook(
            url=webhook_url, secret_token=config.TELEGRAM_WEBHOOK_SECRET
        )

        logger.info(
            "Webhook set successfully",
            extra={"context": {"webhook_url": webhook_url}},
        )

        return (
            jsonify({"message": "Webhook set successfully", "url": webhook_url}),
            200,
        )

    except Exception as exc:
        logger.error(
            "Failed to set webhook",
            extra={"context": {"webhook_url": webhook_url, "error": str(exc)}},
        )
        return jsonify({"error": "Failed to set webhook"}), 500


@telegram_bp.route("/delete-webhook", methods=["POST"])
@admin_only
def delete_webhook():
    """Remove webhook configuration (admin only)."""
    messenger_service = get_messenger()
    if not messenger_service.bot:
        return jsonify({"error": "Telegram bot not initialized"}), 500

    try:
        messenger_service.bot.delete_webhook()

        logger.info("Webhook deleted successfully")

        return jsonify({"message": "Webhook deleted successfully"}), 200

    except Exception as exc:
        logger.error(
            "Failed to delete webhook",
            extra={"context": {"error": str(exc)}},
        )
        return jsonify({"error": "Failed to delete webhook"}), 500


@telegram_bp.route("/webhook-info", methods=["GET"])
@admin_only
def webhook_info():
    """Get current webhook configuration (admin only)."""
    messenger_service = get_messenger()
    if not messenger_service.bot:
        return jsonify({"error": "Telegram bot not initialized"}), 500

    try:
        info = messenger_service.bot.get_webhook_info()

        response_data = {
            "url": info.url or "",
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": (
                datetime.utcfromtimestamp(info.last_error_date).isoformat() if info.last_error_date else None
            ),
            "last_error_message": info.last_error_message,
        }

        return jsonify(response_data), 200

    except Exception as exc:
        logger.error(
            "Failed to get webhook info",
            extra={"context": {"error": str(exc)}},
        )
        return jsonify({"error": "Failed to get webhook info"}), 500

