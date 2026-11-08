import qbittorrentapi

# Данные для входа
conn_info = list(
    host="localhost",
    port=8080,
    username="admin",
    password="adminadmin",
)

try:
    # Подключаемся
    with qbittorrentapi.Client(**conn_info) as qbt_client:
        # Выводим версию
        print(f"qBittorrent: {qbt_client.app.version}")

        # Получаем список всех торрентов
        print("\nСписок торрентов:")
        for torrent in qbt_client.torrents_info():
            # name - название, state - состояние (downloading, paused и т.д.)
            print(f"[{torrent.state}] {torrent.name} ({torrent.progress * 100:.1f}%)")

except qbittorrentapi.LoginFailed as e:
    print(f"Ошибка входа: {e}")
except Exception as e:
    print(f"Не удалось подключиться: {e}")
