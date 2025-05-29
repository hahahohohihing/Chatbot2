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

# 텔레그램 알림 함수
def send_telegram(message):
    token = '8162677613:AAHRmQEOZqK-FFIGFpVUR4VTFbvhnJwgfGo'
    chat_id = '7297780886'
    url = f'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}'
    requests.get(url)

#시장가 매수 함수
def buy_market(symbol='KRW-DOGE', krw_amount=5000):
    try:
        res = upbit.buy_market_order(symbol, krw_amount)
        print('매수 주문 전송 완료', res)
        return res
    except Exception as e:
        print ('매수 주문 실패:', e)
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

# 가격 리스트 저장용
prices = []
last_alert_time = 0
alert_cooldown = 60 * 10  # 10분 쿨타임

while True:
    try:
        # 실시간 DOGE 가격 받아오기
        url = 'https://api.upbit.com/v1/ticker?markets=KRW-DOGE'
        response = requests.get(url)
        price = response.json()[0]['trade_price']
        print("현재 DOGE 가격 =", price)
        

        prices.append(price)
        if len(prices) > 100:
            prices.pop(0)

        # 조건 감시 (가격 리스트 20개 이상 쌓였을 때만)
        if len(prices) >= 20:
            df = pd.DataFrame(prices, columns=["close"])
            df["MA20"] = df["close"].rolling(window=20).mean()
            df["STD"] = df["close"].rolling(window=20).std()
            df["lower_band"] = df["MA20"] - 2 * df["STD"]
            rsi = calculate_rsi(prices)

            current_rsi = rsi.iloc[-1]
            lower_band = df["lower_band"].iloc[-1]

            # 거래량 정보 받아오기 (1분봉 20개)
            candle_url = "https://api.upbit.com/v1/candles/minutes/1?market=KRW-DOGE&count=20"
            candle_data = requests.get(candle_url).json()
            volumes = [candle['candle_acc_trade_volume'] for candle in candle_data]
            current_volume = volumes[0]
            avg_volume = sum(volumes[1:]) / len(volumes[1:])
            # print(f"[거래량] 현재: {current_volume:.2f}, 평균: {avg_volume:.2f}")
            # print(f"[지표] RSI: {current_rsi:.2f}, 하단 밴드: {lower_band:.2f}")
            print(f"현재 DOGE 가격 = {price:.2f} | RSI = {current_rsi:.2f} | 하단 밴드 = {lower_band:.2f} | 거래량 = {current_volume:.2f} / 평균 = {avg_volume:.2f}")

            # 조건 세 가지 모두 만족 시 텔레그램 전송
            # print(f"조건 검사 → 가격: {price:.2f} < {lower_band:.2f}, RSI: {current_rsi:.2f} < 30, 거래량: {current_volume:.2f} > {avg_volume:.2f}")
            
            if price < lower_band and current_rsi < 30 and current_volume > avg_volume:
                now = time.time()
                if now - last_alert_time > alert_cooldown:
                    send_telegram(
                        f"DOGE 조건 충족!매수 시도 됨\n- 가격: {price}\n- RSI: {current_rsi:.2f}\n- 거래량: {current_volume:.2f} > 평균: {avg_volume:.2f}"
                    )
                    buy_market()
                    last_alert_time = now
                else:
                    print("조건 충족했지만 쿨타임 중")

        time.sleep(10)

    except Exception as e:
        print("에러 발생 =", e)
        time.sleep(10)

