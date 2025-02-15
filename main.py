import asyncio
import logging
from datetime import datetime, timedelta
from os import getenv
from dotenv import load_dotenv
from tinkoff.invest import Client, CandleInterval
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Загрузка переменных окружения из .env
load_dotenv()

# Настройки
TINKOFF_TOKEN = getenv("TINKOFF_TOKEN")
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
THRESHOLD_PERCENT = 2.0  # Пороговое значение для скачка цены (в процентах)
INTERVAL = CandleInterval.CANDLE_INTERVAL_1_MIN  # Интервал свечей (1 минута)

# Логирование
logging.basicConfig(level=logging.INFO)

# Словарь для хранения chat_id пользователей
user_chat_ids = set()

# Функция для получения последней цены
def get_last_price(client, figi):
    candles = client.get_all_candles(
        figi=figi,
        from_=datetime.utcnow() - timedelta(minutes=5),
        interval=INTERVAL,
    )
    prices = [candle.close.units + candle.close.nano / 1e9 for candle in candles]
    return prices[-1] if prices else None

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_chat_ids.add(chat_id)
    await update.message.reply_text("Бот запущен! Вы будете получать уведомления о резких скачках цен.")

# Функция для проверки скачков
async def check_price_spikes(context: ContextTypes.DEFAULT_TYPE):
    with Client(TINKOFF_TOKEN) as client:
        # Пример: отслеживаем акции Сбербанка (замените FIGI на нужный)
        figi = "BBG004730N88"  # FIGI для SBER
        previous_price = None

        while True:
            current_price = get_last_price(client, figi)
            if current_price is None:
                logging.info("Не удалось получить цену")
                await asyncio.sleep(60)
                continue

            if previous_price is not None:
                price_change_percent = abs((current_price - previous_price) / previous_price * 100)
                if price_change_percent >= THRESHOLD_PERCENT:
                    message = (
                        f"⚠️ Резкий скачок цены!\n"
                        f"Инструмент: SBER\n"
                        f"Старая цена: {previous_price:.2f}\n"
                        f"Новая цена: {current_price:.2f}\n"
                        f"Изменение: {price_change_percent:.2f}%"
                    )
                    await bot.send_message(chat_id=CHAT_ID, text=message)
                    logging.info(f"Отправлено уведомление: {message}")

            previous_price = current_price
            await asyncio.sleep(60)  # Проверяем каждую минуту

# Основная функция
def main():
    # Создаем приложение Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # Запускаем задачу для проверки скачков цен
    application.job_queue.run_repeating(check_price_spikes, interval=60, first=0)

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
