import os
import requests
import yfinance as yf
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from flask import Flask, request, abort

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 設定你的 Channel Access Token 和 Channel Secret
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 存儲目標股票代碼和目標價格
target_prices = {"AAPL": 150}  # 示例數據

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    app.logger.info("Received message: " + event.message.text)
    text = event.message.text.split()
    if len(text) == 3 and text[0].lower() == 'set':
        stock_symbol = text[1].upper()
        try:
            target_price = float(text[2])
            target_prices[stock_symbol] = target_price
            reply_message = f'已設定 {stock_symbol} 的目標價格為 {target_price}'
            app.logger.info(reply_message)
        except ValueError:
            reply_message = '目標價格必須是數字。'
            app.logger.warning(reply_message)
    else:
        reply_message = '請輸入正確格式：set 股票代碼 目標價格'
        app.logger.warning(reply_message)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_message)
    )
    app.logger.info("Replied to user")

def get_stock_price(stock_symbol):
    stock = yf.Ticker(stock_symbol)
    stock_info = stock.history(period="1d")
    if not stock_info.empty:
        return stock_info['Close'].iloc[-1]
    return None

def check_prices():
    logger.info("Checking stock prices...")
    for stock_symbol, target_price in target_prices.items():
        current_price = get_stock_price(stock_symbol)
        if current_price is not None:
            logger.info(f"{stock_symbol}: Current price {current_price}, Target price {target_price}")
            if current_price >= target_price:
                message = f'{stock_symbol} 已達到目標價格 {target_price}，目前價格為 {current_price}'
                try:
                    line_bot_api.push_message(
                        '0965277931',  # 使用者的 LINE USER ID
                        TextSendMessage(text=message)
                    )
                    logger.info("Sent notification: " + message)
                    del target_prices[stock_symbol]  # 移除已達到目標的股票
                except LineBotApiError as e:
                    logger.error(f"Error sending message: {e}")

if __name__ == "__main__":
    if os.getenv('GITHUB_ACTIONS'):
        # 在 CI/CD 環境中，僅運行股票監控
        check_prices()
    else:
        # 在開發環境中運行 Flask 伺服器和股票監控
        scheduler = BackgroundScheduler()
        scheduler.add_job(check_prices, 'interval', minutes=5)
        scheduler.start()
        app.run(debug=True)
