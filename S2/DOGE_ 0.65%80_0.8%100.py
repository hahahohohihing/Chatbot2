import pyupbit
import time
import datetime
import numpy as np
import requests
import os


# API 키 설정
access = os.getenv('UPBIT_ACCESS_KEY')
secret = os.getenv('UPBIT_SECRET_KEY')
upbit = pyupbit.Upbit(access, secret)

# 텔레그램 설정
telegram_token = "8162677613:AAHRmQEOZqK-FFIGFpVUR4VTFbvhnJwgfGo"
telegram_chat_id = "7297780886"

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {"chat_id": telegram_chat_id, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        print('텔레그램 전송 실패')

# 기술 지표
def compute_rsi(data, period=14):
    delta = data['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_bollinger_bands(series, window=20, num_std=2):
    ma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    return ma, ma + num_std * std, ma - num_std * std

# 지표 초기화
def get_daily_indicators(ticker="KRW-DOGE"):
    df = pyupbit.get_ohlcv(ticker, interval="day", count=50)
    today = df.iloc[-1]
    low, high, close, volume = today['low'], today['high'], today['close'], today['volume']
    entry_price = low + (high - low) * 0.2
    exit1_price = low + (high - low) * 0.65
    exit2_price = low + (high - low) * 0.8
    ma20 = df['close'].rolling(window=20).mean().iloc[-1]
    rsi = compute_rsi(df).iloc[-1]
    _, _, bb_lower = compute_bollinger_bands(df['close'])
    bb_lower_today = bb_lower.iloc[-1]
    volume_ma = df['volume'].rolling(window=20).mean().iloc[-1]

    return {
        "low": low,
        "high": high,
        "close": close,
        "volume": volume,
        "entry": entry_price,
        "exit1": exit1_price,
        "exit2": exit2_price,
        "ma20": ma20,
        "rsi": rsi,
        "bb_lower": bb_lower_today,
        "vol_ma": volume_ma
    }

def run_strategy(ticker="KRW-DOGE"):
    last_checked_day = None
    state = {
        "bought": False,
        "bought_extra": False,
        "partial_sold": False,
        "holdings": 0
    }
    last_log_time = datetime.datetime.now()

    while True:
        try:
            now = datetime.datetime.now()

            if (now - last_log_time).total_seconds() >= 600:
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ✅ 전략 실행 중...")
                last_log_time = now

            # 지표 초기화
            if last_checked_day != now.date() and now.hour >= 9:
                indicators = get_daily_indicators(ticker)
                last_checked_day = now.date()
                state = {
                    "bought": False,
                    "bought_extra": False,
                    "partial_sold": False,
                    "holdings": 0
                }
                cut_price = indicators["low"] * 0.98
                send_telegram_message(
                    f"📊 전략 초기화 완료\n"
                    f"진입가: {indicators['entry']:.2f}, 1차청산: {indicators['exit1']:.2f}, 2차청산: {indicators['exit2']:.2f}, "
                    f"손절가: {cut_price:.2f}, MA20: {indicators['ma20']:.2f}"
                )

            price = pyupbit.get_current_price(ticker)
            if price is None:
                time.sleep(10)
                continue

            # 1차 진입
            if not state["bought"] and price <= indicators["entry"]:
                krw = upbit.get_balance("KRW")
                if krw is None or krw < 5000:
                    send_telegram_message("❗ KRW 잔고 부족 또는 조회 실패")
                    time.sleep(10)
                    continue
                amount = krw * 0.8
                res = upbit.buy_market_order(ticker, amount)
                if res:
                    send_telegram_message(f"✅ 진입가 도달 → 80% 매수\n가격: {price:.2f}")
                    state["bought"] = True
                time.sleep(5)

            # 2차 진입 조건
            if state["bought"] and not state["bought_extra"]:
                if (indicators["rsi"] <= 30 and indicators["close"] < indicators["bb_lower"]
                        and indicators["volume"] > indicators["vol_ma"]):
                    res = upbit.buy_market_order(ticker, 10000)
                    if res:
                        send_telegram_message("🎯 RSI/볼밴/거래량 조건 충족 → 추가 매수 10,000원")
                        state["bought_extra"] = True
                    time.sleep(5)

            # 보유량 갱신
            if state["bought"] and state["holdings"] == 0:
                bal = upbit.get_balance(ticker)
                state["holdings"] = float(bal) if bal else 0.0

            # 1차 청산
            if state["bought"] and not state["partial_sold"] and state["holdings"] > 0 and price >= indicators["exit1"]:
                qty = state["holdings"] * 0.8
                upbit.sell_market_order(ticker, qty)
                send_telegram_message(f"💰 1차 청산 도달 → 80% 매도\n가격: {price:.2f}")
                state["holdings"] -= qty
                state["partial_sold"] = True
                time.sleep(5)

            # 2차 청산
            if state["partial_sold"] and state["holdings"] > 0 and price >= indicators["exit2"]:
                upbit.sell_market_order(ticker, state["holdings"])
                send_telegram_message(f"🏁 2차 청산 도달 → 나머지 전량 매도\n가격: {price:.2f}")
                state["holdings"] = 0
                state["bought"] = False
                state["bought_extra"] = False
                state["partial_sold"] = False
                time.sleep(5)

            # MA20 근접 청산 (선택)
            if state["holdings"] > 0:
                if abs(price - indicators["ma20"]) / indicators["ma20"] <= 0.003:
                    upbit.sell_market_order(ticker, state["holdings"])
                    send_telegram_message(f"📉 MA20 근접 → 전량 청산\n가격: {price:.2f}")
                    state["holdings"] = 0
                    state["bought"] = False
                    state["bought_extra"] = False
                    state["partial_sold"] = False
                    time.sleep(5)

            # 손절 조건
            if state["bought"] and state["holdings"] > 0 and price <= indicators["low"] * 0.98:
                upbit.sell_market_order(ticker, state["holdings"])
                send_telegram_message(f"⚠ 손절가 도달 → 전량 청산\n현재가: {price:.2f}")
                state["holdings"] = 0
                state["bought"] = False
                state["bought_extra"] = False
                state["partial_sold"] = False
                time.sleep(5)

            time.sleep(30)

        except Exception as e:
            send_telegram_message(f"❗ 오류 발생: {e}")
            time.sleep(60)

if __name__ == '__main__':
    run_strategy("KRW-DOGE")
