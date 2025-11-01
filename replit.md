# Discord Trial Key Bot

## Overview
A Discord bot that manages trial key distribution with built-in eligibility checks. Users can claim trial keys through an interactive button, and administrators can manage the key pool through slash commands.

## Project Type
Backend Discord bot application (no frontend)

## Setup Date
November 01, 2025

## Core Features
- **Trial Key Distribution**: Users can claim trial keys through a persistent "Try" button
- **Age Requirement**: Requires Discord accounts to be at least 7 days old
- **One Key Per User**: Prevents multiple claims from the same user
- **Admin Commands**: Add keys, post trial buttons, and manage the key pool
- **Persistent Storage**: Keys and claims stored in JSON files

## Project Architecture

### Main Files
- `bot.py`: Main Discord bot implementation
- `main.py`: Legacy entry point (not used)
- `pyproject.toml`: Python project dependencies

### Dependencies
- discord.py >= 2.6.4: Discord API library

### Data Storage
- `keys.json`: Pool of available trial keys
- `claims.json`: Record of user claims (user_id -> key)

### Environment Variables
- `DISCORD_TOKEN`: Discord bot token (required, stored in Replit Secrets)
- `DATA_DIR`: Directory for data files (optional, defaults to ".")

## Bot Commands

### Slash Commands
- `/posttrial`: Post the "Try" button message (admin only)
- `/addkeys`: Add trial keys to the pool (admin only)
- `/mykey`: Show your claimed trial key

### Interactive Elements
- **Try Button**: Persistent button that allows eligible users to claim keys

## Configuration
- Account age requirement: 7 days
- Permissions: Administrator role required for management commands

## Setup Instructions

### Discord Developer Portal Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or select an existing one
3. Go to the "Bot" section and copy the token
4. Add the token to Replit Secrets as `DISCORD_TOKEN`
5. **(Optional)** If you want to use "guild" mode (server join age checks):
   - Enable "SERVER MEMBERS INTENT" in the Bot settings
   - Uncomment `intents.members = True` in bot.py (line 234)

### Bot Permissions
When inviting the bot to your server, make sure to enable:
- `applications.commands` (for slash commands)
- `bot` scope
- Send Messages, Read Message History, etc.

## Configuration Options

### Age Check Modes
- **account** (default): Checks Discord account creation date
- **guild**: Checks when user joined the server (requires SERVER MEMBERS INTENT)

### Admin Commands
Use `/setmode` to switch between modes and `/setdays` to change the minimum age requirement.

## Recent Changes
- Initial import and setup (2025-11-01)
- Added .gitignore for Python project
- Configured workflow to run bot
- Set up DISCORD_TOKEN secret management
- Fixed Transform parameter issues for discord.py compatibility
- Disabled members intent by default (only needed for guild mode)
- Bot successfully connected and running
- Improved user display: Now shows usernames (e.g., "Azec#1234 (1424750637564039179)") instead of just IDs
- Updated `/listclaims` to fetch and display Discord usernames
- Updated `/exportclaims` to include username column in CSV export
- **Added automatic schema migration**: Old `claims.json` format is automatically converted to new format on startup
- **Fixed claim handling**: Robust error handling for both old and new claim data formats
- **Improved date formatting**: Timestamps now display as "1 November 2025 at 22:22" instead of messy ISO format
- **Cleaner message layout**: Better structured output in `/listclaims` and `/mykey` commands
