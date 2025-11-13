# Quick Telegram Setup - What to Do in Telegram App

## Yes, you need to do these steps in your Telegram app:

### Step 1: Create a Bot (5 minutes)

1. **Open Telegram app** on your phone or desktop
2. **Search for `@BotFather`** in Telegram
3. **Start a chat** with BotFather
4. **Send this command**: `/newbot`
5. **Follow the prompts**:
   - BotFather will ask: "Alright, a new bot. How are we going to call it? Please choose a name for your bot."
   - **Reply with a name** (e.g., "VigilantEye Alerts")
   - BotFather will ask: "Good. Now let's choose a username for your bot. It must end in `bot`. Like this, for example: TetrisBot or tetris_bot."
   - **Reply with a username** ending in `bot` (e.g., "vigilanteye_alerts_bot")
6. **BotFather will give you a token** that looks like:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
7. **Copy this token** - you'll need it for your server configuration

### Step 2: Choose Your Notification Method

You have **two options**:

#### Option A: Use a Telegram Channel (Recommended for Teams)

1. **Create a new channel** in Telegram:
   - Click the menu (☰) in Telegram
   - Select "New Channel"
   - Give it a name (e.g., "Security Alerts")
   - Make it Public or Private (your choice)

2. **Add your bot as administrator**:
   - Go to channel settings (click channel name → Edit)
   - Click "Administrators"
   - Click "Add Administrator"
   - Search for your bot (the username you created, e.g., `@vigilanteye_alerts_bot`)
   - Select it and give it permission to "Post Messages"
   - Click "Done"

3. **Send a test message** to the channel (any message)

4. **Get the Channel ID**:
   - Open a web browser
   - Go to: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Replace `<YOUR_BOT_TOKEN>` with the token from Step 1
   - Look for a number that starts with `-100` (e.g., `-1001234567890`)
   - **That's your Channel ID** - copy it!

#### Option B: Use a Private Chat (Easier for Personal Use)

1. **Start a chat with your bot**:
   - Search for your bot in Telegram (using the username you created)
   - Click "Start" or send any message to the bot

2. **Get your Chat ID**:
   - Open a web browser
   - Go to: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Replace `<YOUR_BOT_TOKEN>` with the token from Step 1
   - Look for a positive number (e.g., `123456789`)
   - **That's your Chat ID** - copy it!

### Step 3: Configure Your Server

1. **Set the bot token** in your server:
   - Edit `config.py` and update:
     ```python
     TELEGRAM_BOT_TOKEN = "your_bot_token_here"
     ```
   - OR set environment variable:
     ```bash
     export TELEGRAM_BOT_TOKEN="your_bot_token_here"
     ```

2. **Restart your server** if needed

### Step 4: Configure in Dashboard

1. **Go to your VigilantEye dashboard**
2. **Click "Configure"** in the Smart Alerts section
3. **Enable "Telegram Notifications"**
4. **Enter your Channel/Chat ID** (the number you got from Step 2)
5. **Click "Save Configuration"**

### Step 5: Test It!

1. **Start your camera** on the dashboard
2. **Enable motion or object detection**
3. **Move in front of the camera** or place objects
4. **Check your Telegram channel/chat** - you should receive an alert! 🎉

## Summary Checklist

- [ ] Created bot with @BotFather
- [ ] Got bot token
- [ ] Created channel OR started chat with bot
- [ ] Added bot as admin (if using channel)
- [ ] Got Channel/Chat ID from getUpdates
- [ ] Set bot token in config.py or environment
- [ ] Entered Channel/Chat ID in dashboard
- [ ] Tested by triggering an alert

## Troubleshooting

**Bot not sending messages?**
- Make sure bot is added as administrator (for channels)
- Check that bot token is correct in config.py
- Verify Channel/Chat ID is correct (negative for channels, positive for chats)

**Can't find Channel ID?**
- Make sure you sent a message to the channel first
- Check that bot is an administrator
- Try the getUpdates URL again

**Need help?**
- Click "How to get Channel ID?" button in the dashboard configuration modal
- Check the full guide: `TELEGRAM_SETUP_GUIDE.md`

