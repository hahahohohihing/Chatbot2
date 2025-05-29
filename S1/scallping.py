import pyupbit
import time
import datetime
import requests

# === 설정 ===
access = "YOUR_ACCESS_KEY"
secret = "YOUR_SECRET_KEY"
upbit = pyupbit.Upbit(access, secret)
symbol = "KRW-OM"  # ← 여기를 원하는 종목으로 바꾸면 전체 적용됨
coin = symbol.split('-')[1]

# 텔레그램 설정 (옵션)
def send_telegram(msg):
    token = "YOUR_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
    try:
        requests.get(url)
    except:
        print("텔레그램 전송 실패")

# 장세 분석 (5분봉 기준)
def get_market_trend():
    df = pyupbit.get_ohlcv(symbol, interval="minute5", count=20)
    ma5 = df['close'].rolling(window=5).mean().iloc[-1]
    ma20 = df['close'].rolling(window=20).mean().iloc[-1]
    if ma5 > ma20 + 0.5:
        return "bull"
    elif ma5 < ma20 - 0.5:
        return "bear"
    else:
        return "side"

# 전략 파라미터 설정
def get_strategy_params(trend):
    if trend == "bull":
        return {"take_profit_pct": 0.00280, "stop_loss_pct": 0.01000}  # + -0.1%
    elif trend == "side":
        return {"take_profit_pct": 0.00240, "stop_loss_pct": 0.01000}  # + -0.1%
    else:
        return {"take_profit_pct": 0.00180, "stop_loss_pct": 0.01000}  #  -0.1%

def run_strategy():
    print("📊 자동매매 시작")
    flag_entry = False
    prev_open = None
    prev_close = None
    entry = None

    while True:
        try:
            now = datetime.datetime.now()

            # 5분봉 시작 시점에 양봉 조건 확인
            if now.minute % 5 == 0 and now.second < 2:
                trend = get_market_trend()
                params = get_strategy_params(trend)
                take_profit_pct = params["take_profit_pct"]
                stop_loss_pct = params["stop_loss_pct"]

                df = pyupbit.get_ohlcv(symbol, interval="minute5", count=2)
                prev_open = df.iloc[-2]['open']
                prev_close = df.iloc[-2]['close']
                price = pyupbit.get_current_price(symbol)

                if prev_close > prev_open and price > prev_close:
                    flag_entry = True  # 양봉 확인됨 → 눌림 대기 시작
                    print(f"양봉 조건 만족 → 눌림 진입 대기 (prev_close={prev_close})")
                    send_telegram("🟡 양봉 시작 감지 → 눌림 대기 중")

            # 눌림 조건 충족 시 진입
            if flag_entry and prev_close:
                price = pyupbit.get_current_price(symbol)
                if price <= prev_close * 0.998:  # 약 0.2% 눌림
                    krw = upbit.get_balance("KRW")
                    if krw and krw > 5000:
                        amt = krw * 0.99
                        upbit.buy_market_order(symbol, amt)
                        entry = price
                        send_telegram(f"🟢 눌림 매수 진입! 진입가: {entry}")
                        print(f"눌림 매수 진입: {entry}원")
                        flag_entry = False  # 진입 완료 후 플래그 해제

                        # 모니터링 루프
                        while True:
                            curr = pyupbit.get_current_price(symbol)
                            if curr is None:
                                time.sleep(1)
                                continue
                            if curr >= entry * (1 + take_profit_pct):
                                vol = upbit.get_balance(coin)
                                if vol:
                                    upbit.sell_market_order(symbol, vol)
                                    send_telegram(f"✅ 익절 성공! 매도가: {curr:.2f}")
                                    break
                            elif curr <= entry * (1 - stop_loss_pct):
                                vol = upbit.get_balance(coin)
                                if vol:
                                    upbit.sell_market_order(symbol, vol)
                                    send_telegram(f"❌ 손절 발생! 매도가: {curr:.2f}")
                                    break
                            time.sleep(1)

            time.sleep(1)

        except Exception as e:
            print("오류:", e)
            send_telegram(f"⚠ 오류 발생: {e}")
            time.sleep(10)

if __name__ == '__main__':
    run_strategy()
