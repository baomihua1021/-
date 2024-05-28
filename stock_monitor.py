import requests
import yfinance as yf
import os

def get_stock_price(stock_symbol):
    stock = yf.Ticker(stock_symbol)
    stock_info = stock.history(period="1d")
    current_price = stock_info['Close'].iloc[-1]
    return current_price

def send_line_notify(message, token):
    headers = {
        'Authorization': f'Bearer {token}'
    }
    data = {
        'message': message
    }
    response = requests.post('https://notify-api.line.me/api/notify', headers=headers, data=data)
    return response.status_code

def main():
    stock_symbol = 'AAPL'  # 你的股票代碼
    target_price = 150.0  # 你的目標價格

    current_price = get_stock_price(stock_symbol)
    if (current_price is not None) and (current_price >= target_price):
        message = f'{stock_symbol} 已達到目標價格 {target_price}，目前價格為 {current_price}'
        token = os.getenv('CHANNEL_ACCESS_TOKEN')
        send_line_notify(message, token)

if __name__ == "__main__":
    main()
