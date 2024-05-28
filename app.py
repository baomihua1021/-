import os
import requests
import yfinance as yf
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# 設定你的 Channel Access Token 和 Channel Secret
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 存儲目標股票代碼和目標價格
target_prices = {}

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
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.split()
    if len(text) == 3 and text[0].lower() == 'set':
        stock_symbol = text[1].upper()
        try:
            target_price = float(text[2])
            target_prices[stock_symbol] = target_price
            reply_message = f'已設定 {stock_symbol} 的目標價格為 {target_price}'
        except ValueError:
            reply_message = '目標價格必須是數字。'
    else:
        reply_message = '請輸入正確格式：set 股票代碼 目標價格'

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_message)
    )

def get_stock_price(stock_symbol):
    stock = yf.Ticker(stock_symbol)
    stock_info = stock.history(period="1d")
    if not stock_info.empty:
        return stock_info['Close'].iloc[-1]
    return None

def check_prices():
    for stock_symbol, target_price in target_prices.items():
        current_price = get_stock_price(stock_symbol)
        if current_price is not None and current_price >= target_price:
            message = f'{stock_symbol} 已達到目標價格 {target_price}，目前價格為 {current_price}'
            line_bot_api.push_message(
                'YOUR_USER_ID',  # 使用者的 LINE USER ID
                TextSendMessage(text=message)
            )
            del target_prices[stock_symbol]  # 移除已達到目標的股票

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_prices, 'interval', minutes=5)
    scheduler.start()
    app.run()
