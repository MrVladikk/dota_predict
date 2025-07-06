# Код для файла get_data.py (версия для сбора большого количества данных)
import requests
import time
import json
import os

# --- НАСТРОЙКИ ---
# Сколько "страниц" по 100 матчей мы хотим скачать?
# 5 = ~500 матчей
# 10 = ~1000 матчей
# 20 = ~2000 матчей (рекомендуется для хорошей базы)
PAGES_TO_FETCH = 20
OUTPUT_FILENAME = 'dota_matches_data.json'
# ------------------


def get_data():
    all_matches_data = []
    last_match_id = None

    print(f"Начинаем сбор данных. Цель: скачать {PAGES_TO_FETCH} страниц (~{PAGES_TO_FETCH*100} матчей).")
    print("Это займет значительное время...")

    for i in range(PAGES_TO_FETCH):
        # Формируем URL. Для первой страницы он будет без параметра, для следующих - с less_than_match_id
        url = "https://api.opendota.com/api/proMatches"
        if last_match_id:
            url += f"?less_than_match_id={last_match_id}"
        
        try:
            print(f"\n--- Загрузка страницы {i + 1}/{PAGES_TO_FETCH} ---")
            response = requests.get(url)
            response.raise_for_status()
            current_page_matches = response.json()

            if not current_page_matches:
                print("Достигнут конец истории матчей. Завершаем сбор.")
                break
            
            # Сохраняем ID последнего матча на странице, чтобы запросить следующую порцию
            last_match_id = current_page_matches[-1]['match_id']

            # Собираем детальную информацию по каждому матчу на странице
            for j, match_summary in enumerate(current_page_matches):
                match_id = match_summary['match_id']
                try:
                    detail_response = requests.get(f"https://api.opendota.com/api/matches/{match_id}")
                    detail_response.raise_for_status()
                    all_matches_data.append(detail_response.json())
                    print(f"Страница {i + 1}: Обработан матч {j + 1}/{len(current_page_matches)} (ID: {match_id})")
                    time.sleep(1.1) # Обязательная пауза, чтобы не заблокировали
                except requests.exceptions.RequestException as e:
                    print(f"Пропущена ошибка при получении деталей матча {match_id}: {e}")
                except json.JSONDecodeError:
                    print(f"Пропущена ошибка декодирования для матча {match_id}")

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при загрузке страницы {i + 1}: {e}")
            print("Прерываем сбор. Сохраняем то, что успели скачать.")
            break
    
    # Сохраняем все собранные данные в файл
    if all_matches_data:
        print(f"\nСбор данных завершен. Собрано {len(all_matches_data)} матчей.")
        print(f"Сохранение в файл '{OUTPUT_FILENAME}'...")
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(all_matches_data, f, ensure_ascii=False, indent=4)
        print("Данные успешно сохранены!")
    else:
        print("\nНе удалось собрать данные.")


# --- Основная часть скрипта ---
if __name__ == "__main__":
    # Перед запуском спрашиваем пользователя, чтобы он не удалил данные случайно
    if os.path.exists(OUTPUT_FILENAME):
        answer = input(f"Файл '{OUTPUT_FILENAME}' уже существует. Перезаписать его новыми данными? (y/n): ").lower()
        if answer == 'y':
            get_data()
        else:
            print("Отмена операции.")
    else:
        get_data()