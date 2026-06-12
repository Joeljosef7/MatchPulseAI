import os
import requests
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from database import get_all_follows, alert_already_sent, mark_alert_sent
from constants import FLAGS

load_dotenv()

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")
FOOTBALL_API_URL = "https://api.football-data.org/v4/"


async def check_upcoming_matches(context):
    try:
        follows = get_all_follows()

        if not follows:
            return

        headers = {
            "X-Auth-Token": FOOTBALL_API_KEY
        }

        response = requests.get(
            FOOTBALL_API_URL + "competitions/WC/matches?status=SCHEDULED",
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            logging.error(
                f"Scheduler API error: {response.status_code}"
            )
            return

        matches = response.json()["matches"]

        now = datetime.now(timezone.utc)
        one_hour_later = now + timedelta(hours=1)

        for match in matches:
            match_time = datetime.fromisoformat(
                match["utcDate"].replace("Z", "+00:00")
            )

            if not (now <= match_time <= one_hour_later):
                continue

            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            match_id = match["id"]

            for user_id, team in follows:

                if team not in (home, away):
                    continue

                if alert_already_sent(user_id, match_id):
                    continue

                try:
                    remaining = match_time - now
                    minutes = int(
                        remaining.total_seconds() / 60
                    )

                    if minutes >= 60:
                        time_text = f"{minutes // 60}h"
                    else:
                        time_text = f"{minutes}m"

                    home_flag = FLAGS.get(home, "🏳️")
                    away_flag = FLAGS.get(away, "🏳️")

                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"🔔 *Match Alert!*\n\n"
                            f"⚽ {home_flag} {home}\n"
                            f"🆚\n"
                            f"⚽ {away_flag} {away}\n\n"
                            f"⏳ Starts in {time_text}\n\n"
                            f"Your team *{team}* is playing soon!"
                        ),
                        parse_mode="Markdown"
                    )

                    mark_alert_sent(
                        user_id,
                        match_id
                    )

                    logging.info(
                        f"Alert sent to {user_id} "
                        f"for {home} vs {away}"
                    )

                except Exception as e:
                    logging.error(
                        f"Failed to send alert "
                        f"to {user_id}: {e}"
                    )

    except Exception as e:
        logging.exception(
            f"Scheduler error: {e}"
        )
