# Код для файла predict_pro_teams.py (ИСПРАВЛЕННАЯ версия 2.0)

import requests
import pandas as pd
import time
import json
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import os

def main():
    print("--- ЗАПУСК ПРОГРАММЫ ПРОГНОЗИРОВАНИЯ ---")

    if not os.path.exists('dota_matches_data.json'):
        print("\nОШИБКА: Файл с данными 'dota_matches_data.json' не найден.")
        print("Пожалуйста, сначала запустите скрипт 'get_data.py', чтобы скачать данные.")
        return

    print("\nШаг 1: Загрузка данных...")
    try:
        teams_response = requests.get("https://api.opendota.com/api/teams")
        teams_data = teams_response.json()
        team_id_map = {team['team_id']: team['name'] for team in teams_data if isinstance(team, dict) and team.get('name')}
        team_name_map = {team['name'].lower(): team['team_id'] for team in teams_data if isinstance(team, dict) and team.get('name')}

        heroes_response = requests.get("https://api.opendota.com/api/heroes")
        heroes_data = heroes_response.json()
        
        # ИЗМЕНЕНИЕ ЗДЕСЬ: Добавлена проверка для списка героев
        hero_id_map = {
            hero['id']: hero['localized_name'] 
            for hero in heroes_data 
            if isinstance(hero, dict) and hero.get('id') and hero.get('localized_name')
        }

        with open('dota_matches_data.json', 'r', encoding='utf-8') as f:
            matches_data = json.load(f)
        print("Данные успешно загружены.")
    except Exception as e:
        print(f"ОШИБКА при загрузке данных: {e}")
        return

    print("\nШаг 2: Обработка матчей и создание признаков...")
    # ... (остальной код остается без изменений) ...
    parsed_matches = []
    for match in matches_data:
        if not all(k in match for k in ['picks_bans', 'radiant_team', 'dire_team', 'radiant_win']):
            continue
        if not match.get('radiant_team') or not match.get('dire_team'):
            continue

        radiant_picks = [pb['hero_id'] for pb in match['picks_bans'] if pb['is_pick'] and pb['team'] == 0]
        dire_picks = [pb['hero_id'] for pb in match['picks_bans'] if pb['is_pick'] and pb['team'] == 1]
        
        if len(radiant_picks) != 5 or len(dire_picks) != 5:
            continue
            
        row = {
            'match_id': match['match_id'],
            'radiant_win': 1 if match['radiant_win'] else 0,
            'radiant_team_id': match['radiant_team'].get('team_id'),
            'dire_team_id': match['dire_team'].get('team_id'),
            'radiant_picks': radiant_picks,
            'dire_picks': dire_picks
        }
        parsed_matches.append(row)

    df = pd.DataFrame(parsed_matches).dropna(subset=['radiant_team_id', 'dire_team_id'])
    
    # Пропускаем создание признаков для героев, которых нет в нашей карте
    valid_hero_ids = hero_id_map.keys()
    for hero_id in valid_hero_ids:
        df[f'hero_{hero_id}_radiant'] = df['radiant_picks'].apply(lambda p: 1 if hero_id in p else 0)
        df[f'hero_{hero_id}_dire'] = df['dire_picks'].apply(lambda p: 1 if hero_id in p else 0)

    df['radiant_team'] = df['radiant_team_id']
    df['dire_team'] = df['dire_team_id']
    
    team_matches = {}
    for index, row in df.iterrows():
        rad_id, dire_id = row['radiant_team_id'], row['dire_team_id']
        if rad_id not in team_matches: team_matches[rad_id] = []
        if dire_id not in team_matches: team_matches[dire_id] = []
        team_matches[rad_id].append(row['radiant_win'] == 1)
        team_matches[dire_id].append(row['radiant_win'] == 0)

    team_winrates = {team_id: sum(results) / len(results) for team_id, results in team_matches.items() if results}
    df['radiant_winrate'] = df['radiant_team_id'].map(team_winrates).fillna(0.5)
    df['dire_winrate'] = df['dire_team_id'].map(team_winrates).fillna(0.5)
    
    df_final = df.drop(columns=['match_id', 'radiant_team_id', 'dire_team_id', 'radiant_picks', 'dire_picks'])
    print("Обработка завершена.")
    
    if df_final.empty:
        print("ОШИБКА: Недостаточно данных для обучения. Попробуйте собрать больше матчей.")
        return

    print("\nШаг 3: Обучение модели машинного обучения...")
    X = df_final.drop('radiant_win', axis=1)
    y = df_final['radiant_win']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=150, random_state=42)
    model.fit(X_train, y_train)
    
    accuracy = model.score(X_test, y_test)
    print(f"Модель обучена! Точность на тестовых данных: {accuracy * 100:.2f}%")
    
    print("\n" + "="*40)
    print("    ИНТЕРФЕЙС ПРОГНОЗИРОВАНИЯ МАТЧЕЙ")
    print("="*40)

    while True:
        print("\nВведите данные для нового прогноза (или нажмите Ctrl+C для выхода).")
        
        team_1 = input("Введите название первой команды (Radiant): ")
        team_2 = input("Введите название второй команды (Dire): ")
        
        radiant_heroes_str = input("Герои Radiant через запятую (оставьте пустым, если неизвестно): ")
        dire_heroes_str = input("Герои Dire через запятую (оставьте пустым, если неизвестно): ")
        
        radiant_heroes = [hero.strip().title() for hero in radiant_heroes_str.split(',') if hero.strip()]
        dire_heroes = [hero.strip().title() for hero in dire_heroes_str.split(',') if hero.strip()]

        team1_id = team_name_map.get(team_1.lower())
        team2_id = team_name_map.get(team_2.lower())

        if not team1_id:
            print(f"\n[!] ОШИБКА: Команда '{team_1}' не найдена в базе данных!")
            continue
        if not team2_id:
            print(f"\n[!] ОШИБКА: Команда '{team_2}' не найдена в базе данных!")
            continue

        hero_name_to_id = {name.lower(): id for id, name in hero_id_map.items()}
        try:
            radiant_hero_ids = [hero_name_to_id[name.lower()] for name in radiant_heroes]
            dire_hero_ids = [hero_name_to_id[name.lower()] for name in dire_heroes]
        except KeyError as e:
            print(f"\n[!] ОШИБКА: Герой с именем {e} не найден! Проверьте правильность написания.")
            continue
            
        input_row = pd.Series(0, index=X.columns)
        input_row['radiant_team'] = team1_id
        input_row['dire_team'] = team2_id
        input_row['radiant_winrate'] = team_winrates.get(team1_id, 0.5)
        input_row['dire_winrate'] = team_winrates.get(team2_id, 0.5)

        # Проверяем наличие колонки перед записью
        for hero_id in radiant_hero_ids:
            col_name = f'hero_{hero_id}_radiant'
            if col_name in input_row.index:
                input_row[col_name] = 1
        for hero_id in dire_hero_ids:
            col_name = f'hero_{hero_id}_dire'
            if col_name in input_row.index:
                input_row[col_name] = 1

        input_df = pd.DataFrame([input_row])
        prediction_proba = model.predict_proba(input_df)[0]
        radiant_win_chance = prediction_proba[1] 
        
        print("\n" + "—"*20 + " РЕЗУЛЬТАТ " + "—"*20)
        print(f"Команда 1 (Radiant): {team_1.title()}")
        print(f"Команда 2 (Dire): {team_2.title()}")
        print("-" * 50)
        print(f"===> Шанс на победу {team_1.title()}: {radiant_win_chance * 100:.2f}%")
        print(f"===> Шанс на победу {team_2.title()}: {(1 - radiant_win_chance) * 100:.2f}%")
        print("—" * 50)


if __name__ == "__main__":
    main()