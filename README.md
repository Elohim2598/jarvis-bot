# Jarvis — AI-Powered Discord Bot

An AI-powered Discord bot built with Python, Discord.py and Groq (LLaMA 3.3). Features AI chat, moderation, weather, crypto, Wikipedia, currency conversion, book lookup, reminders and more.

---

## Tech Stack

- **Python 3.12**
- **Discord.py** — Discord API wrapper
- **Groq API** — LLaMA 3.3 70b for AI responses
- **aiohttp** — Async HTTP requests

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/jarvis-bot.git
cd jarvis-bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
```
Fill in your API keys in the `.env` file (see API Keys section below).

### 4. Run the bot
```bash
python bot.py
```

---

## API Keys

| Key | Required | Where to get it |
|---|---|---|
| `DISCORD_TOKEN` | Yes | [Discord Developer Portal](https://discord.com/developers/applications) → Bot → Reset Token |
| `GROQ_API_KEY` | Yes | [console.groq.com](https://console.groq.com) |
| `OPENWEATHER_API_KEY` | For `!weather` | [openweathermap.org](https://openweathermap.org/api) — free tier |
| `COINGGECKO` | For `!crypto` | No key needed |
| `EXCHANGERATE` | For `!convert` | No key needed |
| `WIKIPEDIA` | For `!wiki` | No key needed |
| `OPEN LIBRARY` | For `!book` | No key needed |

---

## Commands

### AI Chat
| Command | Description |
|---|---|
| `!ask <question>` | Ask Jarvis anything |
| `@Jarvis <message>` | Mention Jarvis to chat |
| `!reset` | Clear your conversation history |
| `!ping` | Check bot latency |

### Utility
| Command | Description |
|---|---|
| `!weather <city>` | Current weather for any city |
| `!remind <minutes> <message>` | Get a DM reminder after X minutes |
| `!translate <language> <text>` | Translate text to any language |
| `!summarize <text>` | Summarize a long block of text |

### APIs
| Command | Description |
|---|---|
| `!crypto <coin>` | Live price, 24h change and market cap |
| `!convert <amount> <from> <to>` | Currency conversion e.g. `!convert 100 USD BOB` |
| `!wiki <topic>` | Wikipedia summary with thumbnail |
| `!book <title>` | Book info from Open Library |
| `!news <topic>` | Latest headlines on any topic |

### Server Info
| Command | Description |
|---|---|
| `!userinfo @user` | Account age, roles, join date |
| `!serverinfo` | Server stats, boost level, member count |
| `!avatar @user` | Display a user's avatar |
| `!roles` | List all server roles |

### Fun
| Command | Description |
|---|---|
| `!joke` | Jarvis tells a dry British joke |
| `!roast @user` | Jarvis roasts someone with British wit |
| `!8ball <question>` | Ask the magic 8-ball |
| `!story <topic>` | Jarvis generates a short story |

### Moderation
| Command | Description |
|---|---|
| `!kick @user [reason]` | Kick a member |
| `!ban @user [reason]` | Ban a member |
| `!unban <username>` | Unban a member |
| `!mute @user [minutes] [reason]` | Timeout a member |
| `!unmute @user` | Remove timeout |
| `!clear <amount>` | Delete up to 100 messages |
| `!prune <amount>` | Delete large number of messages (loops in batches) |

---

*Built by [Sebastian Elohim Perrone](https://www.linkedin.com/in/sebastianperrone/)*
