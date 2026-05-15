import sys
import os

from updater import BotUpdater, UpdateStatus
import config

sys.path.append(os.path.dirname(__file__))


def main():
    updater = BotUpdater(
        repo_owner="LegoManchik",
        repo_name="PPV.voice",
        current_version=config.BOT_VERSION,
        branch="1.0",
        blacklist=open("blacklist.txt").read().split('\n')
    )

    print("Проверка обновлений...")
    update_info = updater.check_for_updates()

    if update_info.status == UpdateStatus.UPDATE_AVAILABLE:
        print(f"Доступна версия {update_info.latest_version}")
        print(update_info.changelog)

        response = input("Установить обновление? (y/n): ")
        if response.lower() == 'y':
            print("Устанавливаю обновление...")
            if updater.download_and_update():
                print("Обновление успешно! Перезапустите бота.")
                updater.restart_bot()
            else:
                print("Ошибка при обновлении!")
    else:
        print(update_info.message)


if __name__ == "__main__":
    main()