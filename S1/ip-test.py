import requests
print("현재 공인 IP:", requests.get("https://api.ipify.org").text)