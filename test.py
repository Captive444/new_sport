import json
import logging
import os
from pathlib import Path
from typing import Dict

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlayerAnalyzer:
    """Класс для анализа данных игроков с учетом возраста и роста"""
    
    # Оптимальные параметры по позициям (рост в см, возраст)
    POSITION_STANDARDS = {
        'goalkeeper': {'optimal_height': (188, 198), 'optimal_age': (25, 32)},
        'defender': {'optimal_height': (180, 192), 'optimal_age': (24, 30)},
        'midfielder': {'optimal_height': (175, 185), 'optimal_age': (23, 28)},
        'forward': {'optimal_height': (178, 190), 'optimal_age': (24, 29)}
    }
    
    # Коэффициенты для расчетов
    AGE_FACTOR_BELOW = 0.02
    AGE_FACTOR_ABOVE = 0.03
    HEIGHT_FACTOR_BELOW = 0.02
    HEIGHT_FACTOR_ABOVE = 0.01
    
    DEFAULT_READINESS = {
        'goalkeeper': 0.4,
        'defender': 0.45,
        'midfielder': 0.45,
        'forward': 0.45
    }
    
    def __init__(self):
        self.position_weights = {
            'goalkeeper': {'conceded': 0.25, 'clean_sheets': 0.25, 'minutes': 0.2, 'discipline': 0.15, 'stability': 0.15},
            'defender': {'attack': 0.25, 'minutes': 0.25, 'discipline': 0.2, 'stability': 0.15, 'experience': 0.15},
            'midfielder': {'productivity': 0.3, 'minutes': 0.25, 'discipline': 0.2, 'activity': 0.15, 'experience': 0.1},
            'forward': {'efficiency': 0.35, 'accuracy': 0.25, 'minutes': 0.2, 'discipline': 0.15, 'experience': 0.05}
        }

    def safe_divide(self, numerator: float, denominator: float) -> float:
        """Безопасное деление с проверкой нуля"""
        return numerator / denominator if denominator != 0 else 0

    def normalize(self, value: float, max_value: float) -> float:
        """Нормализация значения к диапазону 0-1"""
        return min(max(value / max_value, 0), 1)

    def calculate_age_factor(self, age: int, position: str) -> float:
        """Рассчитывает возрастной коэффициент"""
        if not age:
            return 0.9  # Дефолтное значение если возраст неизвестен
            
        min_age, max_age = self.POSITION_STANDARDS[position]['optimal_age']
        
        if age < min_age:
            return 0.9 + (age - min_age) * self.AGE_FACTOR_BELOW
        elif age > max_age:
            return 1.0 - (age - max_age) * self.AGE_FACTOR_ABOVE
        else:
            return 1.0

    def calculate_height_factor(self, height: int, position: str) -> float:
        """Рассчитывает коэффициент роста"""
        if not height:
            return 0.95  # Дефолтное значение если рост неизвестен
            
        min_h, max_h = self.POSITION_STANDARDS[position]['optimal_height']
        
        if height < min_h:
            return 0.9 + (height - min_h) * self.HEIGHT_FACTOR_BELOW
        elif height > max_h:
            return 1.0 - (height - max_h) * self.HEIGHT_FACTOR_ABOVE
        else:
            return 1.0

    def calculate_position_readiness(self, position: str, metrics: Dict, age: int, height: int) -> float:
        """Общий метод для расчета готовности по позиции"""
        try:
            if position not in self.position_weights:
                logger.warning(f"Unknown position: {position}")
                return self.DEFAULT_READINESS.get(position, 0.45)
            
            base_readiness = sum(
                self.position_weights[position][key] * value 
                for key, value in metrics.items()
            )
            
            age_factor = self.calculate_age_factor(age, position)
            height_factor = self.calculate_height_factor(height, position)
            
            final_readiness = base_readiness * age_factor * height_factor
            
            # Ограничиваем значение между минимальным и максимальным
            return max(0.1, min(0.95, final_readiness))
            
        except Exception as e:
            logger.error(f"Error calculating {position} readiness: {e}", exc_info=True)
            return self.DEFAULT_READINESS.get(position, 0.45)

    def calculate_goalkeeper_readiness(self, stats: Dict, age: int, height: int) -> float:
        """Расчет готовности вратаря с учетом новых данных"""
        try:
            total_stats = stats.get('total_stats', {})
            matches = total_stats.get('total_matches', 0)
            
            if matches == 0:
                return self.DEFAULT_READINESS['goalkeeper']
            
            conceded = total_stats.get('total_goals_conceded', 0)
            clean_sheets = total_stats.get('total_clean_sheets', 0)
            minutes = total_stats.get('total_minutes_played', 0)
            cards = total_stats.get('total_yellow_cards', 0) + total_stats.get('total_red_cards', 0) * 2
            substitutions = total_stats.get('total_substitutions_out', 0)
            
            # Если минуты = 0, используем приблизительный расчет
            if minutes == 0:
                minutes = matches * 90  # Среднее 90 минут за матч
                logger.info(f"Estimated minutes: {matches} * 90 = {minutes}")
            
            metrics = {
                'conceded': 1 - self.normalize(conceded, matches * 2.5),
                'clean_sheets': self.normalize(clean_sheets, matches),
                'minutes': self.normalize(minutes, matches * 90),
                'discipline': 1 - self.normalize(cards, matches * 0.7),
                'stability': 1 - self.normalize(substitutions, matches * 0.5)
            }
            
            return self.calculate_position_readiness('goalkeeper', metrics, age, height)
            
        except Exception as e:
            logger.error(f"Error in goalkeeper readiness calculation: {e}", exc_info=True)
            return self.DEFAULT_READINESS['goalkeeper']

    def calculate_defender_readiness(self, stats: Dict, age: int, height: int) -> float:
        """Расчет готовности защитника с учетом новых данных"""
        try:
            total_stats = stats.get('total_stats', {})
            matches = total_stats.get('total_matches', 0)
            
            if matches == 0:
                return self.DEFAULT_READINESS['defender']
            
            goals = total_stats.get('total_goals', 0)
            assists = total_stats.get('total_assists', 0)
            minutes = total_stats.get('total_minutes_played', 0)
            cards = total_stats.get('total_yellow_cards', 0) + total_stats.get('total_red_cards', 0) * 2
            
            # Если минуты = 0, используем приблизительный расчет
            if minutes == 0:
                minutes = matches * 85  # Среднее 85 минут за матч для защитников
                logger.info(f"Estimated minutes: {matches} * 85 = {minutes}")
            
            # Для защитников используем упрощенную стабильность на основе замен
            substitutions_in = total_stats.get('total_substitutions_in', 0)
            substitutions_out = total_stats.get('total_substitutions_out', 0)
            stability = 1 - self.normalize(substitutions_out, matches * 0.7)
            
            metrics = {
                'attack': self.normalize(goals + assists, matches * 0.8),
                'minutes': self.normalize(minutes, matches * 90),
                'discipline': 1 - self.normalize(cards, matches * 0.6),
                'stability': stability,
                'experience': self.normalize(matches, 100)
            }
            
            return self.calculate_position_readiness('defender', metrics, age, height)
            
        except Exception as e:
            logger.error(f"Error in defender readiness calculation: {e}", exc_info=True)
            return self.DEFAULT_READINESS['defender']

    def calculate_midfielder_readiness(self, stats: Dict, age: int, height: int) -> float:
        """Расчет готовности полузащитника с учетом новых данных"""
        try:
            total_stats = stats.get('total_stats', {})
            matches = total_stats.get('total_matches', 0)
            
            if matches == 0:
                return self.DEFAULT_READINESS['midfielder']
            
            goals = total_stats.get('total_goals', 0)
            assists = total_stats.get('total_assists', 0)
            minutes = total_stats.get('total_minutes_played', 0)
            cards = total_stats.get('total_yellow_cards', 0) + total_stats.get('total_red_cards', 0) * 2
            
            # Если минуты = 0, используем приблизительный расчет
            if minutes == 0:
                minutes = matches * 80  # Среднее 80 минут за матч для полузащитников
                logger.info(f"Estimated minutes: {matches} * 80 = {minutes}")
            
            # Для полузащитников используем активность на основе замен
            substitutions_in = total_stats.get('total_substitutions_in', 0)
            substitutions_out = total_stats.get('total_substitutions_out', 0)
            activity = 1 - self.normalize(substitutions_out, matches * 0.8)
            
            metrics = {
                'productivity': self.normalize(goals * 1.5 + assists, matches * 0.7),
                'minutes': self.normalize(minutes, matches * 90),
                'discipline': 1 - self.normalize(cards, matches * 0.5),
                'activity': activity,
                'experience': self.normalize(matches, 100)
            }
            
            return self.calculate_position_readiness('midfielder', metrics, age, height)
            
        except Exception as e:
            logger.error(f"Error in midfielder readiness calculation: {e}", exc_info=True)
            return self.DEFAULT_READINESS['midfielder']

    def calculate_forward_readiness(self, stats: Dict, age: int, height: int) -> float:
        """Расчет готовности нападающего с учетом новых данных"""
        try:
            total_stats = stats.get('total_stats', {})
            matches = total_stats.get('total_matches', 0)
            
            if matches == 0:
                return self.DEFAULT_READINESS['forward']
            
            goals = total_stats.get('total_goals', 0)
            assists = total_stats.get('total_assists', 0)
            minutes = total_stats.get('total_minutes_played', 0)
            cards = total_stats.get('total_yellow_cards', 0) + total_stats.get('total_red_cards', 0) * 2
            
            # Если минуты = 0, используем приблизительный расчет
            if minutes == 0:
                minutes = matches * 75  # Среднее 75 минут за матч для нападающих
                logger.info(f"Estimated minutes: {matches} * 75 = {minutes}")
            
            # Для нападающих используем точность на основе голевых действий
            accuracy = self.normalize(goals + assists, matches * 1.2)
            
            metrics = {
                'efficiency': self.normalize(goals * 2, matches * 1.0),
                'accuracy': accuracy,
                'minutes': self.normalize(minutes, matches * 80),
                'discipline': 1 - self.normalize(cards, matches * 0.4),
                'experience': self.normalize(matches, 100)
            }
            
            return self.calculate_position_readiness('forward', metrics, age, height)
            
        except Exception as e:
            logger.error(f"Error in forward readiness calculation: {e}", exc_info=True)
            return self.DEFAULT_READINESS['forward']

    def calculate_player_readiness(self, player_data: Dict) -> float:
        """Основная функция расчета готовности"""
        try:
            if not player_data or not isinstance(player_data, dict):
                logger.warning("Invalid player data")
                return 0.45
                
            position = player_data.get('position', '').lower()
            stats = player_data.get('stats', {})
            age = player_data.get('age')
            height = player_data.get('height')
            
            if any(word in position for word in ['вратарь', 'gk', 'goalkeeper']):
                return self.calculate_goalkeeper_readiness(stats, age, height)
            elif any(word in position for word in ['защитник', 'defender']):
                return self.calculate_defender_readiness(stats, age, height)
            elif any(word in position for word in ['нап', 'вингер', 'forward']):
                return self.calculate_forward_readiness(stats, age, height)
            else:
                return self.calculate_midfielder_readiness(stats, age, height)
                
        except Exception as e:
            logger.error(f"Error calculating player readiness: {e}", exc_info=True)
            return 0.45

    def analyze_team(self, input_file: str, output_file: str = None) -> None:
        """Анализ одной команды с сохранением результатов"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                players = json.load(f)
                
            if not isinstance(players, list):
                logger.error(f"Input file {input_file} should contain a list of players")
                return
                
            results = []
            for player in players:
                try:
                    readiness = self.calculate_player_readiness(player)
                    results.append({
                        'name': player.get('name'),
                        'position': player.get('position'),
                        'readiness': readiness
                    })
                except Exception as e:
                    logger.error(f"Error processing player {player.get('name')}: {e}")
                    continue
            
            # Если output_file не указан, создаем автоматически
            if output_file is None:
                base_name = Path(input_file).stem  # Имя файла без расширения
                output_dir = Path(input_file).parent  # Директория файла
                output_file = str(output_dir / f"{base_name}_res.json")
                
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Результаты сохранены в {output_file}")
            
        except FileNotFoundError:
            logger.error(f"Файл не найден: {input_file}")
        except json.JSONDecodeError:
            logger.error(f"Ошибка чтения JSON из файла: {input_file}")
        except Exception as e:
            logger.error(f"Ошибка анализа команды: {e}", exc_info=True)

    def analyze_all_teams_in_folder(self, root_folder: str = "commands") -> None:
        """Рекурсивный анализ всех команд в папке и подпапках"""
        root_path = Path(root_folder)
        
        if not root_path.exists():
            logger.error(f"Папка не найдена: {root_folder}")
            return
        
        logger.info(f"Начинаю анализ всех команд в папке: {root_folder}")
        
        # Ищем все JSON файлы (кроме уже созданных _res.json)
        json_files = list(root_path.rglob("*.json"))
        
        # Фильтруем файлы, которые не являются результатами (_res.json)
        team_files = [f for f in json_files if not f.name.endswith("_res.json")]
        
        logger.info(f"Найдено {len(team_files)} файлов для анализа")
        
        for team_file in team_files:
            try:
                logger.info(f"Обработка файла: {team_file}")
                
                # Автоматически создаем имя для файла результатов
                output_file = team_file.with_name(f"{team_file.stem}_res.json")
                
                # Анализируем команду
                self.analyze_team(str(team_file), str(output_file))
                
                logger.info(f"Готово: {team_file.name} -> {output_file.name}")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке {team_file}: {e}", exc_info=True)
        
        logger.info(f"Анализ завершен. Обработано файлов: {len(team_files)}")

if __name__ == "__main__":
    analyzer = PlayerAnalyzer()
    
    # Вариант 1: Анализ всех команд в папке commands
    analyzer.analyze_all_teams_in_folder("commands")
    
    # Вариант 2: Анализ конкретной команды (старый вариант)
    # analyzer.analyze_team("commands/24-tk/Генчлербирлиги.json", "result.json")
    # Для отладочного вывода всей команды
    # analyzer.debug_team_readiness(input_file)

# import json
# import logging
# from typing import Dict

# def safe_divide(numerator: float, denominator: float) -> float:
#     """Безопасное деление с проверкой нуля и логированием"""
#     try:
#         return numerator / denominator if denominator != 0 else 0
#     except Exception as e:
#         logging.warning(f"Division error: {e} (numerator={numerator}, denominator={denominator})")
#         return 0

# def normalize(value: float, max_value: float) -> float:
#     """Нормализация значения к диапазону 0-1"""
#     return min(max(value / max_value, 0), 1)

# def calculate_goalkeeper_readiness(stats: Dict) -> float:
#     """Улучшенный расчет готовности вратаря"""
#     try:
#         total_stats = stats.get('total_stats', {})
#         matches = total_stats.get('total_matches', 0)
        
#         if matches == 0:
#             return 0.4  # Более консервативная оценка для новых игроков
        
#         # Основные показатели
#         conceded = total_stats.get('total_goals_conceded', 0)
#         clean_sheets = total_stats.get('total_clean_sheets', 0)
#         minutes = total_stats.get('total_minutes_played', 0)
        
#         # Дополнительные показатели
#         cards = total_stats.get('total_yellow_cards', 0) + total_stats.get('total_red_cards', 0) * 2
#         substitutions = total_stats.get('total_substitutions_out', 0)  # Частые замены могут указывать на проблемы
        
#         # Нормализованные метрики
#         conceded_norm = 1 - normalize(conceded, matches * 2.5)  # Норма до 2.5 голов за матч
#         clean_sheets_norm = normalize(clean_sheets, matches)
#         minutes_norm = normalize(minutes, matches * 90)
#         discipline = 1 - normalize(cards, matches * 0.7)  # Норма до 0.7 карточек за матч
#         stability = 1 - normalize(substitutions, matches * 0.5)  # Норма до 0.5 замен за матч
        
#         # Взвешенная формула
#         readiness = (
#             0.25 * conceded_norm +
#             0.25 * clean_sheets_norm +
#             0.20 * minutes_norm +
#             0.15 * discipline +
#             0.15 * stability
#         )
        
#         return max(0.1, min(0.95, readiness))  # Более узкий диапазон
    
#     except Exception as e:
#         logging.error(f"Error calculating goalkeeper readiness: {e}", exc_info=True)
#         return 0.45  # Среднее значение при ошибке

# def calculate_defender_readiness(stats: Dict) -> float:
#     """Улучшенный расчет готовности защитника"""
#     try:
#         total_stats = stats.get('total_stats', {})
#         matches = total_stats.get('total_matches', 0)
        
#         if matches == 0:
#             return 0.45
        
#         # Основные показатели
#         goals = total_stats.get('total_goals', 0)
#         assists = total_stats.get('total_assists', 0)
#         minutes = total_stats.get('total_minutes_played', 0)
        
#         # Дополнительные показатели
#         cards = total_stats.get('total_yellow_cards', 0) + total_stats.get('total_red_cards', 0) * 2
#         substitutions_out = total_stats.get('total_substitutions_out', 0)
#         own_goals = total_stats.get('total_own_goals', 0)
        
#         # Нормализованные метрики
#         attack_contribution = normalize(goals + assists * 0.5, matches * 0.5)  # Норма до 0.5 участий в голе за матч
#         minutes_norm = normalize(minutes, matches * 90)
#         discipline = 1 - normalize(cards, matches * 0.6)
#         stability = 1 - normalize(substitutions_out + own_goals * 2, matches * 0.6)
        
#         # Взвешенная формула
#         readiness = (
#             0.25 * attack_contribution +
#             0.25 * minutes_norm +
#             0.20 * discipline +
#             0.15 * stability +
#             0.15 * (1 if matches > 10 else 0.5)  # Бонус за опыт
#         )
        
#         return max(0.15, min(0.95, readiness))
    
#     except Exception as e:
#         logging.error(f"Error calculating defender readiness: {e}", exc_info=True)
#         return 0.45

# def calculate_midfielder_readiness(stats: Dict) -> float:
#     """Улучшенный расчет готовности полузащитника"""
#     try:
#         total_stats = stats.get('total_stats', {})
#         matches = total_stats.get('total_matches', 0)
        
#         if matches == 0:
#             return 0.45
        
#         # Основные показатели
#         goals = total_stats.get('total_goals', 0)
#         assists = total_stats.get('total_assists', 0)
#         minutes = total_stats.get('total_minutes_played', 0)
        
#         # Дополнительные показатели
#         cards = total_stats.get('total_yellow_cards', 0) + total_stats.get('total_red_cards', 0) * 2
#         substitutions_in = total_stats.get('total_substitutions_in', 0)
#         substitutions_out = total_stats.get('total_substitutions_out', 0)
        
#         # Нормализованные метрики
#         productivity = normalize(goals * 1.5 + assists, matches * 0.7)  # Голы ценятся больше
#         minutes_norm = normalize(minutes, matches * 90)
#         discipline = 1 - normalize(cards, matches * 0.5)
#         activity = 1 - normalize(substitutions_in + substitutions_out, matches * 1.2)
        
#         # Взвешенная формула
#         readiness = (
#             0.30 * productivity +
#             0.25 * minutes_norm +
#             0.20 * discipline +
#             0.15 * activity +
#             0.10 * (1 if matches > 15 else 0.6)  # Бонус за опыт
#         )
        
#         return max(0.15, min(0.95, readiness))
    
#     except Exception as e:
#         logging.error(f"Error calculating midfielder readiness: {e}", exc_info=True)
#         return 0.45

# def calculate_forward_readiness(stats: Dict) -> float:
#     """Улучшенный расчет готовности нападающего"""
#     try:
#         total_stats = stats.get('total_stats', {})
#         matches = total_stats.get('total_matches', 0)
        
#         if matches == 0:
#             return 0.45
        
#         # Основные показатели
#         goals = total_stats.get('total_goals', 0)
#         assists = total_stats.get('total_assists', 0)
#         minutes = total_stats.get('total_minutes_played', 0)
        
#         # Дополнительные показатели
#         cards = total_stats.get('total_yellow_cards', 0) + total_stats.get('total_red_cards', 0) * 2
#         shots_on_target = total_stats.get('total_shots_on_target', goals * 2)  # Примерная оценка, если данные отсутствуют
#         substitutions_out = total_stats.get('total_substitutions_out', 0)
        
#         # Нормализованные метрики
#         efficiency = normalize(goals * 2 + assists, matches * 1.2)
#         accuracy = normalize(shots_on_target, matches * 2) if shots_on_target > 0 else 0.5
#         minutes_norm = normalize(minutes, matches * 80)  # Нападающие могут чаще заменяться
#         discipline = 1 - normalize(cards, matches * 0.4)  # Более строгие требования к дисциплине
        
#         # Взвешенная формула
#         readiness = (
#             0.35 * efficiency +
#             0.25 * accuracy +
#             0.20 * minutes_norm +
#             0.15 * discipline +
#             0.05 * (1 if matches > 20 else 0.5)  # Меньший бонус за опыт
#         )
        
#         return max(0.2, min(0.95, readiness))  # Нападающие могут иметь более высокий разброс
    
#     except Exception as e:
#         logging.error(f"Error calculating forward readiness: {e}", exc_info=True)
#         return 0.45

# def calculate_player_readiness(player_data: Dict) -> float:
#     """Улучшенная основная функция расчета готовности игрока"""
#     try:
#         position = player_data.get('position', '').lower()
#         stats = player_data.get('stats', {})
        
#         # Улучшенное определение позиции
#         if any(word in position for word in ['вратарь', 'gk', 'goalkeeper']):
#             return calculate_goalkeeper_readiness(stats)
#         elif any(word in position for word in ['защитник', 'defender', 'центр. защитник', 'full-back']):
#             return calculate_defender_readiness(stats)
#         elif any(word in position for word in ['нап', 'вингер', 'forward', 'striker', 'winger']):
#             return calculate_forward_readiness(stats)
#         else:
#             # По умолчанию считаем полузащитником
#             return calculate_midfielder_readiness(stats)
    
#     except Exception as e:
#         logging.error(f"Error calculating player readiness: {e}", exc_info=True)
#         return 0.45

# def save_player_readiness_to_json(input_file: str, output_file: str) -> None:
#     """Сохранение готовности игроков в JSON файл с обработкой ошибок"""
#     try:
#         with open(input_file, 'r', encoding='utf-8') as f:
#             players_data = json.load(f)

#         results = []
#         for player in players_data:
#             readiness = calculate_player_readiness(player)
#             results.append({
#                 'name': player.get('name', 'Unknown'),
#                 'position': player.get('position', 'Unknown'),
#                 'readiness': readiness
#             })

#         with open(output_file, 'w', encoding='utf-8') as f:
#             json.dump(results, f, ensure_ascii=False, indent=4)
            
#     except Exception as e:
#         print(f"Error processing file: {e}")

# # Пример использования
# input_file = 'comands/Suwon FC.json'
# output_file = 'output_with_readiness_2.json'
# save_player_readiness_to_json(input_file, output_file)

# # для отладки

# # import json
# # import logging
# # from typing import Dict

# def safe_divide(numerator: float, denominator: float) -> float:
#     """Безопасное деление с проверкой нуля"""
#     try:
#         return numerator / denominator if denominator != 0 else 0
#     except Exception as e:
#         logging.warning(f"Division error: {e}")
#         return 0

# def normalize(value: float, max_value: float) -> float:
#     """Нормализация значения к диапазону 0-1"""
#     return min(max(value / max_value, 0), 1)

# def calculate_goalkeeper_readiness(stats: Dict) -> float:
#     """Расчет готовности вратаря"""
#     try:
#         total_stats = stats.get('total_stats', {})
#         matches = total_stats.get('total_matches', 0)
        
#         if matches == 0:
#             return 0.4
        
#         conceded = total_stats.get('total_goals_conceded', 0)
#         clean_sheets = total_stats.get('total_clean_sheets', 0)
#         minutes = total_stats.get('total_minutes_played', 0)
#         cards = total_stats.get('total_yellow_cards', 0) + total_stats.get('total_red_cards', 0) * 2
#         substitutions = total_stats.get('total_substitutions_out', 0)
        
#         conceded_norm = 1 - normalize(conceded, matches * 2.5)
#         clean_sheets_norm = normalize(clean_sheets, matches)
#         minutes_norm = normalize(minutes, matches * 90)
#         discipline = 1 - normalize(cards, matches * 0.7)
#         stability = 1 - normalize(substitutions, matches * 0.5)
        
#         readiness = (
#             0.25 * conceded_norm +
#             0.25 * clean_sheets_norm +
#             0.20 * minutes_norm +
#             0.15 * discipline +
#             0.15 * stability
#         )
        
#         return max(0.1, min(0.95, readiness))
    
#     except Exception as e:
#         logging.error(f"Error calculating goalkeeper readiness: {e}")
#         return 0.45

# def debug_player_readiness(player_data: Dict) -> None:
#     """Детальный вывод расчетов готовности игрока"""
#     try:
#         position = player_data.get('position', 'Unknown')
#         name = player_data.get('name', 'Unknown')
#         stats = player_data.get('stats', {}).get('total_stats', {})
#         matches = stats.get('total_matches', 0)
        
#         print(f"\n=== Детальный расчет для {name} ({position}) ===")
#         print(f"Всего матчей: {matches}")
        
#         if matches == 0:
#             print("Возвращаем значение по умолчанию: 0.4" if 'вратарь' in position.lower() else "Возвращаем значение по умолчанию: 0.45")
#             return
        
#         if 'вратарь' in position.lower():
#             print("\nРасчет для вратаря:")
#             conceded = stats.get('total_goals_conceded', 0)
#             clean_sheets = stats.get('total_clean_sheets', 0)
#             minutes = stats.get('total_minutes_played', 0)
#             cards = stats.get('total_yellow_cards', 0) + stats.get('total_red_cards', 0) * 2
#             substitutions = stats.get('total_substitutions_out', 0)
            
#             print(f"Пропущено голов: {conceded} ({safe_divide(conceded, matches):.2f} за матч)")
#             print(f"Сухие матчи: {clean_sheets} ({safe_divide(clean_sheets, matches):.2f} за матч)")
#             print(f"Минуты: {minutes} ({safe_divide(minutes, matches):.2f} за матч)")
#             print(f"Карточки: {cards} ({safe_divide(cards, matches):.2f} за матч)")
#             print(f"Замены: {substitutions} ({safe_divide(substitutions, matches):.2f} за матч)")
            
#             conceded_norm = 1 - normalize(conceded, matches * 2.5)
#             clean_sheets_norm = normalize(clean_sheets, matches)
#             minutes_norm = normalize(minutes, matches * 90)
#             discipline = 1 - normalize(cards, matches * 0.7)
#             stability = 1 - normalize(substitutions, matches * 0.5)
            
#             print("\nНормализованные показатели:")
#             print(f"Пропущенные голы: {conceded_norm:.3f}")
#             print(f"Сухие матчи: {clean_sheets_norm:.3f}")
#             print(f"Минуты: {minutes_norm:.3f}")
#             print(f"Дисциплина: {discipline:.3f}")
#             print(f"Стабильность: {stability:.3f}")
            
#             readiness = (
#                 0.25 * conceded_norm +
#                 0.25 * clean_sheets_norm +
#                 0.20 * minutes_norm +
#                 0.15 * discipline +
#                 0.15 * stability
#             )
            
#             print("\nИтоговый расчет:")
#             print(f"0.25 * {conceded_norm:.3f} = {0.25 * conceded_norm:.3f}")
#             print(f"0.25 * {clean_sheets_norm:.3f} = {0.25 * clean_sheets_norm:.3f}")
#             print(f"0.20 * {minutes_norm:.3f} = {0.20 * minutes_norm:.3f}")
#             print(f"0.15 * {discipline:.3f} = {0.15 * discipline:.3f}")
#             print(f"0.15 * {stability:.3f} = {0.15 * stability:.3f}")
#             print(f"Сумма: {readiness:.3f}")
        
#         final_readiness = calculate_goalkeeper_readiness(player_data.get('stats', {}))
#         print(f"\nФинальный показатель готовности: {final_readiness:.3f}")
        
#     except Exception as e:
#         print(f"Ошибка при отладке: {e}")

# def debug_team_readiness(input_file: str) -> None:
#     """Отладочный вывод для всех игроков команды"""
#     try:
#         with open(input_file, 'r', encoding='utf-8') as f:
#             players = json.load(f)
            
#         for player in players:
#             debug_player_readiness(player)
#             print("\n" + "="*50 + "\n")
            
#     except Exception as e:
#         print(f"Ошибка загрузки файла: {e}")

# if __name__ == "__main__":
#     # Пример использования
#     input_file = 'comands/Suwon FC.json'  # Укажите ваш путь к файлу
    
#     # Для отладки всей команды
#     debug_team_readiness(input_file)
    




# 777777777777777777777





    # Для отладки одного игрока (пример)
    # test_player = {
    #     "name": "Test Player",
    #     "position": "Вратарь",
    #     "stats": {
    #         "total_stats": {
    #             "total_matches": 10,
    #             "total_goals_conceded": 12,
    #             "total_clean_sheets": 3,
    #             "total_minutes_played": 900,
    #             "total_yellow_cards": 2,
    #             "total_red_cards": 0,
    #             "total_substitutions_out": 1
    #         }
    #     }
    # }
    # debug_player_readiness(test_player)

# 002


# import json
# from typing import Dict, List

# def safe_divide(numerator: float, denominator: float) -> float:
#     """Безопасное деление с проверкой нуля"""
#     return numerator / denominator if denominator != 0 else 0

# # def calculate_goalkeeper_readiness(stats: Dict) -> float:
# #     """Расчет готовности вратаря с проверкой всех ключей"""
# #     try:
# #         total_stats = stats.get('total_stats', {})
# #         matches = total_stats.get('total_matches', 0)
# #         if matches == 0:
# #             return 0.5
        
# #         conceded = total_stats.get('total_goals_conceded', 0)
# #         clean_sheets = total_stats.get('total_clean_sheets', 0)
# #         minutes = total_stats.get('total_minutes_played', 0)
        
# #         conceded_per_match = safe_divide(conceded, matches)
# #         clean_sheets_ratio = safe_divide(clean_sheets, matches)
# #         minutes_ratio = safe_divide(minutes, matches * 90)
        
# #         readiness = (
# #             0.4 * (1 - min(conceded_per_match / 3, 1)) +
# #             0.3 * clean_sheets_ratio +
# #             0.3 * min(minutes_ratio, 1)
# #         )
# #         return max(0.1, min(0.99, readiness))
    
# #     except Exception as e:
# #         print(f"Error calculating goalkeeper readiness: {e}")
# #         return 0.5


# # формула обнавленная для вратаря

# def calculate_goalkeeper_readiness(stats: Dict) -> float:
#     """Улучшенный расчет готовности вратаря"""
#     try:
#         total_stats = stats.get('total_stats', {})
#         matches = total_stats.get('total_matches', 0)
        
#         if matches == 0:
#             return 0.5  # или рассмотреть другие факторы
        
#         conceded = total_stats.get('total_goals_conceded', 0)
#         clean_sheets = total_stats.get('total_clean_sheets', 0)
#         minutes = total_stats.get('total_minutes_played', 0)
#         cards = total_stats.get('total_yellow_cards', 0) + total_stats.get('total_red_cards', 0) * 2
        
#         # Нормализация показателей
#         conceded_per_match = safe_divide(conceded, matches)
#         clean_sheets_ratio = safe_divide(clean_sheets, matches)
#         minutes_ratio = safe_divide(minutes, matches * 90)
#         discipline = 1 - min(cards / (matches * 0.7), 1)  # Нормализация количества карточек
        
#         # Взвешенная формула
#         readiness = (
#             0.3 * (1 - min(conceded_per_match / 3, 1)) +  # Меньший вес на пропущенные голы
#             0.3 * clean_sheets_ratio +
#             0.2 * min(minutes_ratio, 1) +
#             0.2 * discipline  # Учет дисциплины
#         )
        
#         return max(0.1, min(0.99, readiness))
    
#     except Exception as e:
#         logging.error(f"Error calculating goalkeeper readiness: {e}", exc_info=True)
#         return 0.5

#         # конец

# def calculate_defender_readiness(stats: Dict) -> float:
#     """Расчет готовности защитника с проверкой всех ключей"""
#     try:
#         total_stats = stats.get('total_stats', {})
#         matches = total_stats.get('total_matches', 0)
#         if matches == 0:
#             return 0.5
        
#         goals = safe_divide(total_stats.get('total_goals', 0), matches)
#         assists = safe_divide(total_stats.get('total_assists', 0), matches)
#         yellow_cards = safe_divide(total_stats.get('total_yellow_cards', 0), matches)
#         minutes = safe_divide(total_stats.get('total_minutes_played', 0), matches * 90)
        
#         readiness = (
#             0.3 * goals +
#             0.2 * assists +
#             0.2 * (1 - min(yellow_cards / 0.5, 1)) +
#             0.3 * min(minutes, 1)
#         )
#         return max(0.1, min(0.99, readiness))
    
#     except Exception as e:
#         print(f"Error calculating defender readiness: {e}")
#         return 0.5

# def calculate_forward_readiness(stats: Dict) -> float:
#     """Расчет готовности нападающего с проверкой всех ключей"""
#     try:
#         total_stats = stats.get('total_stats', {})
#         matches = total_stats.get('total_matches', 0)
#         if matches == 0:
#             return 0.5
        
#         goals = safe_divide(total_stats.get('total_goals', 0), matches)
#         assists = safe_divide(total_stats.get('total_assists', 0), matches)
#         yellow_cards = safe_divide(total_stats.get('total_yellow_cards', 0), matches)
#         minutes = safe_divide(total_stats.get('total_minutes_played', 0), matches * 90)
        
#         readiness = (
#             0.5 * goals +
#             0.3 * assists +
#             0.1 * (1 - min(yellow_cards / 0.5, 1)) +
#             0.1 * min(minutes, 1)
#         )
#         return max(0.1, min(0.99, readiness))
    
#     except Exception as e:
#         print(f"Error calculating forward readiness: {e}")
#         return 0.5

# def calculate_player_readiness(player_data: Dict) -> float:
#     """Основная функция расчета готовности игрока с обработкой ошибок"""
#     try:
#         position = player_data.get('position', '').lower()
#         stats = player_data.get('stats', {})
        
#         if 'вратарь' in position:
#             return calculate_goalkeeper_readiness(stats)
#         elif 'защитник' in position:
#             return calculate_defender_readiness(stats)
#         elif 'нап' in position or 'вингер' in position:
#             return calculate_forward_readiness(stats)
#         else:
#             # Для полузащитников и других позиций
#             total_stats = stats.get('total_stats', {})
#             matches = total_stats.get('total_matches', 0)
#             if matches == 0:
#                 return 0.5
                
#             goals = safe_divide(total_stats.get('total_goals', 0), matches)
#             assists = safe_divide(total_stats.get('total_assists', 0), matches)
#             yellow_cards = safe_divide(total_stats.get('total_yellow_cards', 0), matches)
#             minutes = safe_divide(total_stats.get('total_minutes_played', 0), matches * 90)
            
#             readiness = (
#                 0.4 * goals +
#                 0.3 * assists +
#                 0.1 * (1 - min(yellow_cards / 0.5, 1)) +
#                 0.2 * min(minutes, 1)
#             )
#             return max(0.1, min(0.99, readiness))
    
#     except Exception as e:
#         print(f"Error calculating player readiness: {e}")
#         return 0.5

# def save_player_readiness_to_json(input_file: str, output_file: str) -> None:
#     """Сохранение готовности игроков в JSON файл с обработкой ошибок"""
#     try:
#         with open(input_file, 'r', encoding='utf-8') as f:
#             players_data = json.load(f)

#         results = []
#         for player in players_data:
#             readiness = calculate_player_readiness(player)
#             results.append({
#                 'name': player.get('name', 'Unknown'),
#                 'position': player.get('position', 'Unknown'),
#                 'readiness': readiness
#             })

#         with open(output_file, 'w', encoding='utf-8') as f:
#             json.dump(results, f, ensure_ascii=False, indent=4)
            
#     except Exception as e:
#         print(f"Error processing file: {e}")

# # Пример использования
# input_file = 'comands/Ulsan HD.json'
# output_file = 'output_with_readiness_1.json'
# save_player_readiness_to_json(input_file, output_file)


# 01111


# import json
# from typing import List, Dict

# def calculate_goalkeeper_readiness(stats: Dict) -> float:
#     """Расчет готовности вратаря"""
#     matches = stats['total_stats']['total_matches']
#     if matches == 0:
#         return 0.5  # нейтральное значение при отсутствии данных
    
#     conceded_per_match = stats['total_stats']['total_goals_conceded'] / matches
#     clean_sheets_ratio = stats['total_stats']['total_clean_sheets'] / matches
#     minutes_ratio = stats['total_stats']['total_minutes_played'] / (matches * 90)
    
#     # Формула для вратаря
#     readiness = (
#         0.4 * (1 - min(conceded_per_match / 3, 1)) +  # Нормируем на 3 гола за матч как максимум
#         0.3 * clean_sheets_ratio +
#         0.3 * min(minutes_ratio, 1)
#     )
#     return max(0, min(1, readiness))  # Ограничиваем от 0 до 1

# def calculate_defender_readiness(stats: Dict) -> float:
#     """Расчет готовности защитника"""
#     matches = stats['total_stats']['total_matches']
#     if matches == 0:
#         return 0.5
    
#     goals = stats['total_stats']['total_goals'] / matches
#     assists = stats['total_stats']['total_assists'] / matches
#     yellow_cards = stats['total_stats']['total_yellow_cards'] / matches
#     minutes_ratio = stats['total_stats']['total_minutes_played'] / (matches * 90)
    
#     readiness = (
#         0.3 * goals +
#         0.2 * assists +
#         0.2 * (1 - min(yellow_cards / 0.5, 1)) +  # Нормируем на 0.5 желтых карточек за матч
#         0.3 * min(minutes_ratio, 1)
#     )
#     return max(0, min(1, readiness))

# def calculate_forward_readiness(stats: Dict) -> float:
#     """Расчет готовности нападающего"""
#     matches = stats['total_stats']['total_matches']
#     if matches == 0:
#         return 0.5
    
#     goals = stats['total_stats']['total_goals'] / matches
#     assists = stats['total_stats']['total_assists'] / matches
#     yellow_cards = stats['total_stats']['total_yellow_cards'] / matches
#     minutes_ratio = stats['total_stats']['total_minutes_played'] / (matches * 90)
    
#     readiness = (
#         0.5 * goals +
#         0.3 * assists +
#         0.1 * (1 - min(yellow_cards / 0.5, 1)) +
#         0.1 * min(minutes_ratio, 1)
#     )
#     return max(0, min(1, readiness))

# def calculate_player_readiness(player_data: Dict) -> float:
#     """Основная функция расчета готовности игрока"""
#     position = player_data['position']
#     stats = player_data['stats']
    
#     if 'вратарь' in position.lower():
#         return calculate_goalkeeper_readiness(stats)
#     elif 'защитник' in position.lower():
#         return calculate_defender_readiness(stats)
#     elif 'нап' in position.lower() or 'вингер' in position.lower():
#         return calculate_forward_readiness(stats)
#     else:
#         # Для полузащитников и других позиций используем усредненную формулу
#         matches = stats['total_stats']['total_matches']
#         if matches == 0:
#             return 0.5
            
#         goals = stats['total_stats']['total_goals'] / matches
#         assists = stats['total_stats']['total_assists'] / matches
#         yellow_cards = stats['total_stats']['total_yellow_cards'] / matches
#         minutes_ratio = stats['total_stats']['total_minutes_played'] / (matches * 90)
        
#         readiness = (
#             0.4 * goals +
#             0.3 * assists +
#             0.1 * (1 - min(yellow_cards / 0.5, 1)) +
#             0.2 * min(minutes_ratio, 1)
#         )
#         return max(0, min(1, readiness))

# def save_player_readiness_to_json(input_file: str, output_file: str) -> None:
#     """Сохранение готовности игроков в JSON файл"""
#     with open(input_file, 'r', encoding='utf-8') as f:
#         players_data = json.load(f)

#     results = []
#     for player in players_data:
#         readiness = calculate_player_readiness(player)
#         results.append({
#             'name': player['name'],
#             'position': player['position'],
#             'readiness': readiness
#         })

#     # Сохраняем результаты в новый JSON файл
#     with open(output_file, 'w', encoding='utf-8') as f:
#         json.dump(results, f, ensure_ascii=False, indent=4)

# # Пример использования
# input_file = 'comands/plus_3.json'
# output_file = 'output_with_readiness_1.json'
# save_player_readiness_to_json(input_file, output_file)
