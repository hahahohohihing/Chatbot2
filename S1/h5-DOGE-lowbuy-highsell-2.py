import time
import pyupbit
import os
import requests
import pandas as pd
from dotenv import load_dotenv

# .env 파일에서 키 불러오기
load_dotenv()
access = os.getenv('UPBIT_ACCESS_KEY')
secret = os.getenv('UPBIT_SECRET_KEY')
upbit = pyupbit.Upbit(access, secret)

# 고정 매수 금액 (KRW 단위)
FIXED_KRW_AMOUNT = 150000

# 텔레그램 알림 함수
def send_telegram(message):
    token = '8162677613:AAHRmQEOZqK-FFIGFpVUR4VTFbvhnJwgfGo'
    chat_id = '7297780886'
    url = f'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}'
    requests.get(url)

# 시장가 매수 함수
def buy_market(symbol='KRW-DOGE', krw_amount=FIXED_KRW_AMOUNT):
    try:
        res = upbit.buy_market_order(symbol, krw_amount)
        print('매수 주문 전송 완료', res)
        return res
    except Exception as e:
        print('매수 주문 실패:', e)
        send_telegram(f'[에러] 매수 실패: {e}')
        return None

# 시장가 매도 함수
def sell_market(symbol='KRW-DOGE', volume=None):
    try:
        res = upbit.sell_market_order(symbol, volume)
        print('판매 성공:', res)
        return res
    except Exception as e:
        print('판매 실패:', e)
        send_telegram(f'[에러] 매도 실패: {e}')
        return None

# RSI 계산 함수
def calculate_rsi(prices, period=14):
    df = pd.DataFrame(prices, columns=['close'])
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# 초기 변수 설정
prices = []
last_alert_time = 0
alert_cooldown = 60 * 10  # 10분
partial_sell_done = False
full_sell_done = False
was_cut_loss = False
symbol = 'KRW-DOGE'

while True:
    try:
        # 실시간 DOGE 가격 받아오기
        price = pyupbit.get_current_price(symbol)
        print("현재 DOGE 가격 =", price)

        prices.append(price)
        if len(prices) > 100:
            prices.pop(0)

        if len(prices) >= 20:
            df = pd.DataFrame(prices, columns=["close"])
            df["MA20"] = df["close"].rolling(window=20).mean()
            df["STD"] = df["close"].rolling(window=20).std()
            df["lower_band"] = df["MA20"] - 2 * df["STD"]
            rsi = calculate_rsi(prices)
            current_rsi = rsi.iloc[-1]
            lower_band = df["lower_band"].iloc[-1]

            # 거래량 정보 받아오기 (5분봉 20개)
            candle_url = "https://api.upbit.com/v1/candles/minutes/5?market=KRW-DOGE&count=20"
            candle_data = requests.get(candle_url).json()
            volumes = [candle['candle_acc_trade_volume'] for candle in candle_data]
            current_volume = volumes[0]
            avg_volume = sum(volumes[1:]) / len(volumes[1:])
            print(f"현재 DOGE 가격 = {price:.2f} | RSI = {current_rsi:.2f} | 하단 밴드 = {lower_band:.2f} | 거래량 = {current_volume:.2f} / 평균 = {avg_volume:.2f}")

        # 평균 매입가 및 보유량
        avg_price = upbit.get_avg_buy_price('DOGE')
        volume = upbit.get_balance('DOGE')
        current_price = price

        if volume and avg_price:
            if current_price >= avg_price * 1.015 and not partial_sell_done:
                qty = float(volume) / 2
                sell_market(symbol, qty)
                send_telegram(f'판매 성공! 50% 매도\n매입가: {avg_price}, 현재가: {current_price}')
                partial_sell_done = True
            elif current_price >= avg_price * 1.022 and not full_sell_done:
                sell_market(symbol, volume)
                send_telegram(f'판매 성공! 모두 매도\n매입가: {avg_price}, 현재가: {current_price}')
                full_sell_done = True
            elif current_price <= avg_price * 0.971:
                sell_market(symbol, volume)
                send_telegram(f'손절 -1% 실행\n매입가: {avg_price}, 현재가: {current_price}')
                was_cut_loss = True
                partial_sell_done = False
                full_sell_done = False

        # 손절 이후 MA5 > MA20 상향 돌파 시 매수
        if was_cut_loss:
            ma_df = pyupbit.get_ohlcv(symbol, interval="minute5", count=30)
            ma_df["MA5"] = ma_df["close"].rolling(window=5).mean()
            ma_df["MA20"] = ma_df["close"].rolling(window=20).mean()
            prev_ma5 = ma_df["MA5"].iloc[-2]
            prev_ma20 = ma_df["MA20"].iloc[-2]
            curr_ma5 = ma_df["MA5"].iloc[-1]
            curr_ma20 = ma_df["MA20"].iloc[-1]

            if prev_ma5 < prev_ma20 and curr_ma5 > curr_ma20:
                krw_balance = float(upbit.get_balance("KRW"))
                if krw_balance >= FIXED_KRW_AMOUNT:
                    res = buy_market(symbol, FIXED_KRW_AMOUNT)
                    if res:
                        send_telegram(f'손절 후 MA5 상향 돌파 → 150,000원 매수 실행\n현재가: {price}')
                        was_cut_loss = False
                        last_alert_time = time.time()
                        partial_sell_done = False
                        full_sell_done = False
                else:
                    send_telegram(f"[🚫매수 실패] 잔고 부족 (보유 KRW: {krw_balance:.2f})")

        # RSI + 볼밴 + 거래량 조건 매수
        if not was_cut_loss and len(prices) >= 20:
            if price < lower_band and current_rsi < 30 and current_volume > avg_volume:
                now = time.time()
                if now - last_alert_time > alert_cooldown:
                    krw_balance = float(upbit.get_balance("KRW"))
                    if krw_balance >= FIXED_KRW_AMOUNT:
                        res = buy_market(symbol, FIXED_KRW_AMOUNT)
                        if res:
                            send_telegram(f"DOGE 조건 충족! 매수 실행\n- 가격: {price}\n- RSI: {current_rsi:.2f}\n- 거래량: {current_volume:.2f} > 평균: {avg_volume:.2f}")
                            last_alert_time = now
                            partial_sell_done = False
                            full_sell_done = False
                    else:
                        send_telegram(f"[🚫매수 실패] 잔고 부족 (보유 KRW: {krw_balance:.2f})")

        time.sleep(30)

    except Exception as e:
        print("에러 발생 =", e)
        send_telegram(f'[에러 발생] {e}')
        time.sleep(10)
        
