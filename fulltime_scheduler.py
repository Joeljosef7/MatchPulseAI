import os
import logging
import requests
from dotenv import load_dotenv
from database import get_all_follows, fulltime_alert_sent, mark_fulltime_alert_sent
from constants import FLAGS

load_dotenv()

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")
FOOTBALL_API_URL = "https://api.football-data.org/v4/"


async def check_fulltime_matches(context):
    try:
        follows = get_all_follows()

        if not follows:
            return

        headers = {
            "X-Auth-Token": FOOTBALL_API_KEY
        }

        response = requests.get(
            FOOTBALL_API_URL + "competitions/WC/matches?status=FINISHED",
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            logging.error(
                f"Full-time API error: {response.status_code}"
            )
            return

        matches = response.json()["matches"]

        for match in matches:

            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]

            match_id = match["id"]

            home_score = match["score"]["fullTime"]["home"]
            away_score = match["score"]["fullTime"]["away"]

            if home_score is None or away_score is None:
                continue

            if home_score > away_score:
                result = f"{home} won"
            elif away_score > home_score:
                result = f"{away} won"
            else:
                result = "Draw"

            home_flag = FLAGS.get(home, "🏳️")
            away_flag = FLAGS.get(away, "🏳️")

            for user_id, team in follows:

                if team not in (home, away):
                    continue

                if fulltime_alert_sent(user_id, match_id):
                    continue

                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🏁 *FULL TIME*\n\n"
                        f"{home_flag} *{home}* {home_score} - {away_score} *{away}* {away_flag}\n\n"
                        f"📊 {result}"
                    ),
                    parse_mode="Markdown"
                )

                mark_fulltime_alert_sent(
                    user_id,
                    match_id
                )

                logging.info(
                    f"Full-time alert sent to {user_id}"
                )

    except Exception as e:
        logging.exception(
            f"Full-time scheduler error: {e}"
        )
