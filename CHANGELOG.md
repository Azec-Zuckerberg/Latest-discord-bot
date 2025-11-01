# Changelog

All notable changes to the Discord Trial Key Bot.

## [Unreleased] - 2025-11-01

### Added
- Initial project setup in Replit environment
- Python dependencies configuration (discord.py >= 2.6.4)
- Discord bot workflow configuration
- Proper .gitignore for Python project
- Project documentation (replit.md)
- Secret management for DISCORD_TOKEN via Replit Secrets

### Changed
- Fixed `app_commands.Transform()` compatibility issues
  - Replaced incorrect Transform usage with simple boolean defaults in `/listclaims` command
  - Replaced incorrect Transform usage in `/listkeys` command  
  - Fixed parameter type for `return_to_pool` in `/revoke` command
- Disabled Members Intent by default
  - Changed from `intents.members = True` to commented out
  - Bot now works without privileged intents enabled in Discord Developer Portal
  - Users can optionally enable it for "guild" mode (server join age checks)
- Improved user display in claim listings
  - `/listclaims` now fetches and displays Discord usernames instead of just user IDs
  - Format: `Username#1234 (1424750637564039179)` or `Username (1424750637564039179)` for new format
  - Falls back to user ID if fetch fails
- Enhanced CSV export in `/exportclaims`
  - Added "username" column to CSV output
  - CSV now includes: user_id, username, key
  - Automatically fetches usernames from Discord API
- Improved date/time display formatting
  - Timestamps now display as "1 November 2025 at 22:22" instead of ISO format
  - Applied to `/listclaims`, `/mykey`, and Try button messages
  - Much cleaner and easier to read

### Fixed
- Bot startup errors due to privileged intents requirement
- Type errors in command parameter definitions
- User ID display (now shows readable usernames)
- **Schema migration for claims.json**: Added automatic migration from old format (`"user_id": "KEY"`) to new format (`"user_id": {"key": "...", "claimed_at": "..."}`)
- **Robust claim handling**: The "already claimed" message now handles both old and new data formats gracefully without errors

## Bot Features

### User Commands
- `/mykey` - Check your claimed trial key
- **Try Button** - Persistent button to claim trial keys (requires account age check)

### Admin Commands
- `/posttrial` - Post the Try button message
- `/addkeys` - Add trial keys to the pool (comma or newline separated)
- `/listkeys` - List available keys or attach full list as file
- `/listclaims` - List claimed keys with usernames
- `/revoke` - Revoke a user's claim, optionally return key to pool
- `/assign` - Force assign a key to a user
- `/removekey` - Remove a key from pool or claims
- `/exportkeys` - Download keys pool as text file
- `/exportclaims` - Download claims as CSV with usernames
- `/setdays` - Set minimum required days to qualify (0-3650)
- `/setmode` - Set check mode: 'account' (account age) or 'guild' (server join age)

### Configuration
- Default minimum age: 7 days
- Default mode: account age check
- Account age check works without privileged intents
- Guild/server join age check requires SERVER MEMBERS INTENT enabled

### Data Storage
- `keys.json` - Pool of available keys and configuration
- `claims.json` - Record of user claims (user_id -> key)

## Status
✅ Bot is running successfully
✅ Connected to Discord as Azec Trials#5483
✅ All commands functional
✅ User display improvements implemented
