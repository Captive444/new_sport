import json
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from math import exp, factorial
import math
import re

@dataclass
class CardStats:
    """Статистика карточек игрока"""
    yellow_cards_per_90: float
    red_cards_per_90: float
    fouls_per_90: float
    aggression_factor: float

class CardPredictor:
    def __init__(self):
        # Увеличенные коэффициенты влияния позиции на карточки
        self.position_factors = {
            "вратарь": {"yellow": 0.2, "red": 0.02, "fouls": 0.3},
            "центр. защитник": {"yellow": 1.8, "red": 0.5, "fouls": 1.5},
            "левый защитник": {"yellow": 1.5, "red": 0.3, "fouls": 1.2},
            "правый защитник": {"yellow": 1.5, "red": 0.3, "fouls": 1.2},
            "опорный полузащитник": {"yellow": 2.0, "red": 0.6, "fouls": 1.8},
            "центр. полузащитник": {"yellow": 1.2, "red": 0.25, "fouls": 1.0},
            "атак. полузащитник": {"yellow": 0.9, "red": 0.15, "fouls": 0.8},
            "левый вингер": {"yellow": 1.0, "red": 0.18, "fouls": 0.9},
            "правый вингер": {"yellow": 1.0, "red": 0.18, "fouls": 0.9},
            "центральный нап.": {"yellow": 0.7, "red": 0.12, "fouls": 0.6}
        }
        
        # Факторы важности матча
        self.match_importance = {
            "дерби": 1.6,
            "вылет": 1.4,
            "еврокубки": 1.3,
            "кубок": 1.2,
            "обычный": 1.0
        }
        
        # Влияние готовности на агрессивность
        self.readiness_impact = {
            "very_low": 1.5,  # < 0.3
            "low": 1.3,       # 0.3-0.5
            "medium": 1.0,    # 0.5-0.7
            "high": 0.7,      # 0.7-0.9
            "very_high": 0.5  # > 0.9
        }
        
        # Базовые показатели карточек для лиги
        self.league_baseline = {
            "yellow_per_game": 3.5,  # Среднее желтых карточек за матч
            "red_per_game": 0.3,     # Среднее красных карточек за матч
        }
    
    def clean_name(self, name: str) -> str:
        """Очистка имени от лишних символов и номеров"""
        cleaned = re.sub(r'^#\d+\s*', '', name)
        cleaned = re.sub(r'[^\w\s]', '', cleaned)
        return cleaned.strip().lower()
    
    def estimate_minutes_played(self, player_data: Dict) -> int:
        """Оценка сыгранных минут на основе количества матчей"""
        total_stats = player_data['stats']['total_stats']
        total_matches = total_stats.get('total_matches', 0)
        
        if total_stats.get('total_minutes_played', 0) > 0:
            return total_stats['total_minutes_played']
        
        # Более реалистичная оценка минут
        if total_matches > 0:
            # Для игроков с матчами - предполагаем 70 минут в среднем
            estimated_minutes = total_matches * 70
        else:
            # Для новых игроков - базовое значение
            estimated_minutes = 90
            
        return max(estimated_minutes, 90)
    
    def calculate_player_card_stats(self, player_data: Dict, minutes_played_threshold: int = 45) -> Optional[CardStats]:
        """Расчет статистики карточек для игрока"""
        if not player_data.get('stats') or not player_data['stats'].get('total_stats'):
            return None
        
        total_stats = player_data['stats']['total_stats']
        total_minutes = self.estimate_minutes_played(player_data)
        
        if total_minutes < minutes_played_threshold:
            return None
        
        # Расчет показателей на 90 минут
        yellow_cards = total_stats.get('total_yellow_cards', 0)
        red_cards = total_stats.get('total_red_cards', 0)
        
        # Добавляем сглаживание для избежания деления на ноль
        yellow_per_90 = (yellow_cards / total_minutes) * 90
        red_per_90 = (red_cards / total_minutes) * 90
        
        # Более агрессивная оценка агрессивности
        aggression = (yellow_per_90 * 0.8 + red_per_90 * 3.0) * 1.2
        
        return CardStats(
            yellow_cards_per_90=max(yellow_per_90, 0.05),  # Минимальное значение
            red_cards_per_90=max(red_per_90, 0.005),       # Минимальное значение
            fouls_per_90=aggression * 1.5,
            aggression_factor=aggression
        )
    
    def get_readiness_category(self, readiness: float) -> str:
        """Категоризация готовности"""
        if readiness < 0.3: return "very_low"
        elif readiness < 0.5: return "low"
        elif readiness < 0.7: return "medium"
        elif readiness < 0.9: return "high"
        else: return "very_high"
    
    def predict_player_cards(self, player_data: Dict, player_readiness: float, 
                           match_type: str = "обычный", is_home: bool = True) -> Dict:
        """Прогноз карточек для конкретного игрока"""
        position = player_data['position'].lower()
        
        # Базовые факторы
        pos_factors = self.position_factors.get(position, self.position_factors["центр. полузащитник"])
        importance_factor = self.match_importance.get(match_type, 1.0)
        
        # Влияние готовности
        readiness_cat = self.get_readiness_category(player_readiness)
        readiness_factor = self.readiness_impact[readiness_cat]
        
        # Домашний/гостевой фактор
        venue_factor = 0.85 if is_home else 1.15
        
        # Расчет вероятностей
        card_stats = self.calculate_player_card_stats(player_data)
        
        if card_stats:
            # Используем реальную статистику игрока
            base_yellow = card_stats.yellow_cards_per_90
            base_red = card_stats.red_cards_per_90
        else:
            # Более реалистичные дефолтные значения
            base_yellow = pos_factors["yellow"] * 0.5
            base_red = pos_factors["red"] * 0.1
        
        # Увеличиваем базовые вероятности
        yellow_prob = min(0.25, base_yellow * pos_factors["yellow"] * importance_factor * 
                         readiness_factor * venue_factor / 45)  # Делим на 45 вместо 90
        
        red_prob = min(0.08, base_red * pos_factors["red"] * importance_factor * 
                      readiness_factor * venue_factor / 45)     # Делим на 45 вместо 90
        
        # Вероятность получения хотя бы одной карточки
        any_card_prob = 1 - (1 - yellow_prob) * (1 - red_prob)
        
        return {
            "yellow_card_prob": yellow_prob,
            "red_card_prob": red_prob,
            "any_card_prob": any_card_prob,
            "expected_cards": yellow_prob + red_prob * 2,
            "aggression_level": readiness_factor * pos_factors["yellow"]
        }
    
    def create_readiness_dict(self, readiness_data: List[Dict], team_players: List[Dict]) -> Dict:
        """Создание словаря готовности с улучшенным сопоставлением имен"""
        readiness_dict = {}
        
        for readiness_player in readiness_data:
            readiness_name = self.clean_name(readiness_player['name'])
            for team_player in team_players:
                team_name = self.clean_name(team_player['name'])
                if readiness_name == team_name:
                    readiness_dict[team_player['name']] = readiness_player['readiness']
                    break
        
        return readiness_dict
    
    def predict_team_cards(self, team_players: List[Dict], readiness_data: List[Dict],
                         match_type: str, is_home: bool) -> Dict:
        """Прогноз карточек для всей команды"""
        total_yellow_prob = 0
        total_red_prob = 0
        player_predictions = []
        
        # Создаем словарь готовности
        readiness_dict = self.create_readiness_dict(readiness_data, team_players)
        
        print(f"  Сопоставлено {len(readiness_dict)} игроков из {len(team_players)}")
        
        for player in team_players:
            player_name = player['name']
            if player_name in readiness_dict:
                prediction = self.predict_player_cards(
                    player, readiness_dict[player_name], match_type, is_home
                )
                player_predictions.append({
                    "name": player_name,
                    "position": player['position'],
                    "prediction": prediction
                })
                total_yellow_prob += prediction["yellow_card_prob"]
                total_red_prob += prediction["red_card_prob"]
        
        # Корректируем общие показатели на основе базовых значений лиги
        team_size_factor = len([p for p in team_players if p['name'] in readiness_dict]) / 11.0
        baseline_adjustment = 1.2  # Корректировка к базовым значениям
        
        expected_yellows = total_yellow_prob * baseline_adjustment * team_size_factor
        expected_reds = total_red_prob * baseline_adjustment * team_size_factor
        
        # Ограничиваем максимальные значения
        expected_yellows = min(expected_yellows, 5.0)
        expected_reds = min(expected_reds, 1.0)
        
        # Пуассоновское распределение для общего количества карточек
        team_prediction = {
            "expected_yellows": expected_yellows,
            "expected_reds": expected_reds,
            "expected_total_cards": expected_yellows + expected_reds,
            "over_15_cards_prob": self.poisson_probability(expected_yellows + expected_reds, 2, 10),
            "over_25_cards_prob": self.poisson_probability(expected_yellows + expected_reds, 3, 10),
            "over_35_cards_prob": self.poisson_probability(expected_yellows + expected_reds, 4, 10),
            "player_predictions": sorted(player_predictions, 
                                      key=lambda x: x['prediction']['any_card_prob'], 
                                      reverse=True)
        }
        
        return team_prediction
    
    def poisson_probability(self, mean: float, min_goals: int, max_goals: int = 10) -> float:
        """Вероятность по Пуассону для количества карточек"""
        if mean <= 0:
            return 0.0
            
        prob = 0
        for k in range(min_goals, max_goals + 1):
            prob += (mean ** k) * exp(-mean) / math.factorial(k)
        return prob
    
    def predict_match_cards(self, team1_data: List[Dict], team2_data: List[Dict],
                          team1_readiness: List[Dict], team2_readiness: List[Dict],
                          match_type: str = "обычный", is_team1_home: bool = True) -> Dict:
        """Прогноз карточек на весь матч"""
        print("Начинаем прогноз карточек...")
        
        team1_pred = self.predict_team_cards(team1_data, team1_readiness, match_type, is_team1_home)
        team2_pred = self.predict_team_cards(team2_data, team2_readiness, match_type, not is_team1_home)
        
        total_yellows = team1_pred["expected_yellows"] + team2_pred["expected_yellows"]
        total_reds = team1_pred["expected_reds"] + team2_pred["expected_reds"]
        total_cards = total_yellows + total_reds
        
        # Корректировка общих показателей матча
        match_adjustment = 1.3
        total_yellows_adj = total_yellows * match_adjustment
        total_reds_adj = total_reds * match_adjustment
        total_cards_adj = total_yellows_adj + total_reds_adj
        
        return {
            "team1": team1_pred,
            "team2": team2_pred,
            "match_total": {
                "expected_yellows": total_yellows_adj,
                "expected_reds": total_reds_adj,
                "expected_total_cards": total_cards_adj,
                "over_25_cards_prob": self.poisson_probability(total_cards_adj, 3, 15),
                "over_35_cards_prob": self.poisson_probability(total_cards_adj, 4, 15),
                "over_45_cards_prob": self.poisson_probability(total_cards_adj, 5, 15),
                "both_teams_cards_prob": 1 - (1 - min(team1_pred["expected_total_cards"]/3, 1)) * 
                                       (1 - min(team2_pred["expected_total_cards"]/3, 1))
            },
            "most_risky_players": (team1_pred["player_predictions"][:5] + 
                                 team2_pred["player_predictions"][:5])
        }

def main():
    # Инициализация прогнозиста
    predictor = CardPredictor()
    
    # Загрузка данных
    try:
        with open('commands/12-br/Sport Club do Recife.json', 'r', encoding='utf-8') as f:
            team1_data = json.load(f)
        
        with open('commands/12-br/Esporte Clube Juventude.json', 'r', encoding='utf-8') as f:
            team2_data = json.load(f)
        
        with open('output_with_readiness_1.json', 'r', encoding='utf-8') as f:
            team1_readiness = json.load(f)
        
        with open('output_with_readiness_2.json', 'r', encoding='utf-8') as f:
            team2_readiness = json.load(f)
            
        print("Данные успешно загружены!")
        print(f"Команда 1: {len(team1_data)} игроков")
        print(f"Команда 2: {len(team2_data)} игроков")
        print(f"Готовность 1: {len(team1_readiness)} записей")
        print(f"Готовность 2: {len(team2_readiness)} записей")
            
    except FileNotFoundError as e:
        print(f"Ошибка: Файл не найден - {e}")
        return
    except json.JSONDecodeError as e:
        print(f"Ошибка чтения JSON: {e}")
        return
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return
    
    # Прогноз карточек на матч
    prediction = predictor.predict_match_cards(
        team1_data, team2_data, team1_readiness, team2_readiness,
        match_type="дерби", is_team1_home=True
    )
    
    # Вывод результатов
    print("\n" + "=" * 60)
    print("ПРОГНОЗ КАРТОЧЕК НА МАТЧ")
    print("=" * 60)
    
    print(f"\n📊 ОБЩАЯ СТАТИСТИКА МАТЧА:")
    print(f"🟡 Ожидаемое количество желтых карточек: {prediction['match_total']['expected_yellows']:.2f}")
    print(f"🔴 Ожидаемое количество красных карточек: {prediction['match_total']['expected_reds']:.2f}")
    print(f"📋 Общее ожидаемое количество карточек: {prediction['match_total']['expected_total_cards']:.2f}")
    
    print(f"\n🎯 ВЕРОЯТНОСТИ ТОТАЛОВ:")
    print(f"✅ >2.5 карточек: {prediction['match_total']['over_25_cards_prob']:.1%}")
    print(f"✅ >3.5 карточек: {prediction['match_total']['over_35_cards_prob']:.1%}")
    print(f"✅ >4.5 карточек: {prediction['match_total']['over_45_cards_prob']:.1%}")
    print(f"🔄 Обе команды получат карточки: {prediction['match_total']['both_teams_cards_prob']:.1%}")
    
    print(f"\n👥 СТАТИСТИКА ПО КОМАНДАМ:")
    print(f"Команда 1: {prediction['team1']['expected_yellows']:.2f}🟡 {prediction['team1']['expected_reds']:.2f}🔴")
    print(f"Команда 2: {prediction['team2']['expected_yellows']:.2f}🟡 {prediction['team2']['expected_reds']:.2f}🔴")
    
    print(f"\n⚠️  САМЫЕ РИСКОВАННЫЕ ИГРОКИ:")
    risky_players = sorted(prediction['most_risky_players'], 
                          key=lambda x: x['prediction']['any_card_prob'], 
                          reverse=True)[:8]
    
    for i, player in enumerate(risky_players, 1):
        pred = player['prediction']
        print(f"{i}. {player['name']} ({player['position']})")
        print(f"   🟡 Вероятность желтой: {pred['yellow_card_prob']:.1%}")
        print(f"   🔴 Вероятность красной: {pred['red_card_prob']:.1%}")
        print(f"   📊 Вероятность любой карточки: {pred['any_card_prob']:.1%}")
        print()

if __name__ == "__main__":
    main()
# import json
# import numpy as np
# from typing import Dict, List, Optional
# from dataclasses import dataclass
# from math import exp, factorial
# import math

# @dataclass
# class CardStats:
#     """Статистика карточек игрока"""
#     yellow_cards_per_90: float
#     red_cards_per_90: float
#     fouls_per_90: float
#     aggression_factor: float

# class CardPredictor:
#     def __init__(self):
#         # Коэффициенты влияния позиции на карточки
#         self.position_factors = {
#             "вратарь": {"yellow": 0.1, "red": 0.01, "fouls": 0.2},
#             "центр. защитник": {"yellow": 1.2, "red": 0.3, "fouls": 1.1},
#             "левый защитник": {"yellow": 1.0, "red": 0.2, "fouls": 0.9},
#             "правый защитник": {"yellow": 1.0, "red": 0.2, "fouls": 0.9},
#             "опорный полузащитник": {"yellow": 1.4, "red": 0.4, "fouls": 1.3},
#             "центр. полузащитник": {"yellow": 0.8, "red": 0.15, "fouls": 0.7},
#             "атак. полузащитник": {"yellow": 0.6, "red": 0.1, "fouls": 0.5},
#             "левый вингер": {"yellow": 0.7, "red": 0.12, "fouls": 0.6},
#             "правый вингер": {"yellow": 0.7, "red": 0.12, "fouls": 0.6},
#             "центральный нап.": {"yellow": 0.5, "red": 0.08, "fouls": 0.4}
#         }
        
#         # Факторы важности матча
#         self.match_importance = {
#             "дерби": 1.4,
#             "вылет": 1.3,
#             "еврокубки": 1.2,
#             "кубок": 1.1,
#             "обычный": 1.0
#         }
        
#         # Влияние готовности на агрессивность
#         self.readiness_impact = {
#             "very_low": 1.4,  # < 0.3
#             "low": 1.2,       # 0.3-0.5
#             "medium": 1.0,    # 0.5-0.7
#             "high": 0.8,      # 0.7-0.9
#             "very_high": 0.6  # > 0.9
#         }
    
#     def calculate_player_card_stats(self, player_data: Dict, minutes_played_threshold: int = 180) -> Optional[CardStats]:
#         """Расчет статистики карточек для игрока"""
#         if not player_data.get('stats') or not player_data['stats'].get('total_stats'):
#             return None
        
#         total_stats = player_data['stats']['total_stats']
#         total_minutes = total_stats.get('total_minutes_played', 0)
        
#         if total_minutes < minutes_played_threshold:
#             return None
        
#         # Расчет показателей на 90 минут
#         yellow_per_90 = (total_stats.get('total_yellow_cards', 0) / total_minutes) * 90
#         red_per_90 = (total_stats.get('total_red_cards', 0) / total_minutes) * 90
        
#         # Оценка агрессивности (на основе карточек и предположений о фолах)
#         aggression = (yellow_per_90 * 0.6 + red_per_90 * 2.0) * 0.8
        
#         return CardStats(
#             yellow_cards_per_90=yellow_per_90,
#             red_cards_per_90=red_per_90,
#             fouls_per_90=aggression * 1.2,  # Примерная оценка фолов
#             aggression_factor=aggression
#         )
    
#     def get_readiness_category(self, readiness: float) -> str:
#         """Категоризация готовности"""
#         if readiness < 0.3: return "very_low"
#         elif readiness < 0.5: return "low"
#         elif readiness < 0.7: return "medium"
#         elif readiness < 0.9: return "high"
#         else: return "very_high"
    
#     def predict_player_cards(self, player_data: Dict, player_readiness: float, 
#                            match_type: str = "обычный", is_home: bool = True) -> Dict:
#         """Прогноз карточек для конкретного игрока"""
#         position = player_data['position'].lower()
        
#         # Базовые факторы
#         pos_factors = self.position_factors.get(position, self.position_factors["центр. полузащитник"])
#         importance_factor = self.match_importance.get(match_type, 1.0)
        
#         # Влияние готовности
#         readiness_cat = self.get_readiness_category(player_readiness)
#         readiness_factor = self.readiness_impact[readiness_cat]
        
#         # Домашний/гостевой фактор
#         venue_factor = 0.9 if is_home else 1.1
        
#         # Расчет вероятностей
#         card_stats = self.calculate_player_card_stats(player_data)
#         if card_stats:
#             base_yellow = card_stats.yellow_cards_per_90
#             base_red = card_stats.red_cards_per_90
#         else:
#             # Дефолтные значения для новых игроков
#             base_yellow = pos_factors["yellow"] * 0.3
#             base_red = pos_factors["red"] * 0.05
        
#         # Итоговые вероятности
#         yellow_prob = min(0.8, base_yellow * pos_factors["yellow"] * importance_factor * 
#                          readiness_factor * venue_factor / 90)
        
#         red_prob = min(0.3, base_red * pos_factors["red"] * importance_factor * 
#                       readiness_factor * venue_factor / 90)
        
#         # Вероятность получения хотя бы одной карточки
#         any_card_prob = 1 - (1 - yellow_prob) * (1 - red_prob)
        
#         return {
#             "yellow_card_prob": yellow_prob,
#             "red_card_prob": red_prob,
#             "any_card_prob": any_card_prob,
#             "expected_cards": yellow_prob + red_prob * 2,
#             "aggression_level": readiness_factor * pos_factors["yellow"]
#         }
    
#     def predict_team_cards(self, team_players: List[Dict], readiness_data: List[Dict],
#                          match_type: str, is_home: bool) -> Dict:
#         """Прогноз карточек для всей команды"""
#         total_yellow_prob = 0
#         total_red_prob = 0
#         player_predictions = []
        
#         # Создаем словарь готовности для быстрого доступа
#         readiness_dict = {p['name']: p['readiness'] for p in readiness_data}
        
#         for player in team_players:
#             player_name = player['name']
#             if player_name in readiness_dict:
#                 prediction = self.predict_player_cards(
#                     player, readiness_dict[player_name], match_type, is_home
#                 )
#                 player_predictions.append({
#                     "name": player_name,
#                     "position": player['position'],
#                     "prediction": prediction
#                 })
#                 total_yellow_prob += prediction["yellow_card_prob"]
#                 total_red_prob += prediction["red_card_prob"]
        
#         # Прогноз для команды
#         expected_yellows = total_yellow_prob
#         expected_reds = total_red_prob
        
#         # Пуассоновское распределение для общего количества карточек
#         team_prediction = {
#             "expected_yellows": expected_yellows,
#             "expected_reds": expected_reds,
#             "expected_total_cards": expected_yellows + expected_reds,
#             "over_15_cards_prob": self.poisson_probability(expected_yellows + expected_reds, 2, 10),
#             "over_25_cards_prob": self.poisson_probability(expected_yellows + expected_reds, 3, 10),
#             "over_35_cards_prob": self.poisson_probability(expected_yellows + expected_reds, 4, 10),
#             "player_predictions": sorted(player_predictions, 
#                                       key=lambda x: x['prediction']['any_card_prob'], 
#                                       reverse=True)
#         }
        
#         return team_prediction
    
#     def poisson_probability(self, mean: float, min_goals: int, max_goals: int = 10) -> float:
#         """Вероятность по Пуассону для количества карточек"""
#         prob = 0
#         for k in range(min_goals, max_goals + 1):
#             prob += (mean ** k) * exp(-mean) / math.factorial(k)
#         return prob
    
#     def predict_match_cards(self, team1_data: List[Dict], team2_data: List[Dict],
#                           team1_readiness: List[Dict], team2_readiness: List[Dict],
#                           match_type: str = "обычный", is_team1_home: bool = True) -> Dict:
#         """Прогноз карточек на весь матч"""
#         team1_pred = self.predict_team_cards(team1_data, team1_readiness, match_type, is_team1_home)
#         team2_pred = self.predict_team_cards(team2_data, team2_readiness, match_type, not is_team1_home)
        
#         total_yellows = team1_pred["expected_yellows"] + team2_pred["expected_yellows"]
#         total_reds = team1_pred["expected_reds"] + team2_pred["expected_reds"]
#         total_cards = total_yellows + total_reds
        
#         return {
#             "team1": team1_pred,
#             "team2": team2_pred,
#             "match_total": {
#                 "expected_yellows": total_yellows,
#                 "expected_reds": total_reds,
#                 "expected_total_cards": total_cards,
#                 "over_25_cards_prob": self.poisson_probability(total_cards, 3, 15),
#                 "over_35_cards_prob": self.poisson_probability(total_cards, 4, 15),
#                 "over_45_cards_prob": self.poisson_probability(total_cards, 5, 15),
#                 "both_teams_cards_prob": 1 - (1 - team1_pred["expected_total_cards"]) * 
#                                        (1 - team2_pred["expected_total_cards"])
#             },
#             "most_risky_players": team1_pred["player_predictions"][:3] + team2_pred["player_predictions"][:3]
#         }

# # Пример использования
# def main():
#     # Инициализация прогнозиста
#     predictor = CardPredictor()
    
#     # Загрузка данных
#     try:
#         with open('commands/12-br/Sport Club do Recife.json', 'r', encoding='utf-8') as f:
#             team1_data = json.load(f)
        
#         with open('commands/12-br/Esporte Clube Juventude.json', 'r', encoding='utf-8') as f:
#             team2_data = json.load(f)
        
#         with open('output_with_readiness_1.json', 'r', encoding='utf-8') as f:
#             team1_readiness = json.load(f)
        
#         with open('output_with_readiness_2.json', 'r', encoding='utf-8') as f:
#             team2_readiness = json.load(f)
            
#         print("Данные успешно загружены!")
#         print(f"Команда 1: {len(team1_data)} игроков")
#         print(f"Команда 2: {len(team2_data)} игроков")
#         print(f"Готовность 1: {len(team1_readiness)} записей")
#         print(f"Готовность 2: {len(team2_readiness)} записей")
            
#     except FileNotFoundError as e:
#         print(f"Ошибка: Файл не найден - {e}")
#         return
#     except json.JSONDecodeError as e:
#         print(f"Ошибка чтения JSON: {e}")
#         return
#     except Exception as e:
#         print(f"Неожиданная ошибка: {e}")
#         return
    
#     # Прогноз карточек на матч
#     prediction = predictor.predict_match_cards(
#         team1_data, team2_data, team1_readiness, team2_readiness,
#         match_type="дерби", is_team1_home=True
#     )
    
#     # Вывод результатов
#     print("\n" + "=" * 50)
#     print("ПРОГНОЗ КАРТОЧЕК НА МАТЧ")
#     print("=" * 50)
    
#     print(f"\nОБЩАЯ СТАТИСТИКА:")
#     print(f"Ожидаемое количество желтых карточек: {prediction['match_total']['expected_yellows']:.2f}")
#     print(f"Ожидаемое количество красных карточек: {prediction['match_total']['expected_reds']:.2f}")
#     print(f"Общее ожидаемое количество карточек: {prediction['match_total']['expected_total_cards']:.2f}")
    
#     print(f"\nВЕРОЯТНОСТИ ТОТАЛОВ:")
#     print(f">2.5 карточек: {prediction['match_total']['over_25_cards_prob']:.3f}")
#     print(f">3.5 карточек: {prediction['match_total']['over_35_cards_prob']:.3f}")
#     print(f">4.5 карточек: {prediction['match_total']['over_45_cards_prob']:.3f}")
#     print(f"Обе команды получат карточки: {prediction['match_total']['both_teams_cards_prob']:.3f}")
    
#     print(f"\nСАМЫЕ РИСКОВАННЫЕ ИГРОКИ:")
#     for i, player in enumerate(prediction['most_risky_players'][:5], 1):
#         pred = player['prediction']
#         print(f"{i}. {player['name']} ({player['position']})")
#         print(f"   Вероятность желтой: {pred['yellow_card_prob']:.3f}")
#         print(f"   Вероятность красной: {pred['red_card_prob']:.3f}")
#         print(f"   Вероятность любой карточки: {pred['any_card_prob']:.3f}")
#         print()

# if __name__ == "__main__":
#     main()