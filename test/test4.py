import json
import numpy as np
from math import factorial, exp
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# ==================== КОНСТАНТЫ И МОДЕЛИ ====================
POSITION_WEIGHTS = {
    'вратарь': {'defense': 1.5, 'attack': 0.0},
    'центральный защитник': {'defense': 1.2, 'attack': 0.1},
    'центр. защитник': {'defense': 1.2, 'attack': 0.1},
    'крайний защитник': {'defense': 0.7, 'attack': 0.4},
    'левый защитник': {'defense': 0.7, 'attack': 0.4},
    'правый защитник': {'defense': 0.7, 'attack': 0.4},
    'опорный полузащитник': {'defense': 0.8, 'attack': 0.3},
    'центральный полузащитник': {'defense': 0.5, 'attack': 0.6},
    'центр. полузащитник': {'defense': 0.5, 'attack': 0.6},
    'атакующий полузащитник': {'defense': 0.3, 'attack': 0.8},
    'атак. полузащитник': {'defense': 0.3, 'attack': 0.8},
    'вингер': {'defense': 0.2, 'attack': 1.0},
    'левый вингер': {'defense': 0.2, 'attack': 1.0},
    'правый вингер': {'defense': 0.2, 'attack': 1.0},
    'нападающий': {'defense': 0.1, 'attack': 1.2},
    'центральный нап.': {'defense': 0.1, 'attack': 1.2}
}

@dataclass
class SeasonStats:
    position: int
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_scored: int
    goals_conceded: int
    points: int

@dataclass
class TeamTactics:
    formation: str = "4-3-3"
    possession_avg: float = 0.55
    press_intensity: str = "medium"
    transition_speed: float = 0.7
    cross_accuracy: float = 0.35
    long_shots_per_match: float = 5.1

# ==================== ОСНОВНОЙ КЛАСС КОМАНДЫ ====================
class FootballTeam:
    def __init__(self, name: str, is_home: bool):
        self.name = name
        self.is_home = is_home
        self.players: List[Dict] = []
        self.season_stats: Optional[SeasonStats] = None
        self.tactics: Optional[TeamTactics] = None
        self.stats: Dict = {}
        self.team_value: float = 0.0  # Стоимость состава в млн €
    
    def load_players_from_json(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            self.players = json.load(f)
    
    def calculate_player_stats(self):
        if not self.players:
            self.stats = {'avg_readiness': 0.5, 'attack_strength': 0.5, 'defense_strength': 0.5, 'top_attackers': [0.3]}
            return
        
        readiness = []
        defense_contributions = []
        attack_contributions = []
        
        for player in self.players:
            pos = player['position'].lower()
            readiness.append(player['readiness'])
            
            # Находим подходящий вес для позиции
            weights = None
            for key in POSITION_WEIGHTS:
                if key in pos:
                    weights = POSITION_WEIGHTS[key]
                    break
            
            if weights is None:
                # Дефолтные веса для неизвестных позиций
                weights = {'defense': 0.5, 'attack': 0.5}
            
            defense_contributions.append(player['readiness'] * weights['defense'])
            attack_contributions.append(player['readiness'] * weights['attack'])
        
        # Топ-3 атакующих игрока
        top_attackers = sorted(attack_contributions, reverse=True)[:3]
        
        self.stats = {
            'avg_readiness': np.mean(readiness) if readiness else 0.5,
            'attack_strength': np.mean(top_attackers) if top_attackers else 0.5,
            'defense_strength': np.mean(defense_contributions) if defense_contributions else 0.5,
            'top_attackers': top_attackers
        }
    
    def calculate_season_form(self) -> float:
        if not self.season_stats:
            return 1.0
        
        win_rate = self.season_stats.wins / self.season_stats.matches_played
        loss_rate = self.season_stats.losses / self.season_stats.matches_played
        goal_ratio = self.season_stats.goals_scored / max(1, self.season_stats.goals_conceded)
        
        return (win_rate * 0.5 + (1 - loss_rate) * 0.3 + min(goal_ratio, 2.0) * 0.2)
    
    def adjust_stats_with_season_data(self):
        if not self.season_stats:
            return
        
        form_coeff = self.calculate_season_form()
        
        attack_adjustment = (self.season_stats.goals_scored / self.season_stats.matches_played / 3) * 0.3
        defense_adjustment = (1 - self.season_stats.goals_conceded / self.season_stats.matches_played / 1.5) * 0.3
        
        self.stats['attack_strength'] = self.stats['attack_strength'] * 0.7 + attack_adjustment
        self.stats['defense_strength'] = self.stats['defense_strength'] * 0.7 + defense_adjustment
        self.stats['form_coefficient'] = form_coeff

# ==================== КЛАСС РАСЧЕТА ПРОГНОЗОВ ====================
class MatchPredictor:
    def __init__(self):
        self.weather_impact = {"rain": -0.02, "sunny": 0.03, "windy": -0.01, "snow": -0.03, None: 0.0}
        self.motivation_rules = {
            'вылет': 0.25, 'еврокубки': 0.2, 'дерби': 0.15, 
            'кубок': 0.15, 'клубный_чемпионат': 0.2, 'обычный': 0.05
        }
        self.calibration_curve = self._create_calibration_curve()
    
    def _create_calibration_curve(self) -> Dict[float, float]:
        return {0.1: 0.08, 0.2: 0.18, 0.3: 0.28, 0.4: 0.38, 0.5: 0.48, 0.6: 0.55, 0.7: 0.65, 0.8: 0.75, 0.9: 0.85}
    
    def _get_position_correction(self, team1: FootballTeam, team2: FootballTeam) -> float:
        """Поправка на разницу в классе команд по позиции в лиге"""
        if not team1.season_stats or not team2.season_stats:
            return 0.0
        
        position_diff = team2.season_stats.position - team1.season_stats.position
        return min(0.3, position_diff * 0.03)  # +3% за каждую позицию разницы
    
    def _get_value_correction(self, team1: FootballTeam, team2: FootballTeam) -> float:
        """Поправка на разницу в стоимости состава"""
        if team1.team_value == 0 or team2.team_value == 0:
            return 0.0
        
        value_ratio = team2.team_value / team1.team_value
        return min(0.2, (value_ratio - 1) * 0.05)  # +5% за каждое удвоение стоимости
    
    def calculate_motivation(self, team: FootballTeam, match_type: str) -> float:
        base_motivation = self.motivation_rules.get(match_type, 0.05)
        
        if not team.season_stats:
            return base_motivation
        
        position = team.season_stats.position
        
        if position >= 18: base_motivation += 0.15
        elif 16 <= position <= 17: base_motivation += 0.10
        elif position <= 4: base_motivation += 0.12 if match_type != 'вылет' else 0.05
        elif 5 <= position <= 6: base_motivation += 0.08
        elif 7 <= position <= 9: base_motivation += 0.05
        elif 10 <= position <= 15: base_motivation += 0.02
        
        return min(0.35, max(0.0, base_motivation))
    
    def poisson_probability(self, mean: float, goals: int) -> float:
        return (mean ** goals) * exp(-mean) / factorial(goals)
    
    def calculate_exact_scores(self, team1: FootballTeam, team2: FootballTeam, max_goals: int = 5) -> Dict:
        mean_team1 = 0.8 * team1.stats['attack_strength'] / team2.stats['defense_strength']
        mean_team2 = 1.2 * team2.stats['attack_strength'] / team1.stats['defense_strength']
        
        if team1.is_home:
            mean_team1 *= 1.2
            mean_team2 *= 0.9
        else:
            mean_team1 *= 0.9
            mean_team2 *= 1.2
        
        scores = {}
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                prob = self.poisson_probability(mean_team1, i) * self.poisson_probability(mean_team2, j)
                scores[f"{i}-{j}"] = round(prob, 4)
        
        total = sum(scores.values())
        return {score: prob/total for score, prob in scores.items()}
    
    def calibrate_probability(self, raw_prob: float) -> float:
        rounded_prob = round(raw_prob, 1)
        return self.calibration_curve.get(rounded_prob, raw_prob)
    
    def calculate_value_bet(self, model_prob: float, bookmaker_odds: float) -> Tuple[bool, float]:
        implied_prob = 1 / bookmaker_odds
        value = model_prob - implied_prob
        return value > 0.05, value
    
    def predict(self, team1: FootballTeam, team2: FootballTeam, weather: str, match_type: str, bookmaker_odds: Optional[Dict] = None) -> Dict:
        # Базовые параметры
        home_advantage = 0.1 if team1.season_stats and team1.season_stats.position < 10 else 0.05
        weather_impact = self.weather_impact.get(weather, 0.0)
        
        # Поправки на класс команд
        position_correction = self._get_position_correction(team1, team2)
        value_correction = self._get_value_correction(team1, team2)
        total_correction = position_correction + value_correction
        
        # Мотивация
        team1_motivation = self.calculate_motivation(team1, match_type)
        team2_motivation = self.calculate_motivation(team2, match_type)
        
        # Сила команд с поправками
        team1_power = self._calculate_team_power(team1, home_advantage, team1_motivation)
        team2_power = self._calculate_team_power(team2, -home_advantage * 0.6, team2_motivation + total_correction)
        
        diff = (team1_power - team2_power) * (1 + weather_impact * 0.5)
        
        # Прогноз
        forecasts = self._create_base_forecast(team1, team2, diff, weather_impact)
        self._apply_adjustments(team1, team2, forecasts)
        forecasts = self._calibrate_forecasts(forecasts)
        
        # Точные счета
        forecasts["Точный счет"] = self.calculate_exact_scores(team1, team2)
        forecasts["Точный счет"] = dict(sorted(forecasts["Точный счет"].items(), key=lambda item: item[1], reverse=True)[:10])
        
        # Value bets
        if bookmaker_odds:
            forecasts["Value Bets"] = self._find_value_bets(forecasts, bookmaker_odds)
        
        return forecasts
    
    # def _calculate_team_power(self, team: FootballTeam, advantage: float, motivation: float) -> float:
    #     return (
    #         team.stats['avg_readiness'] * 0.4 +
    #         team.stats['attack_strength'] * 0.4 +
    #         team.stats['defense_strength'] * 0.2 +
    #         advantage +
    #         motivation
    #     )

    def _calculate_team_power(self, team: FootballTeam, advantage: float, motivation: float) -> float:

        base_power = (
            team.stats['avg_readiness'] * 0.3 +  # Меньший вес готовности
            team.stats['attack_strength'] * 0.4 +  # Больший вес атаки
            team.stats['defense_strength'] * 0.3 +  # Больший вес защиты
            advantage +
            motivation
        )
        
        # Учет формы сезона
        if hasattr(team, 'stats') and 'form_coefficient' in team.stats:
            base_power *= team.stats['form_coefficient']
    
        return base_power
    
    def _create_base_forecast(self, team1: FootballTeam, team2: FootballTeam, diff: float, weather_impact: float) -> Dict:
        return {
            "1X2": {
                "П1": max(0.1, min(0.9, 0.45 + diff * 0.6)),
                "X": max(0.1, min(0.9, 0.3 - abs(diff) * 0.7)),
                "П2": max(0.1, min(0.9, 0.25 - diff * 0.6))
            },
            "Тоталы": {
                ">1.5": 0.65 + (team1.stats['attack_strength'] + team2.stats['attack_strength']) * 0.25 + weather_impact,
                "<1.5": 0.35 - (team1.stats['attack_strength'] + team2.stats['attack_strength']) * 0.25 - weather_impact,
                ">2.5": 0.55 + (team1.stats['attack_strength'] + team2.stats['attack_strength']) * 0.2 + weather_impact * 0.7,
                "<2.5": 0.45 - (team1.stats['attack_strength'] + team2.stats['attack_strength']) * 0.2 - weather_impact * 0.7,
                ">3.5": 0.4 + (team1.stats['attack_strength'] + team2.stats['attack_strength']) * 0.15 + weather_impact * 0.5
            },
            "Форы": {
                "Ф1(-1.5)": max(0.1, 0.35 + diff * 0.4),
                "Ф2(+1.5)": max(0.1, 0.65 - diff * 0.4),
                "Ф1(-0.5)": max(0.1, 0.55 + diff * 0.5),
                "Ф2(+0.5)": max(0.1, 0.45 - diff * 0.5)
            },
            "Обе забьют": {
                "Да": min(0.95, max(0.05, (team1.stats['attack_strength'] * 0.6 + team2.stats['attack_strength'] * 0.6) * 0.6 - weather_impact * 0.1)),
                "Нет": 1 - (team1.stats['attack_strength'] * 0.6 + team2.stats['attack_strength'] * 0.6) * 0.6 + weather_impact * 0.1
            }
        }
    
    def _apply_adjustments(self, team1: FootballTeam, team2: FootballTeam, forecasts: Dict):
        if team1.stats['top_attackers'] and team1.stats['top_attackers'][0] > 0.6:
            forecasts["1X2"]["П1"] *= 1.1
            forecasts["Тоталы"][">2.5"] *= 1.15
        
        if team2.stats['top_attackers'] and team2.stats['top_attackers'][0] > 0.6:
            forecasts["1X2"]["П2"] *= 1.1
            forecasts["Тоталы"][">2.5"] *= 1.15
    
    def _calibrate_forecasts(self, forecasts: Dict) -> Dict:
        calibrated = {}
        for market, values in forecasts.items():
            if isinstance(values, dict):
                calibrated[market] = {k: self.calibrate_probability(v) for k, v in values.items()}
            else:
                calibrated[market] = values
        return calibrated
    
    def _find_value_bets(self, forecasts: Dict, bookmaker_odds: Dict) -> Dict:
        value_bets = {}
        for market, values in forecasts.items():
            if market in bookmaker_odds:
                for bet_type, model_prob in values.items():
                    if bet_type in bookmaker_odds[market]:
                        is_value, value = self.calculate_value_bet(model_prob, bookmaker_odds[market][bet_type])
                        if is_value:
                            value_bets[f"{market}_{bet_type}"] = {
                                "model_prob": model_prob,
                                "bookmaker_odds": bookmaker_odds[market][bet_type],
                                "value": value
                            }
        return value_bets

# ==================== ИСПОЛЬЗОВАНИЕ ====================
if __name__ == "__main__":
    # Инициализация команд
    team1 = FootballTeam("Брентфорд", is_home=True)
    team2 = FootballTeam("Челси", is_home=False)
    
    # Загрузка данных
    team1.load_players_from_json("output_with_readiness_1.json")
    team2.load_players_from_json("output_with_readiness_2.json")
    
    # Статистика сезона
    team1.season_stats = SeasonStats(position=17, matches_played=3, wins=1, draws=0, losses=2, goals_scored=3, goals_conceded=5, points=3)
    team2.season_stats = SeasonStats(position=5, matches_played=3, wins=2, draws=1, losses=0, goals_scored=7, goals_conceded=1, points=7)
    
    # Стоимость составов (в млн €)
    team1.team_value = 250  # Брентфорд
    team2.team_value = 900  # Челси
    
    # Тактика
    team1.tactics = TeamTactics(formation="4-2-3", possession_avg=0.48, press_intensity="medium", transition_speed=0.6)
    team2.tactics = TeamTactics(formation="4-2-3", possession_avg=0.62, press_intensity="high", transition_speed=0.8)
    
    # Расчет статистик
    team1.calculate_player_stats()
    team2.calculate_player_stats()
    team1.adjust_stats_with_season_data()
    team2.adjust_stats_with_season_data()
    
    # Прогноз
    predictor = MatchPredictor()
    forecast = predictor.predict(team1, team2, "sunny", "еврокубки", {
        "1X2": {"П1": 4.2, "X": 3.2, "П2": 1.8},
        "Тоталы": {">2.5": 1.8, "<2.5": 2.1},
        "Форы": {"Ф1(-1.5)": 9.1, "Ф2(+1.5)": 1.1}
    })
    
    # Вывод результатов
    print("ПРОГНОЗ НА МАТЧ:")
    for market, values in forecast.items():
        if market not in ["Value Bets", "Точный счет"]:
            print(f"\n{market}:")
            for bet_type, prob in values.items():
                print(f"  {bet_type}: {prob:.3f}")
    
    print(f"\nТочный счет (топ-10):")
    for score, prob in forecast["Точный счет"].items():
        print(f"  {score}: {prob:.3f}")
    
    if "Value Bets" in forecast:
        print(f"\nVALUE BETS:")
        for bet, data in forecast["Value Bets"].items():
            print(f"  {bet}: prob={data['model_prob']:.3f}, odds={data['bookmaker_odds']}, value={data['value']:.3f}")


# ==================== КЛАСС ДЛЯ ВИЗУАЛИЗАЦИИ РАСЧЕТОВ ====================
class CalculationVisualizer:
    """Независимый класс для визуализации процесса расчетов с новыми весами"""
    
    @staticmethod
    def load_and_display_team_data(file_path: str, team_name: str):
        """Загрузка и отображение данных команды"""
        print(f"\n{'='*60}")
        print(f"ДАННЫЕ КОМАНДЫ: {team_name}")
        print(f"{'='*60}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                players = json.load(f)
            
            print(f"Файл: {file_path}")
            print(f"Количество игроков: {len(players)}")
            
            # Статистика по позициям
            positions = {}
            readiness_by_position = {}
            
            for player in players:
                pos = player['position'].lower()
                if pos not in positions:
                    positions[pos] = 0
                    readiness_by_position[pos] = []
                positions[pos] += 1
                readiness_by_position[pos].append(player['readiness'])
            
            print("\nРАСПРЕДЕЛЕНИЕ ПО ПОЗИЦИЯМ:")
            for pos, count in positions.items():
                avg_readiness = np.mean(readiness_by_position[pos]) if readiness_by_position[pos] else 0
                print(f"  {pos}: {count} игроков, средняя готовность: {avg_readiness:.3f}")
            
            # Топ-5 игроков по готовности
            sorted_players = sorted(players, key=lambda x: x['readiness'], reverse=True)[:5]
            print("\nТОП-5 ИГРОКОВ ПО ГОТОВНОСТИ:")
            for i, player in enumerate(sorted_players, 1):
                print(f"  {i}. {player['name']} ({player['position']}): {player['readiness']:.3f}")
                
            return players
            
        except FileNotFoundError:
            print(f"Файл {file_path} не найден!")
            return []
        except json.JSONDecodeError:
            print(f"Ошибка чтения JSON файла {file_path}!")
            return []
    
    @staticmethod
    def calculate_team_stats(players: List[Dict], team_name: str):
        """Расчет и отображение статистик команды с НОВЫМИ весами"""
        print(f"\n{'='*60}")
        print(f"РАСЧЕТ СТАТИСТИК ДЛЯ: {team_name} (НОВЫЕ ВЕСА)")
        print(f"{'='*60}")
        
        if not players:
            print("Нет данных для расчета!")
            return {}
        
        readiness = []
        defense_contributions = []
        attack_contributions = []
        
        print("НОВЫЕ ВЕСА ПОЗИЦИЙ:")
        for category, weights in POSITION_WEIGHTS.items():
            print(f"  {category}: защита ×{weights['defense']}, атака ×{weights['attack']}")
        
        print("\nРАСЧЕТ ДЛЯ КАЖДОГО ИГРОКА:")
        for player in players:
            pos = player['position'].lower()
            readiness.append(player['readiness'])
            
            # Находим подходящий вес для позиции
            weights = None
            for key in POSITION_WEIGHTS:
                if key in pos:
                    weights = POSITION_WEIGHTS[key]
                    break
            
            if weights is None:
                # Дефолтные веса для неизвестных позиций
                weights = {'defense': 0.5, 'attack': 0.5}
                print(f"  ⚠️  {player['name']}: неизвестная позиция '{pos}', использованы веса по умолчанию")
            
            defense_val = player['readiness'] * weights['defense']
            attack_val = player['readiness'] * weights['attack']
            
            defense_contributions.append(defense_val)
            attack_contributions.append(attack_val)
            
            print(f"  {player['name']}: {pos} → защита {player['readiness']:.3f}×{weights['defense']}={defense_val:.3f}, атака {player['readiness']:.3f}×{weights['attack']}={attack_val:.3f}")
        
        # Топ-3 атакующих игрока
        top_attackers = sorted(attack_contributions, reverse=True)[:3] if attack_contributions else [0.3]
        
        stats = {
            'avg_readiness': np.mean(readiness) if readiness else 0.5,
            'attack_strength': np.mean(top_attackers) if top_attackers else 0.5,
            'defense_strength': np.mean(defense_contributions) if defense_contributions else 0.5,
            'top_attackers': top_attackers
        }
        
        print(f"\nИТОГОВЫЕ СТАТИСТИКИ:")
        print(f"  Средняя готовность: {stats['avg_readiness']:.3f}")
        print(f"  Сила атаки (топ-3): {stats['attack_strength']:.3f}")
        print(f"  Сила защиты: {stats['defense_strength']:.3f}")
        print(f"  Топ-атакующие: {[f'{x:.3f}' for x in stats['top_attackers']]}")
        
        return stats
    
    @staticmethod
    def visualize_match_calculation(team1_stats: Dict, team2_stats: Dict, team1_name: str, team2_name: str):
        """Визуализация расчета матча с исправленной формулой"""
        print(f"\n{'='*70}")
        print(f"РАСЧЕТ МАТЧА: {team1_name} vs {team2_name}")
        print(f"{'='*70}")
        
        # Имитация расчета силы команд по НОВОЙ формуле
        print("РАСЧЕТ СИЛЫ КОМАНД (НОВАЯ ФОРМУЛА):")
        print(f"{team1_name}: 0.3×{team1_stats['avg_readiness']:.3f} + 0.4×{team1_stats['attack_strength']:.3f} + 0.3×{team1_stats['defense_strength']:.3f}")
        team1_power = 0.3 * team1_stats['avg_readiness'] + 0.4 * team1_stats['attack_strength'] + 0.3 * team1_stats['defense_strength']
        print(f"  = {team1_power:.3f}")
        
        print(f"{team2_name}: 0.3×{team2_stats['avg_readiness']:.3f} + 0.4×{team2_stats['attack_strength']:.3f} + 0.3×{team2_stats['defense_strength']:.3f}")
        team2_power = 0.3 * team2_stats['avg_readiness'] + 0.4 * team2_stats['attack_strength'] + 0.3 * team2_stats['defense_strength']
        print(f"  = {team2_power:.3f}")
        
        # Разница в силе
        diff = team1_power - team2_power
        print(f"\nРАЗНИЦА В СИЛЕ: {team1_power:.3f} - {team2_power:.3f} = {diff:.3f}")
        
        # Прогноз 1X2
        print(f"\nПРОГНОЗ 1X2:")
        p1 = max(0.1, min(0.9, 0.45 + diff * 0.6))
        x = max(0.1, min(0.9, 0.3 - abs(diff) * 0.7))
        p2 = max(0.1, min(0.9, 0.25 - diff * 0.6))
        
        print(f"  П1: 0.45 + {diff:.3f}×0.6 = {0.45 + diff * 0.6:.3f} → {p1:.3f}")
        print(f"  X: 0.3 - |{diff:.3f}|×0.7 = {0.3 - abs(diff) * 0.7:.3f} → {x:.3f}")
        print(f"  П2: 0.25 - {diff:.3f}×0.6 = {0.25 - diff * 0.6:.3f} → {p2:.3f}")
        
        # Нормализация
        total = p1 + x + p2
        p1_norm = p1 / total
        x_norm = x / total
        p2_norm = p2 / total
        
        print(f"  Нормализация: {p1:.3f} + {x:.3f} + {p2:.3f} = {total:.3f}")
        print(f"  Итог: П1={p1_norm:.3f}, X={x_norm:.3f}, П2={p2_norm:.3f}")
        
        # Дополнительная информация
        print(f"\nДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:")
        print(f"  Преимущество {team1_name} в атаке: {team1_stats['attack_strength'] - team2_stats['attack_strength']:+.3f}")
        print(f"  Преимущество {team1_name} в защите: {team1_stats['defense_strength'] - team2_stats['defense_strength']:+.3f}")
        print(f"  Общее преимущество {team1_name}: {diff:+.3f}")
    
    @staticmethod
    def show_complete_calculation():
        """Полная визуализация всего процесса расчета"""
        print("ВИЗУАЛИЗАЦИЯ РАСЧЕТОВ ПРОГНОЗА С НОВЫМИ ВЕСАМИ")
        print("=" * 70)
        
        # Загрузка данных первой команды
        players1 = CalculationVisualizer.load_and_display_team_data(
            "output_with_readiness_1.json", "БРЕНТФОРД"
        )
        
        # Расчет статистик первой команды
        stats1 = CalculationVisualizer.calculate_team_stats(players1, "БРЕНТФОРД")
        
        # Загрузка данных второй команды
        players2 = CalculationVisualizer.load_and_display_team_data(
            "output_with_readiness_2.json", "ЧЕЛСИ"
        )
        
        # Расчет статистик второй команды
        stats2 = CalculationVisualizer.calculate_team_stats(players2, "ЧЕЛСИ")
        
        # Визуализация расчета матча
        CalculationVisualizer.visualize_match_calculation(stats1, stats2, "БРЕНТФОРД", "ЧЕЛСИ")
        
        print(f"\n{'='*70}")
        print("ЗАКЛЮЧЕНИЕ:")
        print("Этот визуализатор показывает расчеты с ОБНОВЛЕННЫМИ весами позиций")
        print("и исправленной формулой силы команд.")
        print("• Исправлены веса для разных амплуа")
        print("• Учтена разница в классе команд") 
        print("• Добавлены поправки на стоимость состава")
        print("• Формула силы: 30% готовность + 40% атака + 30% защита")

# ==================== ИСПОЛЬЗОВАНИЕ ВИЗУАЛИЗАТОРА ====================
if __name__ == "__main__":
    # Этот код можно запускать отдельно для проверки расчетов
    CalculationVisualizer.show_complete_calculation()


# import json
# import numpy as np
# from math import factorial, exp
# from typing import Dict, List, Optional

# def poisson_probability(mean, goals):
#     """Расчет вероятности по распределению Пуассона"""
#     return (mean ** goals) * exp(-mean) / factorial(goals)

# def calculate_exact_scores(team1: Dict, team2: Dict, max_goals=5):
#     """Расчет вероятностей точного счета"""
#     # Среднее ожидаемое количество голов для каждой команды
#     mean_team1 = 0.8 * team1["attack_strength"] / team2["defense_strength"]
#     mean_team2 = 1.2 * team2["attack_strength"] / team1["defense_strength"]
    
#     # Корректировка на домашнее поле
#     if team1["is_home"]:
#         mean_team1 *= 1.2
#         mean_team2 *= 0.9
#     else:
#         mean_team1 *= 0.9
#         mean_team2 *= 1.2
    
#     # Рассчитываем вероятности для всех возможных счетов
#     scores = {}
#     for i in range(max_goals + 1):
#         for j in range(max_goals + 1):
#             prob = poisson_probability(mean_team1, i) * poisson_probability(mean_team2, j)
#             scores[f"{i}-{j}"] = round(prob, 4)
    
#     # Нормализуем вероятности
#     total = sum(scores.values())
#     return {score: prob/total for score, prob in scores.items()}

# def load_team_data(file_path: str, is_home: bool, position_in_league: int, last_results: Optional[List[int]] = None) -> Dict:
#     """Загружает данные команды из JSON файла с расширенной аналитикой"""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         players = json.load(f)
    
#     if not players:
#         return {
#             'name': file_path.replace('.json', ''),
#             'is_home': is_home,
#             'position_in_league': position_in_league,
#             'last_results': last_results or [],
#             'players': [],
#             'avg_readiness': 0.5,
#             'attack_strength': 0.5,
#             'defense_strength': 0.5,
#             'top_attackers': []
#         }
    
#     # Рассчитываем показатели команды
#     readiness = []
#     defense = []
#     attackers = []
    
#     for player in players:
#         pos = player['position'].lower()
#         readiness.append(player['readiness'])
        
#         if 'вратарь' in pos:
#             defense.append(player['readiness'] * 1.2)  # Усиленный вес вратарей
#         elif 'защитник' in pos:
#             defense.append(player['readiness'] * 0.8)
#         elif 'нап' in pos or 'вингер' in pos:
#             attackers.append(player['readiness'])
#         elif 'полузащитник' in pos:
#             defense.append(player['readiness'] * 0.4)
#             attackers.append(player['readiness'] * 0.6)
    
#     # Топ-3 атакующих игрока (если есть)
#     top_attackers = sorted(attackers, reverse=True)[:3] if attackers else [0.3]
    
#     # Учёт формы (последние 5 матчей: 1-победа, 0-поражение, 0.5-ничья)
#     form_coefficient = 1.0
#     if last_results:
#         form_coefficient = 0.9 + (sum(last_results) / len(last_results)) * 0.2
    
#     return {
#         'name': file_path.replace('.json', ''),
#         'is_home': is_home,
#         'position_in_league': position_in_league,
#         'last_results': last_results or [],
#         'players': players,
#         'avg_readiness': np.mean(readiness) if readiness else 0.5,
#         'attack_strength': np.mean(top_attackers) * form_coefficient,
#         'defense_strength': np.mean(defense) if defense else 0.5,
#         'top_attackers': top_attackers,
#         'form_coefficient': form_coefficient
#     }

# def calculate_motivation(team: Dict, match_type: str) -> float:
#     """Усовершенствованный расчёт мотивации"""
#     base_motivation = {
#         'вылет': 0.25,
#         'еврокубки': 0.2,
#         'дерби': 0.15,
#         'кубок': 0.15,
#         'клубный_чемпионат': 0.2,
#         'обычный': 0.05
#     }.get(match_type, 0.05)
    
#     position = team.get('position_in_league', 1)
#     if position >= 18:  # Зона прямого вылета
#         base_motivation += 0.15
#     elif 16 <= position <= 17:  # Зона плей-офф вылета
#         base_motivation += 0.10
#     elif position <= 4:  # Лига чемпионов
#         base_motivation += 0.12 if match_type != 'вылет' else 0.05
#     elif 5 <= position <= 6:  # Лига Европы
#         base_motivation += 0.08
#     elif 7 <= position <= 9:  # Конференционная лига
#         base_motivation += 0.05
#     elif 10 <= position <= 15:  # Середняки
#         base_motivation += 0.02
    
#     # Учёт формы
#     if team.get('last_results'):
#         win_rate = sum(team['last_results']) / len(team['last_results'])
#         if win_rate > 0.7:
#             base_motivation += 0.05
#         elif win_rate < 0.3:
#             base_motivation -= 0.03
    
#     return min(0.35, max(0.0, base_motivation))

# def calculate_match_probabilities(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
#     """Улучшенный расчёт вероятностей с учётом всех факторов"""
#     # 1. Корректировки силы команд
#     home_advantage = 0.1 if team1["position_in_league"] < 10 else 0.05
#     weather_impact = {
#         "rain": -0.02,
#         "sunny": 0.03,
#         "windy": -0.01,
#         "snow": -0.03,
#         None: 0.0
#     }.get(weather, 0.0)
    
#     # 2. Мотивация с учётом формы
#     team1_motivation = calculate_motivation(team1, match_type)
#     team2_motivation = calculate_motivation(team2, match_type)
    
#     # 3. Итоговые показатели
#     team1_power = (
#         team1["avg_readiness"] * 0.4 +
#         team1["attack_strength"] * 0.4 +
#         team1["defense_strength"] * 0.2 +
#         home_advantage +
#         team1_motivation
#     )
    
#     team2_power = (
#         team2["avg_readiness"] * 0.4 +
#         team2["attack_strength"] * 0.4 +
#         team2["defense_strength"] * 0.2 -
#         home_advantage * 0.6 +
#         team2_motivation
#     )
    
#     # 4. Разница в силе
#     diff = (team1_power - team2_power) * (1 + weather_impact * 0.5)
    
#     # 5. Основные прогнозы
#     forecasts = {
#         "1X2": {
#             "П1": max(0.1, min(0.9, 0.45 + diff * 0.6)),
#             "X": max(0.1, min(0.9, 0.3 - abs(diff) * 0.7)),
#             "П2": max(0.1, min(0.9, 0.25 - diff * 0.6))
#         },
#         "Тоталы": {
#             ">1.5": 0.65 + (team1["attack_strength"] + team2["attack_strength"]) * 0.25 + weather_impact,
#             "<1.5": 0.35 - (team1["attack_strength"] + team2["attack_strength"]) * 0.25 - weather_impact,
#             ">2.5": 0.55 + (team1["attack_strength"] + team2["attack_strength"]) * 0.2 + weather_impact * 0.7,
#             "<2.5": 0.45 - (team1["attack_strength"] + team2["attack_strength"]) * 0.2 - weather_impact * 0.7,
#             ">3.5": 0.4 + (team1["attack_strength"] + team2["attack_strength"]) * 0.15 + weather_impact * 0.5
#         },
#         "Форы": {
#             "Ф1(-1.5)": max(0.1, 0.35 + diff * 0.4),
#             "Ф2(+1.5)": max(0.1, 0.65 - diff * 0.4),
#             "Ф1(-0.5)": max(0.1, 0.55 + diff * 0.5),
#             "Ф2(+0.5)": max(0.1, 0.45 - diff * 0.5)
#         },
#         "Обе забьют": {
#             "Да": min(0.95, max(0.05,
#                 (team1["attack_strength"] * 0.6 + team2["attack_strength"] * 0.6) * 0.6 - weather_impact * 0.1
#             )),
#             "Нет": 1 - (team1["attack_strength"] * 0.6 + team2["attack_strength"] * 0.6) * 0.6 + weather_impact * 0.1
#         },
#         "Первый гол": {
#             "1": team1["attack_strength"] / (team1["attack_strength"] + team2["attack_strength"] + 1e-10),
#             "2": team2["attack_strength"] / (team1["attack_strength"] + team2["attack_strength"] + 1e-10),
#             "Нет": 0.15
#         },
#         "Точный счет": {}
#     }
    
#     # Нормализация
#     forecasts["1X2"] = {k: v / sum(forecasts["1X2"].values()) for k, v in forecasts["1X2"].items()}
#     for market in ["Тоталы", "Форы"]:
#         forecasts[market] = {k: max(0.05, min(0.95, v)) for k, v in forecasts[market].items()}
    
#     # Учёт звёздных игроков
#     if len(team1["top_attackers"]) >= 1 and team1["top_attackers"][0] > 0.6:
#         forecasts["1X2"]["П1"] *= 1.1
#         forecasts["Тоталы"][">2.5"] *= 1.15
    
#     if len(team2["top_attackers"]) >= 1 and team2["top_attackers"][0] > 0.6:
#         forecasts["1X2"]["П2"] *= 1.1
#         forecasts["Тоталы"][">2.5"] *= 1.15
    
#     # Добавляем расчет точного счета
#     forecasts["Точный счет"] = calculate_exact_scores(team1, team2)
#     forecasts["Точный счет"] = dict(sorted(
#         forecasts["Точный счет"].items(),
#         key=lambda item: item[1],
#         reverse=True
#     )[:10])  # Топ-10 вероятных счетов
    
#     return forecasts


# if __name__ == "__main__":
#     # РУЧНОЙ ВВОД ОБЩЕЙ СТАТИСТИКИ СЕЗОНА (будет парситься из таблицы)
#     # Команда 1
#     # team1_season_stats = {
#     #     'position': 1,           # Место в лиге
#     #     'matches_played': 2,    # Всего матчей
#     #     'wins': 2,              # Побед
#     #     'draws': 0,              # Ничьих  
#     #     'losses': 0,             # Поражений
#     #     'goals_scored': 5,      # Забитых голов
#     #     'goals_conceded': 0,    # Пропущенных голов
#     #     'points': 6             # Очков
#     # }
#     team1_season_stats = {
#         'position': 15,
#         'matches_played': 1,
#         'wins': 0,
#         'draws': 1, 
#         'losses': 0,
#         'goals_scored': 0,
#         'goals_conceded': 0,
#         'points': 1          # Очков
#     }
    
#     # Команда 2  
#     team2_season_stats = {
#         'position': 5,           # Место в лиге
#         'matches_played': 1,    # Всего матчей
#         'wins': 1,              # Побед
#         'draws': 0,              # Ничьих  
#         'losses': 0,             # Поражений
#         'goals_scored': 4,      # Забитых голов
#         'goals_conceded': 2,    # Пропущенных голов
#         'points': 3             # Очков
#     }
    
#     # Расчет коэффициента формы на основе всей статистики сезона
#     def calculate_season_form(stats: Dict) -> float:
#         win_rate = stats['wins'] / stats['matches_played']
#         loss_rate = stats['losses'] / stats['matches_played']
#         goal_ratio = stats['goals_scored'] / max(1, stats['goals_conceded'])
        
#         return (win_rate * 0.5 + (1 - loss_rate) * 0.3 + min(goal_ratio, 2.0) * 0.2)
    
#     # Загрузка данных команд с общей статистикой сезона
#     team1 = load_team_data(
#         "output_with_readiness_1.json",
#         is_home=True,
#         position_in_league=team1_season_stats['position'],
#         last_results=None  # Убираем последние 5 матчей
#     )
    
#     # Добавляем общую статистику в объект команды
#     team1['season_stats'] = team1_season_stats
#     team1['form_coefficient'] = calculate_season_form(team1_season_stats)
    
#     # Пересчитываем силу атаки/обороны с учетом общей статистики
#     team1['attack_strength'] = team1['attack_strength'] * 0.7 + (team1_season_stats['goals_scored'] / team1_season_stats['matches_played'] / 3) * 0.3
#     team1['defense_strength'] = team1['defense_strength'] * 0.7 + (1 - team1_season_stats['goals_conceded'] / team1_season_stats['matches_played'] / 1.5) * 0.3
    
#     team2 = load_team_data(
#         "output_with_readiness_2.json",
#         is_home=False,
#         position_in_league=team2_season_stats['position'],
#         last_results=None  # Убираем последние 5 матчей
#     )
    
#     team2['season_stats'] = team2_season_stats
#     team2['form_coefficient'] = calculate_season_form(team2_season_stats)
#     team2['attack_strength'] = team2['attack_strength'] * 0.7 + (team2_season_stats['goals_scored'] / team2_season_stats['matches_played'] / 3) * 0.3
#     team2['defense_strength'] = team2['defense_strength'] * 0.7 + (1 - team2_season_stats['goals_conceded'] / team2_season_stats['matches_played'] / 1.5) * 0.3
    
#     # Вывод статистики для проверки
#     print("ОБЩАЯ СТАТИСТИКА СЕЗОНА:")
#     print(f"{team1['name']}: {team1_season_stats['wins']}В-{team1_season_stats['draws']}Н-{team1_season_stats['losses']}П")
#     print(f"Голы: {team1_season_stats['goals_scored']}-{team1_season_stats['goals_conceded']}")
#     print(f"{team2['name']}: {team2_season_stats['wins']}В-{team2_season_stats['draws']}Н-{team2_season_stats['losses']}П")
#     print(f"Голы: {team2_season_stats['goals_scored']}-{team2_season_stats['goals_conceded']}")
    
#     # Рассчитываем вероятности
#     forecast = calculate_match_probabilities(
#         team1=team1,
#         team2=team2,
#         weather="sunny",
#         match_type="еврокубки"
#     )
    
#     # Выводим результаты
#     print(f"\nПрогноз на матч: {team1['name']} vs {team2['name']}")
#     print(f"Рейтинг силы: {team1['name']} {team1['attack_strength']:.2f} | {team2['name']} {team2['attack_strength']:.2f}")
    
#     for market, values in forecast.items():
#         print(f"\n{market}:")
#         for bet_type, prob in values.items():
#             print(f"  {bet_type}: {prob:.4f}" if market == "Точный счет" else f"  {bet_type}: {prob:.2f}")