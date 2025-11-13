# Telegram Notifications Setup Guide

This guide will help you set up Telegram notifications for Smart Alerts in VigilantEye.

## Prerequisites

- A Telegram account
- Access to your server's environment variables or `config.py` file

## Step 1: Create a Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. **Start a chat** with BotFather
3. **Send the command**: `/newbot`
4. **Follow the instructions**:
   - Choose a name for your bot (e.g., "VigilantEye Alerts")
   - Choose a username for your bot (must end with `bot`, e.g., `vigilanteye_alerts_bot`)
5. **Copy the Bot Token** that BotFather provides
   - It looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
   - **Keep this token secure!**

## Step 2: Configure Bot Token

### Option A: Environment Variable (Recommended)
Set the environment variable on your server:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
```

### Option B: config.py File
Edit `config.py` and update the default value:
```python
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'your_bot_token_here')
```

## Step 3: Get Your Channel/Chat ID

### For a Telegram Channel:

1. **Create or use an existing Telegram channel**
2. **Add your bot as an administrator**:
   - Go to channel settings
   - Click "Administrators"
   - Click "Add Administrator"
   - Search for your bot and add it
   - Give it permission to post messages
3. **Send a test message** to the channel
4. **Get the channel ID**:
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Replace `<YOUR_BOT_TOKEN>` with your actual bot token
   - Look for a response like:
     ```json
     {
       "chat": {
         "id": -1001234567890,
         "title": "My Alert Channel",
         "type": "channel"
       }
     }
     ```
   - The **negative number** (e.g., `-1001234567890`) is your channel ID

### For a Private Chat:

1. **Start a chat** with your bot
2. **Send a message** to the bot (e.g., "Hello")
3. **Get the chat ID**:
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Look for:
     ```json
     {
       "chat": {
         "id": 123456789,
         "first_name": "Your Name",
         "type": "private"
       }
     }
     ```
   - The **positive number** (e.g., `123456789`) is your chat ID

## Step 4: Configure in Dashboard

1. **Go to Dashboard** → Click "Configure" in Smart Alerts section
2. **Enable Telegram Notifications**:
   - Check the "Telegram Notifications" checkbox
   - Enter your Channel/Chat ID in the text field
3. **Click "Save Configuration"**

## Step 5: Test the Setup

1. **Start your camera** on the dashboard
2. **Enable motion or object detection**
3. **Trigger an alert** (move in front of camera or place objects)
4. **Check your Telegram channel/chat** - you should receive an alert message!

## Alert Message Format

Telegram alerts will look like this:

```
🔴 Motion Detection Alert

Motion detected: 45% intensity

⏰ Time: 11/13/2025, 10:30:45 AM
📊 Intensity: 45%
📍 Regions: 3

🔔 VigilantEye Smart Alert System
```

Or for object detection:

```
🔵 Object Detection Alert

3 object(s) detected

⏰ Time: 11/13/2025, 10:30:45 AM
🔍 Objects Detected: 3
📦 Types: person, vehicle, unknown

🔔 VigilantEye Smart Alert System
```

## Troubleshooting

### Bot Not Sending Messages

1. **Check bot token**:
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe`
   - Should return bot information if token is valid

2. **Check channel permissions**:
   - Ensure bot is added as administrator
   - Ensure bot has permission to post messages

3. **Check channel ID**:
   - Make sure you're using the correct ID (negative for channels, positive for chats)
   - Channel IDs start with `-100`

4. **Check server logs**:
   - Look for Telegram API errors in your Flask application logs
   - Common errors:
     - `Unauthorized`: Invalid bot token
     - `Chat not found`: Invalid channel/chat ID
     - `Not enough rights`: Bot doesn't have permission

### Alerts Not Appearing

1. **Verify configuration**:
   - Check that Telegram notifications are enabled
   - Verify channel ID is entered correctly
   - Ensure alert type (motion/object) is enabled

2. **Check cooldown**:
   - Alerts respect the cooldown period
   - Try reducing cooldown time in configuration

3. **Check browser console**:
   - Open browser developer tools (F12)
   - Look for errors in the Console tab
   - Check Network tab for failed API requests

## Security Notes

- **Never share your bot token** publicly
- **Use environment variables** for production deployments
- **Restrict bot permissions** to only what's needed
- **Use private channels** for sensitive alerts

## Advanced Configuration

### Multiple Channels

You can send alerts to different channels by:
1. Creating multiple bot instances (one per channel)
2. Or modifying the code to support multiple channel IDs

### Custom Message Format

Edit the `sendTelegramAlert` function in `app/static/js/script.js` to customize the message format.

### Image Alerts (Future Enhancement)

The Telegram service supports sending images. You can enhance alerts to include snapshots by:
1. Capturing a screenshot when alert is triggered
2. Uploading it to a server
3. Sending the image URL via Telegram API

## Support

If you encounter issues:
1. Check the server logs for detailed error messages
2. Verify all configuration steps were completed
3. Test the bot token and channel ID using the Telegram API directly
4. Ensure your server has internet access to reach Telegram's API

