import os
import json
from datetime import datetime
from team_utils import load_team_data_from_analysis, load_team_data_with_players
from analysis_utils import calculate_match_probabilities, get_detailed_analysis_str, get_forecasts_str

def process_all_matches(commands_dir: str = "commands") -> None:
    """Обработка всех матчей в папке commands"""
    
    print(f"🔍 Поиск матчей в папке: {commands_dir}")
    
    # Находим все папки с матчами
    match_folders = []
    for root, dirs, files in os.walk(commands_dir):
        for file in files:
            if file.endswith("_analysis.json"):
                match_folders.append(root)
                break
    
    print(f"📁 Найдено папок с матчами: {len(match_folders)}")
    
    if not match_folders:
        print("❌ Не найдены папки с матчами!")
        return
    
    # Файл для сохранения результатов
    output_file = f"all_matches_forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"📊 СВОДКА ПРОГНОЗОВ НА ВСЕ МАТЧИ\n")
        f.write(f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")
        
        total_matches = 0
        processed_matches = 0
        
        for match_folder in match_folders:
            analysis_files = [f for f in os.listdir(match_folder) if f.endswith("_analysis.json")]
            
            if not analysis_files:
                print(f"⚠️ В папке {match_folder} не найден файл анализа")
                continue
            
            analysis_file = analysis_files[0]
            analysis_path = os.path.join(match_folder, analysis_file)
            
            print(f"\n🔍 Обработка матча: {analysis_file}")
            
            try:
                with open(analysis_path, 'r', encoding='utf-8') as af:
                    match_data = json.load(af)
                
                total_matches += 1
                
                match_name = match_data.get("match", "Неизвестный матч")
                home_data = match_data.get("home_team", {})
                away_data = match_data.get("away_team", {})
                
                if not home_data or not away_data:
                    print(f"⚠️ Нет данных о командах в матче: {match_name}")
                    continue
                
                home_team_name = home_data.get("team_name", "Команда 1")
                away_team_name = away_data.get("team_name", "Команда 2")
                
                print(f"   Матч: {match_name}")
                print(f"   Домашняя: {home_team_name}")
                print(f"   Гостевая: {away_team_name}")
                
                home_res_file = os.path.join(match_folder, f"{home_team_name}_res.json")
                away_res_file = os.path.join(match_folder, f"{away_team_name}_res.json")
                
                if os.path.exists(home_res_file):
                    team1 = load_team_data_with_players(home_data, True, home_team_name, home_res_file)
                else:
                    team1 = load_team_data_from_analysis(home_data, True, home_team_name)
                    print(f"   ⚠️ Файл игроков для домашней команды не найден: {home_res_file}")
                
                if os.path.exists(away_res_file):
                    team2 = load_team_data_with_players(away_data, False, away_team_name, away_res_file)
                else:
                    team2 = load_team_data_from_analysis(away_data, False, away_team_name)
                    print(f"   ⚠️ Файл игроков для гостевой команды не найден: {away_res_file}")
                
                forecast = calculate_match_probabilities(
                    team1=team1,
                    team2=team2,
                    weather="sunny",
                    match_type="обычный"
                )
                
                analysis_str = get_detailed_analysis_str(forecast, team1, team2)
                forecasts_str = get_forecasts_str(forecast)
                
                f.write(f"\n🎯 МАТЧ: {match_name}\n")
                f.write(f"📅 Дата: {match_data.get('date_time', 'Неизвестно')}\n")
                f.write(f"🏆 Лига: {match_data.get('league', 'Неизвестно')}\n")
                f.write("-"*60 + "\n")
                f.write(analysis_str)
                f.write("\n")
                f.write(forecasts_str)
                f.write("\n" + "="*80 + "\n\n")
                
                processed_matches += 1
                print(f"   ✅ Обработан успешно")
                
            except Exception as e:
                print(f"   ❌ Ошибка обработки матча {analysis_file}: {e}")
                f.write(f"\n❌ ОШИБКА ОБРАБОТКИ МАТЧА: {analysis_file}\n")
                f.write(f"Ошибка: {str(e)}\n")
                f.write("="*80 + "\n\n")
    
    print(f"\n{'='*60}")
    print(f"📊 ОБРАБОТКА ЗАВЕРШЕНА")
    print(f"{'='*60}")
    print(f"Всего матчей найдено: {total_matches}")
    print(f"Успешно обработано: {processed_matches}")
    print(f"Результаты сохранены в: {output_file}")
    
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"📈 ИТОГОВАЯ СТАТИСТИКА\n")
        f.write(f"{'='*80}\n")
        f.write(f"Всего матчей найдено: {total_matches}\n")
        f.write(f"Успешно обработано: {processed_matches}\n")
        f.write(f"Дата генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == "__main__":
    print("="*60)
    print("🏆 АНАЛИЗАТОР ФУТБОЛЬНЫХ МАТЧЕЙ")
    print("="*60)
    process_all_matches("commands")