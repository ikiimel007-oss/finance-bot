#!/system/bin/sh
export BOT_TOKEN="7696393825:AAGsg0HSxacNtQ0J-lMz3aOoySrI_yAIQm0"
BOT_DIR="/root/FinanceBot"
LOG="$BOT_DIR/bot.log"

cd "$BOT_DIR" || exit 1

while true; do
    echo "[$(date)] Starting bot..." >> "$LOG"
    python3 bot.py >> "$LOG" 2>&1
    echo "[$(date)] Bot stopped. Restarting in 3s..." >> "$LOG"
    sleep 3
done
