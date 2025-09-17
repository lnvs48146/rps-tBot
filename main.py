import os
import asyncio
import random
import re
from twitchio.ext import commands

# ===== CONFIG FROM ENV VARIABLES =====
BOT_NICK = os.environ["BOT_NICK"]           # Your bot's Twitch username
CHANNEL = os.environ["CHANNEL"]             # Twitch channel
TOKEN = os.environ["TOKEN"]                 # OAuth token with chat:read and chat:edit scopes
CLIENT_ID = os.environ["CLIENT_ID"]         # Twitch Client ID
CLIENT_SECRET = os.environ["CLIENT_SECRET"] # Twitch Client Secret
BOT_ID = os.environ["BOT_ID"]               # Twitch Bot user ID

CHEAT_MODE = 0                    # 0 = normal, 100 = always rigged
CHEAT_PREVIEW_COUNT = 5           # Number of next bot moves to preview
SEND_DELAY = 0.3                  # Delay between bot sends in seconds
MIN_POINTS = 10000
MAX_POINTS = 500000
# ====================================

class RPSBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            prefix="",
            initial_channels=[CHANNEL],
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            bot_id=BOT_ID
        )
        self.pending_rps = {}  # user -> {'amount':int, 'rigged':bool}
        self.cheat_preview = []  # list of tuples (user, bot_choice)

    async def event_ready(self):
        print(f"{BOT_NICK} is online!")

    async def event_message(self, message):
        if message.author is None or message.author.name.lower() == BOT_NICK.lower():
            return

        author = message.author.name
        content = message.content.lower().strip()
        print(f"[CHAT] {author}: {message.content}")

        # Handle !give points
        match = re.match(r"!give\s+@?" + re.escape(BOT_NICK.lower()) + r"\s+([0-9kKmM]+)", content)
        if match:
            raw_amount = match.group(1)
            amount = self.parse_points(raw_amount)
            print(f"[DEBUG] {author} wants to play with {amount} points")

            if amount < MIN_POINTS or amount > MAX_POINTS:
                msg = (f"The limit for playing is {MIN_POINTS:,} to {MAX_POINTS:,} points, omeBru, {author}! "
                       f"Your {amount:,} points are returned!")
                print(f"[BOT] {msg}")
                await message.channel.send(msg)
                await asyncio.sleep(SEND_DELAY)
                await message.channel.send(f"!givepoints {author} {amount}")
                return

            if author in self.pending_rps:
                msg = f"{author}, you already have a game running! Returning your points!"
                print(f"[BOT] {msg}")
                await message.channel.send(msg)
                await asyncio.sleep(SEND_DELAY)
                await message.channel.send(f"!givepoints {author} {amount}")
                return

            rigged = (CHEAT_MODE == 100)
            self.pending_rps[author] = {'amount': amount, 'rigged': rigged}
            if rigged:
                self.cheat_preview.append((author, self.bot_choice()))

            msg = f"{author}, pick rock, paper, or scissors! Type it in chat."
            print(f"[BOT] {msg}")
            await message.channel.send(msg)
            return

        # Handle RPS choice
        if author in self.pending_rps:
            user_choice = content
            if user_choice not in ["rock", "paper", "scissors"]:
                return

            rigged = self.pending_rps[author]['rigged']
            amount = self.pending_rps[author]['amount']

            if rigged:
                if user_choice == "rock":
                    bot_choice = "paper"
                elif user_choice == "paper":
                    bot_choice = "scissors"
                else:
                    bot_choice = "rock"
            else:
                bot_choice = self.bot_choice()

            if user_choice == bot_choice:
                result_text = f"TIE {author}, we both chose {bot_choice}. Your {amount:,} points are returned!"
                await message.channel.send(result_text)
                await asyncio.sleep(SEND_DELAY)
                await message.channel.send(f"!givepoints {author} {amount}")
            elif self.user_wins(user_choice, bot_choice):
                payout = amount * 3
                result_text = f"🎉 {author} WON! I chose {bot_choice}, you get {payout:,} points!"
                await message.channel.send(result_text)
                await asyncio.sleep(SEND_DELAY)
                await message.channel.send(f"!givepoints {author} {payout}")
            else:
                result_text = f"LOSER I chose {bot_choice}, {author}! You lost your {amount:,} points."
                await message.channel.send(result_text)

            self.pending_rps.pop(author)
            self.cheat_preview = [c for c in self.cheat_preview if c[0] != author]

    def parse_points(self, text):
        text = text.lower().replace(",", "")
        if text.endswith("k"):
            return int(float(text[:-1]) * 1000)
        if text.endswith("m"):
            return int(float(text[:-1]) * 1000000)
        return int(text)

    def bot_choice(self):
        return random.choice(["rock", "paper", "scissors"])

    def user_wins(self, user, bot):
        return (
            (user == "rock" and bot == "scissors") or
            (user == "paper" and bot == "rock") or
            (user == "scissors" and bot == "paper")
        )

    def show_next_games(self):
        return [self.bot_choice() for _ in range(CHEAT_PREVIEW_COUNT)]

if __name__ == "__main__":
    bot = RPSBot()
    bot.run()
