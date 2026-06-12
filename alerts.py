from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from database import follow_team, unfollow_team, get_followed_teams
from constants import FLAGS, WC_TEAMS, TEAM_ACRONYMS

SEARCH, CONFIRM, UNFOLLOW_SELECT = range(3)



def build_follow_keyboard(matches, selected):
    keyboard = []
    pairs = [matches[i:i+2] for i in range(0, len(matches[:8]), 2)]
    for pair in pairs:
        row = []
        for team in pair:
            if team in selected:
                row.append(InlineKeyboardButton(
                    f"✅ {team}", callback_data=f"toggle_follow_{team}"
                ))
            else:
                row.append(InlineKeyboardButton(
                    team, callback_data=f"toggle_follow_{team}"
                ))
        keyboard.append(row)
    keyboard.append([
        InlineKeyboardButton("🔍 Search Again", callback_data="search_again"),
        InlineKeyboardButton("✅ Done", callback_data="follow_done"),
    ])
    return keyboard

def build_unfollow_keyboard(followed, selected):
    keyboard = []
    pairs = [followed[i:i+2] for i in range(0, len(followed), 2)]
    for pair in pairs:
        row = []
        for team in pair:
            if team in selected:
                row.append(InlineKeyboardButton(
                    f"❌ {team}", callback_data=f"toggle_unfollow_{team}"
                ))
            else:
                row.append(InlineKeyboardButton(
                    team, callback_data=f"toggle_unfollow_{team}"
                ))
        keyboard.append(row)
    keyboard.append([
        InlineKeyboardButton("🗑 Confirm Unfollow", callback_data="confirm_unfollow"),
        InlineKeyboardButton("🔙 Back", callback_data="search_again"),
    ])
    return keyboard

async def alerts_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["in_alerts"] = True
    user_id = update.effective_user.id
    followed = get_followed_teams(user_id)
    context.user_data["follow_queue"] = []
    context.user_data["unfollow_queue"] = []
    context.user_data["search_results"] = []

    message = "🔔 *Alerts & Followed Teams*\n\n"
    if followed:
        message += "⭐ *Your followed teams:*\n"
        for team in followed:
            message += f"• {team}\n"
        message += "\n"
    else:
        message += "You're not following any teams yet.\n\n"
    message += "Type a team name to search and follow:"

    keyboard = []
    if followed:
        keyboard.append([
            InlineKeyboardButton("➖ Unfollow Teams", callback_data="unfollow_menu"),
            InlineKeyboardButton("✅ Done", callback_data="alerts_done"),
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("✅ Done", callback_data="alerts_done"),
        ])

    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SEARCH

async def search_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.message.text.lower().strip()

        if query in TEAM_ACRONYMS:
            matches = [TEAM_ACRONYMS[query]]
        else:
            matches = [t for t in WC_TEAMS if t.lower().startswith(query)]

        if not matches:
            keyboard = [[InlineKeyboardButton("✅ Done", callback_data="alerts_done")]]
            await update.message.reply_text(
        "❌ No teams found.\n\n"
        "⚽ Type a team name to search.\n"
        "Example: bra, eng, Mexico\n\n"
        "Or tap Done to exit alerts.",
                reply_markup=InlineKeyboardMarkup(keyboard)
             )
            return SEARCH

        context.user_data["search_results"] = matches
        selected = context.user_data.get("follow_queue", [])
        keyboard = build_follow_keyboard(matches, selected)

        await update.message.reply_text(
            f"Found *{len(matches)}* team(s). Tap to select, tap again to deselect:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CONFIRM

    except Exception as e:
        await update.message.reply_text(
            "⚠️ Something went wrong. Please type /alerts to start again."
        )
        return ConversationHandler.END

async def alerts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "search_again":
        context.user_data["follow_queue"] = []
        context.user_data["search_results"] = []
        await query.edit_message_text(
            "🔍 Type a team name to search:"
        )
        return SEARCH

    if query.data == "alerts_done":
        context.user_data["in_alerts"] = False
        followed = get_followed_teams(user_id)
        if followed:
            teams_list = "\n".join([f"• {t}" for t in followed])
            await query.edit_message_text(
                f"✅ *All set! You're following:*\n\n{teams_list}\n\n"
                "Use /myscore to see their live scores.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "👋 No teams followed yet. Use /alerts anytime to follow teams."
            )
        return ConversationHandler.END

    if query.data.startswith("toggle_follow_"):
        team_name = query.data.replace("toggle_follow_", "")
        follow_queue = context.user_data.get("follow_queue", [])

        if team_name in follow_queue:
            follow_queue.remove(team_name)
        else:
            follow_queue.append(team_name)

        context.user_data["follow_queue"] = follow_queue
        matches = context.user_data.get("search_results", [])
        keyboard = build_follow_keyboard(matches, follow_queue)

        selected_text = ""
        if follow_queue:
            selected_text = "\n\n*Selected:*\n" + "\n".join([f"✅ {t}" for t in follow_queue])

        await query.edit_message_text(
            f"Found *{len(matches)}* team(s). Tap to select, tap again to deselect:{selected_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CONFIRM

    if query.data == "follow_done":
        follow_queue = context.user_data.get("follow_queue", [])
        if not follow_queue:
            await query.edit_message_text(
                "⚠️ No teams selected. Type a team name to search:"
            )
            return SEARCH

        for team in follow_queue:
            follow_team(user_id, team.strip())

        followed = get_followed_teams(user_id)
        teams_list = "\n".join([f"• {t}" for t in followed])
        context.user_data["follow_queue"] = []

        keyboard = [[
            InlineKeyboardButton("➕ Follow More", callback_data="search_again"),
            InlineKeyboardButton("➖ Unfollow Teams", callback_data="unfollow_menu"),
        ],[
            InlineKeyboardButton("✅ Done", callback_data="alerts_done"),
        ]]

        await query.edit_message_text(
            f"✅ *Teams added!*\n\n⭐ Now following:\n{teams_list}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CONFIRM

    if query.data == "unfollow_menu":
        followed = get_followed_teams(user_id)
        if not followed:
            await query.edit_message_text(
                "⚠️ You're not following any teams yet.\n\nType a team name to search:"
            )
            return SEARCH

        context.user_data["unfollow_queue"] = []
        keyboard = build_unfollow_keyboard(followed, [])

        await query.edit_message_text(
            "➖ *Select teams to unfollow:*\n\nTap to select, tap again to deselect.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return UNFOLLOW_SELECT

    if query.data.startswith("toggle_unfollow_"):
        team_name = query.data.replace("toggle_unfollow_", "")
        unfollow_queue = context.user_data.get("unfollow_queue", [])

        if team_name in unfollow_queue:
            unfollow_queue.remove(team_name)
        else:
            unfollow_queue.append(team_name)

        context.user_data["unfollow_queue"] = unfollow_queue
        followed = get_followed_teams(user_id)
        keyboard = build_unfollow_keyboard(followed, unfollow_queue)

        selected_text = ""
        if unfollow_queue:
            selected_text = "\n\n*Selected to remove:*\n" + "\n".join([f"❌ {t}" for t in unfollow_queue])

        await query.edit_message_text(
            f"➖ *Select teams to unfollow:*\n\nTap to select, tap again to deselect.{selected_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return UNFOLLOW_SELECT

    if query.data == "confirm_unfollow":
        unfollow_queue = context.user_data.get("unfollow_queue", [])
        if not unfollow_queue:
            await query.edit_message_text(
                "⚠️ No teams selected. Tap teams to select them."
            )
            return UNFOLLOW_SELECT

        for team in unfollow_queue:
            unfollow_team(user_id, team)

        followed = get_followed_teams(user_id)
        context.user_data["unfollow_queue"] = []

        if followed:
            teams_list = "\n".join([f"• {t}" for t in followed])
            keyboard = [[
                InlineKeyboardButton("➕ Follow More", callback_data="search_again"),
                InlineKeyboardButton("➖ Unfollow More", callback_data="unfollow_menu"),
            ],[
                InlineKeyboardButton("✅ Done", callback_data="alerts_done"),
            ]]
            await query.edit_message_text(
                f"✅ *Teams removed!*\n\n⭐ Still following:\n{teams_list}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(
                "✅ All teams removed.\n\nType a team name to follow one:"
            )
            return SEARCH

        return CONFIRM

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["in_alerts"] = False
    await update.message.reply_text("Alerts setup cancelled.")
    return ConversationHandler.END

def get_alerts_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("alerts", alerts_start)],
        states={
            SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_team),
                CallbackQueryHandler(alerts_callback),
            ],
            CONFIRM: [
                CallbackQueryHandler(alerts_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_team),
            ],
            UNFOLLOW_SELECT: [
                CallbackQueryHandler(alerts_callback),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
        block=True
    )

