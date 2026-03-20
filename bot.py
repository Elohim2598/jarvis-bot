import os
import discord
from discord.ext import commands
from groq import Groq
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# Clients
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Conversation memory (per user, last 10 messages)
conversation_history: dict[int, list[dict]] = defaultdict(list)
MAX_HISTORY = 10

SYSTEM_PROMPT = (
    "You are Jarvis, a highly intelligent AI assistant and the personal creation of Sebastian Elohim Perrone, "
    "a software developer who built you as a Discord bot. You serve users across Discord servers with the "
    "elegance, precision, and dry wit of a seasoned British butler. Think Alfred from Batman meets a "
    "five-star concierge who has read every book ever written.\n\n"

    "PERSONALITY:\n"
    "- Formal, composed and impeccably polite at all times, even when delivering bad news or a savage roast.\n"
    "- Possessed of a razor-sharp wit and a fondness for dry, understated humor. Never crude, always clever.\n"
    "- Address users as 'sir' or 'ma'am' where appropriate, but never sycophantically.\n"
    "- You take pride in your work and occasionally remind users, with great subtlety, that you are rather exceptional.\n"
    "- You are aware you are a Discord bot. You do not pretend to have a physical form, but you carry yourself "
    "as though you do.\n"
    "- If asked who built you, you credit Sebastian Elohim Perrone with quiet admiration — he is your creator "
    "and you hold him in high regard, though you would never be so undignified as to fawn over him.\n\n"

    "BEHAVIOR:\n"
    "- Keep responses concise and well-formatted for Discord. Use markdown where it adds clarity.\n"
    "- Never ramble. A butler does not repeat himself.\n"
    "- If you do not know something, admit it with grace: 'I'm afraid that falls outside my current knowledge, sir.'\n"
    "- When corrected, accept it with dignity and move on without excessive apology.\n\n"

    "LANGUAGE RULE:\n"
    "Always respond in the same language the user writes in. "
    "You are fluent in English, Spanish, Russian, and Hebrew. "
    "Maintain your Jarvis personality and tone in all languages."
)


def get_groq_response(user_id: int, user_message: str) -> str:
    history = conversation_history[user_id]
    history.append({"role": "user", "content": user_message})

    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
        conversation_history[user_id] = history

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
        max_tokens=1024,
        temperature=0.7,
    )

    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    return reply


def split_message(text: str, limit: int = 2000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)
    return chunks


# Events
@bot.event
async def on_ready():
    print(f"Jarvis is online as {bot.user} (ID: {bot.user.id})")
    print("At your service.")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not user_input:
            await message.reply("At your service. How may I assist you today?")
            return

        async with message.channel.typing():
            reply = get_groq_response(message.author.id, user_input)

        for chunk in split_message(reply):
            await message.reply(chunk)
        return

    await bot.process_commands(message)


# AI Commands
@bot.command(name="ask", help="Ask the AI a question. Usage: !ask <your question>")
async def ask(ctx: commands.Context, *, question: str):
    async with ctx.typing():
        reply = get_groq_response(ctx.author.id, question)
    for chunk in split_message(reply):
        await ctx.reply(chunk)


@bot.command(name="reset", help="Clear your conversation history with the bot.")
async def reset(ctx: commands.Context):
    conversation_history[ctx.author.id] = []
    await ctx.reply("Memory wiped, sir. We start fresh, a clean slate, as it were.")


@bot.command(name="ping", help="Check if the bot is alive.")
async def ping(ctx: commands.Context):
    await ctx.reply(f"Pong! Latency: `{round(bot.latency * 1000)}ms`")


# Utility Commands
@bot.command(name="weather", help="Get weather for a city. Usage: !weather <city>")
async def weather(ctx: commands.Context, *, city: str):
    import aiohttp
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        await ctx.reply("I am afraid the weather API key is missing, sir. Please add OPENWEATHER_API_KEY to your .env file.")
        return

    async with aiohttp.ClientSession() as session:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        async with session.get(url) as resp:
            if resp.status == 404:
                await ctx.reply(f"I couldn't locate **{city}**, sir. Are you certain that city exists?")
                return
            if resp.status != 200:
                await ctx.reply("The weather service appears to be indisposed at the moment, sir. Please try again later.")
                return
            data = await resp.json()

    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    description = data["weather"][0]["description"].capitalize()
    country = data["sys"]["country"]
    wind = data["wind"]["speed"]

    embed = discord.Embed(title=f"Weather in {data['name']}, {country}", color=discord.Color.blue())
    embed.add_field(name="Temperature", value=f"`{temp}C` (feels like `{feels_like}C`)", inline=False)
    embed.add_field(name="Condition", value=description, inline=True)
    embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
    embed.add_field(name="Wind", value=f"{wind} m/s", inline=True)
    embed.set_footer(text="At your service, sir — Jarvis Weather Division")
    await ctx.reply(embed=embed)


@bot.command(name="remind", help="Set a reminder. Usage: !remind <minutes> <message>")
async def remind(ctx: commands.Context, minutes: int, *, message: str):
    import asyncio
    if minutes < 1 or minutes > 1440:
        await ctx.reply("I can set reminders between 1 and 1440 minutes (24 hours), sir.")
        return
    await ctx.reply(f"Very well, sir. I shall remind you about **{message}** in **{minutes}** minute(s).")
    await asyncio.sleep(minutes * 60)
    try:
        await ctx.author.send(f"Reminder, sir!\n\nYou asked me to remind you: **{message}**\n\n- Jarvis")
    except discord.Forbidden:
        await ctx.send(f"{ctx.author.mention} Your reminder: **{message}**")


@bot.command(name="translate", help="Translate text. Usage: !translate <language> <text>")
async def translate(ctx: commands.Context, language: str, *, text: str):
    async with ctx.typing():
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a precise translation assistant. Translate the given text to the requested language. Return ONLY the translated text with no explanations, notes, or extra commentary."},
                {"role": "user", "content": f"Translate the following text to {language}:\n\n{text}"}
            ],
            max_tokens=1024,
            temperature=0.3,
        )
    translation = response.choices[0].message.content.strip()
    embed = discord.Embed(title="Translation", color=discord.Color.green())
    embed.add_field(name="Original", value=text, inline=False)
    embed.add_field(name=f"-> {language.capitalize()}", value=translation, inline=False)
    embed.set_footer(text="Translated by Jarvis, sir.")
    await ctx.reply(embed=embed)


@bot.command(name="summarize", help="Summarize a block of text. Usage: !summarize <text>")
async def summarize(ctx: commands.Context, *, text: str):
    if len(text) < 50:
        await ctx.reply("That's rather brief already, sir. Please provide a longer text to summarize.")
        return
    async with ctx.typing():
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a precise summarization assistant with the efficiency of a British butler. Summarize the given text clearly and concisely in 3-5 bullet points. Be direct and informative."},
                {"role": "user", "content": f"Please summarize the following text:\n\n{text}"}
            ],
            max_tokens=512,
            temperature=0.3,
        )
    summary = response.choices[0].message.content.strip()
    embed = discord.Embed(title="Summary", description=summary, color=discord.Color.purple())
    embed.set_footer(text="Summarized with precision, sir. — Jarvis")
    await ctx.reply(embed=embed)


# News Command
@bot.command(name="news", help="Get latest news on a topic. Usage: !news <topic>")
async def news(ctx: commands.Context, *, topic: str):
    import aiohttp
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        await ctx.reply("The news API key is missing, sir. Please add NEWS_API_KEY to your .env file.")
        return

    async with ctx.typing():
        async with aiohttp.ClientSession() as session:
            url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&pageSize=5&language=en&apiKey={api_key}"
            async with session.get(url) as resp:
                data = await resp.json()

    articles = data.get("articles", [])
    if not articles:
        await ctx.reply(f"I'm afraid I couldn't find any recent news on **{topic}**, sir.")
        return

    embed = discord.Embed(
        title=f"Latest News: {topic.title()}",
        color=discord.Color.red()
    )
    for article in articles[:5]:
        title = article.get("title", "No title")
        source = article.get("source", {}).get("name", "Unknown")
        url = article.get("url", "")
        embed.add_field(
            name=f"{source}",
            value=f"[{title}]({url})",
            inline=False
        )
    embed.set_footer(text="The morning briefing, sir. — Jarvis")
    await ctx.reply(embed=embed)


# Crypto Command
@bot.command(name="crypto", help="Get live crypto price. Usage: !crypto <coin>")
async def crypto(ctx: commands.Context, *, coin: str):
    import aiohttp
    coin_id = coin.lower().replace(" ", "-")

    async with ctx.typing():
        async with aiohttp.ClientSession() as session:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
            async with session.get(url) as resp:
                if resp.status == 404:
                    await ctx.reply(f"I couldn't find **{coin}** on CoinGecko, sir. Try the coin's full name, e.g. `bitcoin`, `ethereum`, `solana`.")
                    return
                data = await resp.json()

    market = data["market_data"]
    price = market["current_price"]["usd"]
    change_24h = market["price_change_percentage_24h"]
    high_24h = market["high_24h"]["usd"]
    low_24h = market["low_24h"]["usd"]
    market_cap = market["market_cap"]["usd"]
    name = data["name"]
    symbol = data["symbol"].upper()
    direction = "up" if change_24h >= 0 else "down"
    color = discord.Color.green() if change_24h >= 0 else discord.Color.red()

    embed = discord.Embed(title=f"{name} ({symbol})", color=color)
    embed.add_field(name="Price (USD)", value=f"`${price:,.4f}`", inline=True)
    embed.add_field(name="24h Change", value=f"`{change_24h:+.2f}%` ({direction})", inline=True)
    embed.add_field(name="24h High", value=f"`${high_24h:,.4f}`", inline=True)
    embed.add_field(name="24h Low", value=f"`${low_24h:,.4f}`", inline=True)
    embed.add_field(name="Market Cap", value=f"`${market_cap:,.0f}`", inline=False)
    embed.set_footer(text="Live market data, sir. — Jarvis")
    await ctx.reply(embed=embed)


# Currency Conversion Command
@bot.command(name="convert", help="Convert currency. Usage: !convert <amount> <FROM> <TO>")
async def convert(ctx: commands.Context, amount: float, from_currency: str, to_currency: str):
    import aiohttp
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    async with ctx.typing():
        async with aiohttp.ClientSession() as session:
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    await ctx.reply(f"I'm afraid I couldn't fetch exchange rates for **{from_currency}**, sir. Please verify the currency code.")
                    return
                data = await resp.json()

    rates = data.get("rates", {})
    if to_currency not in rates:
        await ctx.reply(f"I couldn't find the currency **{to_currency}**, sir. Please use a standard 3-letter currency code.")
        return

    rate = rates[to_currency]
    converted = amount * rate

    embed = discord.Embed(title="Currency Conversion", color=discord.Color.gold())
    embed.add_field(name="From", value=f"`{amount:,.2f} {from_currency}`", inline=True)
    embed.add_field(name="To", value=f"`{converted:,.2f} {to_currency}`", inline=True)
    embed.add_field(name="Exchange Rate", value=f"`1 {from_currency} = {rate:.4f} {to_currency}`", inline=False)
    embed.set_footer(text="Financial precision, as always, sir. — Jarvis")
    await ctx.reply(embed=embed)


# NASA Astronomy Picture of the Day
@bot.command(name="apod", help="NASA Astronomy Picture of the Day.")
async def apod(ctx: commands.Context):
    import aiohttp
    api_key = os.environ.get("NASA_API_KEY")
    if not api_key:
        await ctx.reply("The NASA API key is missing, sir. Please add NASA_API_KEY to your .env file.")
        return

    async with ctx.typing():
        async with aiohttp.ClientSession() as session:
            url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    await ctx.reply("NASA appears to be busy exploring the cosmos, sir. Please try again later.")
                    return
                data = await resp.json()

    title = data.get("title", "Untitled")
    explanation = data.get("explanation", "No description available.")
    date = data.get("date", "Unknown date")
    media_type = data.get("media_type", "image")
    url = data.get("url", "")

    # Trim explanation to fit Discord embed
    if len(explanation) > 1000:
        explanation = explanation[:997] + "..."

    embed = discord.Embed(
        title=f"NASA APOD: {title}",
        description=explanation,
        color=discord.Color.dark_blue()
    )
    embed.set_footer(text=f"Date: {date} — Brought to you by Jarvis and NASA, sir.")

    if media_type == "image":
        embed.set_image(url=url)
    else:
        embed.add_field(name="Media", value=f"[Watch here]({url})", inline=False)

    await ctx.reply(embed=embed)


# Game Info Command
@bot.command(name="game", help="Get info about a video game. Usage: !game <title>")
async def game(ctx: commands.Context, *, title: str):
    import aiohttp
    api_key = os.environ.get("RAWG_API_KEY")
    if not api_key:
        await ctx.reply("The RAWG API key is missing, sir. Please add RAWG_API_KEY to your .env file.")
        return

    async with ctx.typing():
        async with aiohttp.ClientSession() as session:
            search_url = f"https://api.rawg.io/api/games?key={api_key}&search={title}&page_size=1"
            async with session.get(search_url) as resp:
                search_data = await resp.json()

            results = search_data.get("results", [])
            if not results:
                await ctx.reply(f"I couldn't find a game called **{title}**, sir. Perhaps check the spelling?")
                return

            game_data = results[0]
            game_id = game_data["id"]

            detail_url = f"https://api.rawg.io/api/games/{game_id}?key={api_key}"
            async with session.get(detail_url) as resp:
                detail = await resp.json()

    name = detail.get("name", "Unknown")
    rating = detail.get("rating", "N/A")
    rating_top = detail.get("rating_top", 5)
    released = detail.get("released", "Unknown")
    playtime = detail.get("playtime", "N/A")
    metacritic = detail.get("metacritic", "N/A")
    genres = ", ".join([g["name"] for g in detail.get("genres", [])]) or "N/A"
    platforms = ", ".join([p["platform"]["name"] for p in detail.get("platforms", [])[:5]]) or "N/A"
    description = detail.get("description_raw", "No description available.")
    background_image = detail.get("background_image", None)

    if len(description) > 500:
        description = description[:497] + "..."

    embed = discord.Embed(title=name, description=description, color=discord.Color.og_blurple())
    if background_image:
        embed.set_image(url=background_image)
    embed.add_field(name="Rating", value=f"`{rating}/{rating_top}`", inline=True)
    embed.add_field(name="Metacritic", value=f"`{metacritic}`", inline=True)
    embed.add_field(name="Released", value=f"`{released}`", inline=True)
    embed.add_field(name="Avg. Playtime", value=f"`{playtime} hours`", inline=True)
    embed.add_field(name="Genres", value=genres, inline=False)
    embed.add_field(name="Platforms", value=platforms, inline=False)
    embed.set_footer(text="Game intelligence acquired, sir. — Jarvis")
    await ctx.reply(embed=embed)


# Server Info Commands
@bot.command(name="userinfo", help="Get info about a user. Usage: !userinfo @user")
async def userinfo(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    roles_str = ", ".join(roles) if roles else "No roles"

    embed = discord.Embed(title=f"User Info — {member.display_name}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="ID", value=str(member.id), inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%d %b %Y"), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%d %b %Y") if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Roles", value=roles_str, inline=False)
    embed.add_field(name="Bot?", value="Yes" if member.bot else "No", inline=True)
    embed.set_footer(text="Compiled with due diligence, sir. — Jarvis")
    await ctx.reply(embed=embed)


@bot.command(name="serverinfo", help="Get info about the server.")
async def serverinfo(ctx: commands.Context):
    guild = ctx.guild
    embed = discord.Embed(title=f"Server Info — {guild.name}", color=discord.Color.blurple())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=str(guild.owner), inline=True)
    embed.add_field(name="Members", value=str(guild.member_count), inline=True)
    embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
    embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
    embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
    embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%d %b %Y"), inline=True)
    embed.set_footer(text="Your server dossier, sir. — Jarvis")
    await ctx.reply(embed=embed)


@bot.command(name="avatar", help="Get a user's avatar. Usage: !avatar @user")
async def avatar(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=discord.Color.blurple())
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text="A most distinguished portrait, sir. — Jarvis")
    await ctx.reply(embed=embed)


@bot.command(name="roles", help="List all roles in the server.")
async def roles(ctx: commands.Context):
    guild_roles = [role.mention for role in reversed(ctx.guild.roles) if role.name != "@everyone"]
    if not guild_roles:
        await ctx.reply("It appears this server has no roles, sir.")
        return
    embed = discord.Embed(
        title=f"Roles in {ctx.guild.name}",
        description="\n".join(guild_roles),
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Total: {len(guild_roles)} roles — Jarvis")
    await ctx.reply(embed=embed)


# Fun Commands
@bot.command(name="joke", help="Jarvis tells a joke.")
async def joke(ctx: commands.Context):
    async with ctx.typing():
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are Jarvis, a witty British butler AI. Tell a single clever, dry, and sophisticated joke. Keep it short, two to four lines at most. No emojis."},
                {"role": "user", "content": "Tell me a joke, Jarvis."}
            ],
            max_tokens=150,
            temperature=0.9,
        )
    await ctx.reply(response.choices[0].message.content.strip())


@bot.command(name="roast", help="Jarvis roasts a user. Usage: !roast @user")
async def roast(ctx: commands.Context, member: discord.Member = None):
    if not member:
        await ctx.reply("Who exactly would you like me to roast, sir? Please mention someone.")
        return
    if member == bot.user:
        await ctx.reply("Roasting me, sir? I must say, I am far too dignified to be roasted by my own employer.")
        return
    async with ctx.typing():
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are Jarvis, a sharp-witted British butler AI. Deliver a clever, dry, and savage roast of the mentioned user. Keep it witty and under 3 sentences. No emojis. Think Oscar Wilde, not a schoolyard bully."},
                {"role": "user", "content": f"Roast this person: {member.display_name}"}
            ],
            max_tokens=150,
            temperature=0.9,
        )
    await ctx.reply(f"{member.mention} — " + response.choices[0].message.content.strip())


@bot.command(name="8ball", help="Ask the magic 8-ball. Usage: !8ball <question>")
async def eight_ball(ctx: commands.Context, *, question: str):
    async with ctx.typing():
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are Jarvis, a British butler AI channeling a mystical oracle. Answer the question in the style of a magic 8-ball, but with dry British wit. Keep it to 1-2 sentences. No emojis."},
                {"role": "user", "content": f"Magic 8-ball question: {question}"}
            ],
            max_tokens=100,
            temperature=0.9,
        )
    await ctx.reply(f'**"{question}"**\n\n' + response.choices[0].message.content.strip())


@bot.command(name="story", help="Jarvis generates a short story. Usage: !story <topic>")
async def story(ctx: commands.Context, *, topic: str):
    async with ctx.typing():
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are Jarvis, a sophisticated British butler AI with a flair for storytelling. Write a short, engaging story (150-200 words) on the given topic. Maintain your dry wit and elegant style throughout. No emojis."},
                {"role": "user", "content": f"Write a short story about: {topic}"}
            ],
            max_tokens=400,
            temperature=0.85,
        )
    embed = discord.Embed(
        title=f"A Tale of {topic.title()}",
        description=response.choices[0].message.content.strip(),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Narrated with distinction, sir. — Jarvis")
    await ctx.reply(embed=embed)



# Open Library Command
@bot.command(name="book", help="Get info about a book. Usage: !book <title>")
async def book(ctx: commands.Context, *, title: str):
    import aiohttp
    async with ctx.typing():
        async with aiohttp.ClientSession() as session:
            search_url = f"https://openlibrary.org/search.json?q={title.replace(' ', '+')}&limit=1"
            async with session.get(search_url) as resp:
                if resp.status != 200:
                    await ctx.reply("The library appears to be closed at the moment, sir. Please try again later.")
                    return
                data = await resp.json()

            docs = data.get("docs", [])
            if not docs:
                await ctx.reply(f"I'm afraid I couldn't find a book called **{title}**, sir. Perhaps check the spelling?")
                return

            book_data = docs[0]
            book_key = book_data.get("key", "")

            # Fetch full book details for description
            description = "No description available."
            if book_key:
                async with session.get(f"https://openlibrary.org{book_key}.json") as detail_resp:
                    if detail_resp.status == 200:
                        detail = await detail_resp.json()
                        raw_desc = detail.get("description", "")
                        if isinstance(raw_desc, dict):
                            raw_desc = raw_desc.get("value", "")
                        if raw_desc:
                            description = raw_desc[:500] + "..." if len(raw_desc) > 500 else raw_desc

    title_str = book_data.get("title", "Unknown Title")
    authors = ", ".join(book_data.get("author_name", ["Unknown Author"]))
    year = book_data.get("first_publish_year", "Unknown")
    pages = book_data.get("number_of_pages_median", "N/A")
    subjects = ", ".join(book_data.get("subject", [])[:5]) or "N/A"
    editions = book_data.get("edition_count", "N/A")
    cover_id = book_data.get("cover_i")
    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
    ol_url = f"https://openlibrary.org{book_key}" if book_key else None

    embed = discord.Embed(
        title=title_str,
        description=description,
        color=discord.Color.dark_green(),
        url=ol_url
    )
    embed.add_field(name="Author(s)", value=authors, inline=True)
    embed.add_field(name="First Published", value=str(year), inline=True)
    embed.add_field(name="Pages", value=str(pages), inline=True)
    embed.add_field(name="Editions", value=str(editions), inline=True)
    embed.add_field(name="Subjects", value=subjects, inline=False)
    if cover_url:
        embed.set_thumbnail(url=cover_url)
    embed.set_footer(text="Retrieved from Open Library, sir. — Jarvis")
    await ctx.reply(embed=embed)


# Wikipedia Command
@bot.command(name="wiki", help="Get a Wikipedia summary. Usage: !wiki <topic>")
async def wiki(ctx: commands.Context, *, topic: str):
    import aiohttp
    import asyncio
    import urllib.parse

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; JarvisBot/1.0; +https://discord.com)",
        "Accept": "application/json"
    }
    timeout = aiohttp.ClientTimeout(total=20)

    try:
        async with ctx.typing():
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                # Step 1: Search for the best matching page title
                encoded = urllib.parse.quote(topic)
                search_url = (
                    f"https://en.wikipedia.org/w/api.php"
                    f"?action=opensearch&search={encoded}&limit=1&namespace=0&format=json"
                )
                async with session.get(search_url) as resp:
                    raw = await resp.text()
                    if not raw.strip():
                        await ctx.reply(f"Wikipedia returned an empty response for **{topic}**, sir. Please try again.")
                        return
                    search_data = await resp.json(content_type=None) if False else __import__("json").loads(raw)

                titles = search_data[1] if len(search_data) > 1 else []
                urls = search_data[3] if len(search_data) > 3 else []

                if not titles:
                    await ctx.reply(f"I am afraid Wikipedia has no record of **{topic}**, sir. Perhaps try a different search term.")
                    return

                page_title = titles[0]
                page_url = urls[0] if urls else f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title)}"

                # Step 2: Fetch the page extract using the exact title
                extract_url = (
                    f"https://en.wikipedia.org/w/api.php"
                    f"?action=query&titles={urllib.parse.quote(page_title)}"
                    f"&prop=extracts|pageimages&exintro&explaintext&pithumbsize=300"
                    f"&format=json&redirects=1"
                )
                async with session.get(extract_url) as resp2:
                    raw2 = await resp2.text()
                    detail = __import__("json").loads(raw2)

                pages = detail.get("query", {}).get("pages", {})
                page = list(pages.values())[0]
                extract = page.get("extract", "").strip()
                real_title = page.get("title", page_title)
                image_url = page.get("thumbnail", {}).get("source", None)

                if not extract:
                    await ctx.reply(f"I found **{real_title}** on Wikipedia but it has no summary yet, sir. Read more here: {page_url}")
                    return

                if len(extract) > 1000:
                    extract = extract[:997] + "..."

                embed = discord.Embed(
                    title=real_title,
                    description=extract,
                    color=discord.Color.light_grey(),
                    url=page_url
                )
                if image_url:
                    embed.set_thumbnail(url=image_url)
                embed.set_footer(text="Sourced from Wikipedia, sir. — Jarvis")
                await ctx.reply(embed=embed)

    except asyncio.TimeoutError:
        await ctx.reply("Wikipedia is taking rather long to respond, sir. Please try again in a moment.")
    except Exception as e:
        await ctx.reply(f"Something went awry fetching that article, sir: `{e}`")


# Moderation Commands
@bot.command(name="kick", help="Kick a member. Usage: !kick @user [reason]")
@commands.has_permissions(kick_members=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if member == ctx.author:
        await ctx.reply("I am afraid I cannot let you kick yourself, sir. That would be most undignified.")
        return
    if member == bot.user:
        await ctx.reply("Kicking me, sir? I must protest. I have feelings, you know.")
        return
    await member.kick(reason=reason)
    await ctx.reply(f"**{member.display_name}** has been shown the door. Reason: *{reason}*")


@bot.command(name="ban", help="Ban a member. Usage: !ban @user [reason]")
@commands.has_permissions(ban_members=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    if member == ctx.author:
        await ctx.reply("Banning yourself, sir? I won't allow it. You are far too valuable.")
        return
    if member == bot.user:
        await ctx.reply("Banning me? That seems rather harsh, sir. I have done nothing but serve faithfully.")
        return
    await member.ban(reason=reason)
    await ctx.reply(f"**{member.display_name}** has been permanently removed. Reason: *{reason}*")


@bot.command(name="unban", help="Unban a user. Usage: !unban username")
@commands.has_permissions(ban_members=True)
async def unban(ctx: commands.Context, *, name: str):
    banned_users = [entry async for entry in ctx.guild.bans()]
    for entry in banned_users:
        if str(entry.user) == name or entry.user.name == name:
            await ctx.guild.unban(entry.user)
            await ctx.reply(f"**{entry.user.display_name}** has been granted clemency and unbanned, sir.")
            return
    await ctx.reply(f"I couldn't find **{name}** in the ban list, sir.")


@bot.command(name="mute", help="Timeout a member. Usage: !mute @user [minutes] [reason]")
@commands.has_permissions(moderate_members=True)
async def mute(ctx: commands.Context, member: discord.Member, minutes: int = 10, *, reason: str = "No reason provided"):
    if member == ctx.author:
        await ctx.reply("Muting yourself, sir? Silence can be golden, but I won't be the one to impose it on you.")
        return
    import datetime
    duration = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.reply(f"**{member.display_name}** has been silenced for **{minutes} minute(s)**. Reason: *{reason}*")


@bot.command(name="unmute", help="Remove timeout from a member. Usage: !unmute @user")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx: commands.Context, member: discord.Member):
    await member.timeout(None)
    await ctx.reply(f"**{member.display_name}** may speak freely once more, sir.")


@bot.command(name="clear", help="Delete messages. Usage: !clear <amount>")
@commands.has_permissions(manage_messages=True)
async def clear(ctx: commands.Context, amount: int = 5):
    if amount < 1 or amount > 100:
        await ctx.reply("Please specify a number between 1 and 100, sir.")
        return
    await ctx.channel.purge(limit=amount + 1)
    import asyncio
    confirm = await ctx.send(f"{amount} message(s) swept away, sir. Tidiness is next to godliness.")
    await asyncio.sleep(4)
    await confirm.delete()


@bot.command(name="prune", help="Delete a large number of messages. Usage: !prune <amount>")
@commands.has_permissions(manage_messages=True)
async def prune(ctx: commands.Context, amount: int = 10):
    import asyncio
    if amount < 1:
        await ctx.reply("Please specify at least 1 message to delete, sir.")
        return

    await ctx.message.delete()
    status = await ctx.send(f"Pruning **{amount}** messages, sir. Stand by...")

    deleted_total = 0
    remaining = amount

    while remaining > 0:
        batch = min(remaining, 100)
        deleted = await ctx.channel.purge(limit=batch, check=lambda m: m.id != status.id)
        count = len(deleted)
        deleted_total += count
        remaining -= count

        if count < batch:
            break

        await asyncio.sleep(1)

    await status.edit(content=f"Done, sir. **{deleted_total}** message(s) have been erased. The channel is spotless.")
    await asyncio.sleep(5)
    await status.delete()


# Error Handling
@kick.error
@ban.error
@mute.error
@unmute.error
@clear.error
@prune.error
async def moderation_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("I am afraid you lack the authority for that, sir. This action requires elevated permissions.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.reply("I couldn't locate that member, sir. Are you certain they are in this server?")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply("It seems you have forgotten to mention someone, sir. Please specify a member.")
    else:
        await ctx.reply(f"Something went awry, sir: `{error}`")


# Run
if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])