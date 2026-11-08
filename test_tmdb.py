import requests

# ВСТАВЬ СЮДА СВОЙ КЛЮЧ ИЗ TMDB
API_KEY = "0974b8ab63ab8b7059c2c6ad9b3d7342"

# Ищем Наруто в базе TMDB
query = "Naruto Shippuden"  # или "Naruto 2002"
url = f"https://api.themoviedb.org/3/search/multi?api_key={API_KEY}&query={query}&language=ru-RU"

response = requests.get(url)
data = response.json()

if response.status_code == 200:
    if data["results"]:
        first = data["results"][0]
        print("Успех! Нашли:")
        print("Название:", first.get("name") or first.get("title"))
        print(
            "Год:", (first.get("first_air_date") or first.get("release_date", ""))[:4]
        )
        print(
            "Постер:", "https://image.tmdb.org/t/p/w500" + first.get("poster_path", "")
        )
    else:
        print("Ничего не найдено.")
else:
    print("Ошибка API. Проверь ключ.", response.status_code)
