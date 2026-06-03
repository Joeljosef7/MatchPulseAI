from dotenv import load_dotenv
import os
import logging
import sys
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database import init_db, add_user, follow_team, unfollow_team, get_followed_teams
from alerts import get_alerts_handler

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token_here")
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "your_key_here")
FOOTBALL_API_URL = "https://api.football-data.org/v4/"
if BOT_TOKEN == "your_token_here":
    print("❌ WARNING: BOT_TOKEN not set!")
    sys.exit()
if FOOTBALL_API_KEY == "your_key_here":
    print("❌ WARNING: FOOTBALL_API_KEY not set!")
    sys.exit()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome {user.first_name} to MatchPulse AI!\n\n"
        "⚽ Your FIFA World Cup 2026 companion.\n\n"
        "Here's what I can do:\n"
        "📅 /fixtures - Today's matches\n"
        "📊 /standings - Group standings\n"
        "🔴 /score - Live scores\n"
        "⭐ /myscore - Followed Team Live scores\n"
        "🔔 /alerts - Match alerts\n"
        "❓ /help - All commands\n\n"
        "Let's get started! Which team are you supporting? 🏆"
    )

async def fixtures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📅 Fetching today's fixtures...")
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    response = requests.get(
        FOOTBALL_API_URL + "competitions/WC/matches?status=SCHEDULED",
        headers=headers
    )
    if response.status_code == 200:
        data = response.json()
        matches = data["matches"]
        if not matches:
            await update.message.reply_text("No matches scheduled today.")
            return
        message = "📅 *Upcoming World Cup Fixtures:*\n\n"
        for match in matches[:10]:
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            date = match["utcDate"][:10]
            message += f"⚽ {home} vs {away}\n📆 {date}\n\n"
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
      error_code = response.status_code
      if error_code == 401:
        await update.message.reply_text("❌ API authentication failed. Contact support.")
      elif error_code == 429:
        await update.message.reply_text("❌ Too many requests. Please wait a moment.")
      else:
        await update.message.reply_text(f"❌ Could not fetch data. Error: {error_code}") 


async def standings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        choice = context.args[0].lower()
        headers = {"X-Auth-Token": FOOTBALL_API_KEY}
        response = requests.get(
            FOOTBALL_API_URL + "competitions/WC/standings",
            headers=headers
        )
        if response.status_code != 200:
            await update.message.reply_text("❌ Could not fetch standings. Try again later.")
            return
        data = response.json()
        groups = data["standings"]
        if choice == "all":
            await update.message.reply_text("📊 *All World Cup Groups:*", parse_mode="Markdown")
            for group in groups:
                message = f"*{group['group']}*\n\n"
                for team in group["table"]:
                    message += (
                        f"{team['position']}. {team['team']['name']}\n"
                        f"P{team['playedGames']} W{team['won']} D{team['draw']} L{team['lost']} | GD{team['goalDifference']:+d} | Pts {team['points']}\n\n"
                    )
                await update.message.reply_text(message, parse_mode="Markdown")
        elif choice == "myteam":
            await update.message.reply_text("⭐ Set your favorite team first using /alerts")
        else:
            found = False
            for group in groups:
                if group["group"].upper().endswith(choice.upper()):
                    found = True
                    message = f"📊 *{group['group']} Standings:*\n\n"
                    for team in group["table"]:
                        message += (
                            f"{team['position']}. {team['team']['name']}\n"
                            f"P{team['playedGames']} W{team['won']} D{team['draw']} L{team['lost']} | GD{team['goalDifference']:+d} | Pts {team['points']}\n\n"
                        )
                    await update.message.reply_text(message, parse_mode="Markdown")
            if not found:
                await update.message.reply_text("❌ Invalid group. Try A through L.")
        return
    keyboard = [
        [
            InlineKeyboardButton("📊 All Groups", callback_data="standings_all"),
            InlineKeyboardButton("🔤 Pick a Group", callback_data="standings_pick"),
        ],
        [
            InlineKeyboardButton("⭐ My Team's Group", callback_data="standings_myteam"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📊 *Which standings would you like?*",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def standings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    response = requests.get(
        FOOTBALL_API_URL + "competitions/WC/standings",
        headers=headers
    )
    if response.status_code != 200:
        await query.edit_message_text("❌ Could not fetch standings. Try again later.")
        return
    data = response.json()
    groups = data["standings"]
    if query.data == "standings_all":
        await query.edit_message_text("📊 *All World Cup Groups:*", parse_mode="Markdown")
        for group in groups:
            message = f"*{group['group']}*\n\n"
            for team in group["table"]:
                message += (
                    f"{team['position']}. {team['team']['name']}\n"
                    f"P{team['playedGames']} W{team['won']} D{team['draw']} L{team['lost']} | GD{team['goalDifference']:+d} | Pts {team['points']}\n\n"
                )
            await query.message.reply_text(message, parse_mode="Markdown")
    elif query.data == "standings_pick":
        group_keyboard = [
            [
                InlineKeyboardButton("Group A", callback_data="group_A"),
                InlineKeyboardButton("Group B", callback_data="group_B"),
                InlineKeyboardButton("Group C", callback_data="group_C"),
            ],
            [
                InlineKeyboardButton("Group D", callback_data="group_D"),
                InlineKeyboardButton("Group E", callback_data="group_E"),
                InlineKeyboardButton("Group F", callback_data="group_F"),
            ],
            [
                InlineKeyboardButton("Group G", callback_data="group_G"),
                InlineKeyboardButton("Group H", callback_data="group_H"),
                InlineKeyboardButton("Group I", callback_data="group_I"),
            ],
            [
                InlineKeyboardButton("Group J", callback_data="group_J"),
                InlineKeyboardButton("Group K", callback_data="group_K"),
                InlineKeyboardButton("Group L", callback_data="group_L"),
            ]
        ]
        await query.edit_message_text(
            "🔤 *Select a group:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(group_keyboard)
        )
    elif query.data == "standings_myteam":
        await query.edit_message_text(
            "⭐ Set your favorite team first using /alerts"
        )
    elif query.data.startswith("group_"):
        choice = query.data.split("_")[1]
        found = False
        for group in groups:
            if group["group"].upper().endswith(choice.upper()):
                found = True
                message = f"📊 *{group['group']} Standings:*\n\n"
                for team in group["table"]:
                    message += (
                        f"{team['position']}. {team['team']['name']}\n"
                        f"P{team['playedGames']} W{team['won']} D{team['draw']} L{team['lost']} | GD{team['goalDifference']:+d} | Pts {team['points']}\n\n"
                    )
                await query.edit_message_text(message, parse_mode="Markdown")
        if not found:
            await query.edit_message_text("❌ Could not find that group.")

async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        team_query = " ".join(context.args).lower()
        await update.message.reply_text(f"🔍 Searching for {team_query}...")
        headers = {"X-Auth-Token": FOOTBALL_API_KEY}
        response = requests.get(
            FOOTBALL_API_URL + "competitions/WC/matches?status=IN_PLAY,PAUSED,LIVE",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            matches = data["matches"]
            found = False
            for match in matches:
                home = match["homeTeam"]["name"]
                away = match["awayTeam"]["name"]
                if team_query in home.lower() or team_query in away.lower():
                    found = True
                    home_score = match["score"]["fullTime"]["home"]
                    away_score = match["score"]["fullTime"]["away"]
                    minute = match.get("minute") or match.get("currentPeriod", "?")
                    await update.message.reply_text(
                        f"🔴 *Live Score:*\n\n"
                        f"⚽ {home} {home_score} - {away_score} {away}\n"
                        f"⏱ Minute: {minute}",
                        parse_mode="Markdown"
                    )
            if not found:
                await update.message.reply_text(
                    f"😴 {team_query.title()} are not playing right now.\n\n"
                    "Use /fixtures to see their next match."
                )
        else:
            await update.message.reply_text("❌ Could not fetch scores. Try again later.")
        return

    # No args — show all live matches with group picker
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    response = requests.get(
        FOOTBALL_API_URL + "competitions/WC/matches?status=IN_PLAY,PAUSED,LIVE",
        headers=headers
    )
    if response.status_code == 200:
        data = response.json()
        matches = data["matches"]
        if not matches:
            await update.message.reply_text(
                "😴 No live matches right now.\n\n"
                "Use /fixtures to see upcoming matches."
            )
            return
        message = "🔴 *All Live Scores:*\n\n"
        for match in matches:
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            home_score = match["score"]["fullTime"]["home"]
            away_score = match["score"]["fullTime"]["away"]
            minute = match.get("minute", "?")
            message += (
                f"⚽ {home} {home_score} - {away_score} {away}\n"
                f"⏱ Minute: {minute}\n\n"
            )
        keyboard = [
            [
                InlineKeyboardButton("🔍 Search by Team", callback_data="score_search"),
                InlineKeyboardButton("🔄 Refresh", callback_data="score_refresh"),
            ]
        ]
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("❌ Could not fetch scores. Try again later.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        f"👋 Welcome {user.first_name} to MatchPulse AI!\n\n"
        "⚽ Your FIFA World Cup 2026 companion.\n\n"
        "Here's what I can do:\n"
        "📅 /fixtures - Today's matches\n"
        "📊 /standings - Group standings\n"
        "🔴 /score - Live scores\n"
        "🔔 /alerts - Manage followed teams\n"
        "⭐ /myscore - Your teams live scores\n"
        "❓ /help - All commands\n\n"
        "Let's get started! Use /alerts to follow your teams 🏆"
    )

async def myscore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    followed = get_followed_teams(user_id)

    if not followed:
        await update.message.reply_text(
            "⭐ You're not following any teams yet.\n\n"
            "Use /alerts to follow your teams first."
        )
        return

    await update.message.reply_text("🔍 Checking your teams...")

    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    response = requests.get(
        FOOTBALL_API_URL + "competitions/WC/matches?status=IN_PLAY,PAUSED,LIVE",
        headers=headers
    )

    if response.status_code != 200:
        await update.message.reply_text("❌ Could not fetch scores. Try again later.")
        return

    data = response.json()
    matches = data["matches"]

    message = "⭐ *Your Teams Live Scores:*\n\n"
    found_any = False

    for team in followed:
        team_found = False
        for match in matches:
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            if team.lower() in home.lower() or team.lower() in away.lower():
                team_found = True
                found_any = True
                home_score = match["score"]["fullTime"]["home"]
                away_score = match["score"]["fullTime"]["away"]
                minute = match.get("minute", "?")
                message += (
                    f"🔴 *{home} {home_score} - {away_score} {away}*\n"
                    f"⏱ Minute: {minute}\n\n"
                )
        if not team_found:
            message += f"😴 *{team}* — Not playing right now\n\n"

    await update.message.reply_text(message, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ *MatchPulse AI — Commands*\n\n"
        "📅 /fixtures — Browse World Cup fixtures\n"
        "📊 /standings — Live group standings\n"
        "🔴 /score — All live match scores\n"
        "🔴 /score [team] — Specific team score\n"
        "⭐ /myscore — Your followed teams scores\n"
        "🔔 /alerts — Follow or unfollow teams\n\n"
        "💡 *Tips:*\n"
        "• Use acronyms: /score bra, /score eng\n"
        "• Standings by group: /standings A\n"
        "• All standings: /standings all\n"
        "• Your teams: /standings myteams\n\n"
        "⚽ *World Cup 2026 starts June 11!*",
        parse_mode="Markdown"
    )

def main():
    init_db()
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )
    app.add_handler(get_alerts_handler())
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("fixtures", fixtures))
    app.add_handler(CommandHandler("standings", standings))
    app.add_handler(CallbackQueryHandler(standings_callback))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(CommandHandler("myscore", myscore))
    app.add_handler(CommandHandler("help", help_command))
    print("✅ MatchPulse AI is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
