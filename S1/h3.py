import requests

def send_telegram(message):
    token = '8162677613:AAHRmQEOZqK-FFIGFpVUR4VTFbvhnJwgfGo'
    chat_id = '7297780886'
    url = f'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}'
    response = requests.get(url)
    print("응답 상태 코드:", response.status_code)
    print("응답 내용:", response.text)

send_telegram('DOGE가 볼린저 밴드 하단 돌파')
