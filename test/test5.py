
import json
import numpy as np
from math import factorial, exp
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# ==================== МОДЕЛИ ДАННЫХ ====================
@dataclass
class SeasonStats:
    """Статистика сезона команды (пока вводится вручную)"""
    position: int              # Место в лиге
    matches_played: int        # Сыграно матчей
    wins: int                  # Побед
    draws: int                 # Ничьих
    losses: int                # Поражений
    goals_scored: int          # Забито голов
    goals_conceded: int        # Пропущено голов
    points: int                # Очков
    # TODO: Добавить парсинг этих данных из турнирной таблицы

@dataclass
class TeamTactics:
    """Тактические показатели (пока вводится вручную)"""
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
    
    def load_players_from_json(self, file_path: str):
        """Загрузка данных игроков из JSON файла"""
        with open(file_path, 'r', encoding='utf-8') as f:
            self.players = json.load(f)
    
    def calculate_player_stats(self):
        """Расчёт статистических показателей на основе игроков"""
        if not self.players:
            self.stats = {
                'avg_readiness': 0.5,
                'attack_strength': 0.5,
                'defense_strength': 0.5,
                'top_attackers': [0.3]
            }
            return
        
        readiness = []
        defense = []
        attackers = []
        
        for player in self.players:
            pos = player['position'].lower()
            readiness.append(player['readiness'])
            
            if 'вратарь' in pos:
                defense.append(player['readiness'] * 1.2)
            elif 'защитник' in pos:
                defense.append(player['readiness'] * 0.8)
            elif 'нап' in pos or 'вингер' in pos:
                attackers.append(player['readiness'])
            elif 'полузащитник' in pos:
                defense.append(player['readiness'] * 0.4)
                attackers.append(player['readiness'] * 0.6)
        
        top_attackers = sorted(attackers, reverse=True)[:3] if attackers else [0.3]
        
        self.stats = {
            'avg_readiness': np.mean(readiness) if readiness else 0.5,
            'attack_strength': np.mean(top_attackers) if top_attackers else 0.5,
            'defense_strength': np.mean(defense) if defense else 0.5,
            'top_attackers': top_attackers
        }
    
    def calculate_season_form(self) -> float:
        """Расчёт коэффициента формы на основе статистики сезона"""
        if not self.season_stats:
            return 1.0
        
        win_rate = self.season_stats.wins / self.season_stats.matches_played
        loss_rate = self.season_stats.losses / self.season_stats.matches_played
        goal_ratio = self.season_stats.goals_scored / max(1, self.season_stats.goals_conceded)
        
        return (win_rate * 0.5 + (1 - loss_rate) * 0.3 + min(goal_ratio, 2.0) * 0.2)
    
    def adjust_stats_with_season_data(self):
        """Корректировка статистик с учётом данных сезона"""
        if not self.season_stats:
            return
        
        form_coeff = self.calculate_season_form()
        
        # Корректировка силы атаки/обороны на основе реальных голов
        attack_adjustment = (self.season_stats.goals_scored / self.season_stats.matches_played / 3) * 0.3
        defense_adjustment = (1 - self.season_stats.goals_conceded / self.season_stats.matches_played / 1.5) * 0.3
        
        self.stats['attack_strength'] = self.stats['attack_strength'] * 0.7 + attack_adjustment
        self.stats['defense_strength'] = self.stats['defense_strength'] * 0.7 + defense_adjustment
        self.stats['form_coefficient'] = form_coeff

# ==================== КЛАСС РАСЧЕТА ПРОГНОЗОВ ====================
class MatchPredictor:
    def __init__(self):
        self.weather_impact = {
            "rain": -0.02, "sunny": 0.03, "windy": -0.01, "snow": -0.03, None: 0.0
        }
        self.motivation_rules = {
            'вылет': 0.25, 'еврокубки': 0.2, 'дерби': 0.15, 
            'кубок': 0.15, 'клубный_чемпионат': 0.2, 'обычный': 0.05
        }
        self.calibration_curve = self._create_calibration_curve()
    
    def _create_calibration_curve(self) -> Dict[float, float]:
        """Калибровочная кривая на основе исторических данных"""
        return {
            0.1: 0.08, 0.2: 0.18, 0.3: 0.28, 0.4: 0.38, 0.5: 0.48,
            0.6: 0.55, 0.7: 0.65, 0.8: 0.75, 0.9: 0.85
        }
    
    def calculate_motivation(self, team: FootballTeam, match_type: str) -> float:
        """Расчёт мотивации с учётом позиции в лиге"""
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
        """Расчёт вероятности по распределению Пуассона"""
        return (mean ** goals) * exp(-mean) / factorial(goals)
    
    def calculate_exact_scores(self, team1: FootballTeam, team2: FootballTeam, max_goals: int = 5) -> Dict:
        """Расчёт вероятностей точного счёта"""
        mean_team1 = 0.8 * team1.stats['attack_strength'] / team2.stats['defense_strength']
        mean_team2 = 1.2 * team2.stats['attack_strength'] / team1.stats['defense_strength']
        
        # Корректировка на домашнее поле и тактику
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
        """Калибровка вероятности на основе исторических данных"""
        rounded_prob = round(raw_prob, 1)
        return self.calibration_curve.get(rounded_prob, raw_prob)
    
    def calculate_value_bet(self, model_prob: float, bookmaker_odds: float) -> Tuple[bool, float]:
        """Определение value bet"""
        implied_prob = 1 / bookmaker_odds
        value = model_prob - implied_prob
        return value > 0.05, value
    
    def predict(self, team1: FootballTeam, team2: FootballTeam, 
               weather: str, match_type: str, bookmaker_odds: Optional[Dict] = None) -> Dict:
        """Основной метод прогнозирования"""
        
        # 1. Расчёт базовых параметров
        home_advantage = 0.1 if team1.season_stats and team1.season_stats.position < 10 else 0.05
        weather_impact = self.weather_impact.get(weather, 0.0)
        
        # 2. Мотивация команд
        team1_motivation = self.calculate_motivation(team1, match_type)
        team2_motivation = self.calculate_motivation(team2, match_type)
        
        # 3. Сила команд с учётом всех факторов
        team1_power = self._calculate_team_power(team1, home_advantage, team1_motivation)
        team2_power = self._calculate_team_power(team2, -home_advantage * 0.6, team2_motivation)
        
        diff = (team1_power - team2_power) * (1 + weather_impact * 0.5)
        
        # 4. Создание базового прогноза
        forecasts = self._create_base_forecast(team1, team2, diff, weather_impact)
        
        # 5. Применение корректировок
        self._apply_adjustments(team1, team2, forecasts)
        
        # 6. Калибровка вероятностей
        forecasts = self._calibrate_forecasts(forecasts)
        
        # 7. Добавление точных счетов
        forecasts["Точный счет"] = self.calculate_exact_scores(team1, team2)
        forecasts["Точный счет"] = dict(sorted(
            forecasts["Точный счет"].items(),
            key=lambda item: item[1],
            reverse=True
        )[:10])
        
        # 8. Анализ value bets (если есть коэффициенты БК)
        if bookmaker_odds:
            forecasts["Value Bets"] = self._find_value_bets(forecasts, bookmaker_odds)
        
        return forecasts
    
    def _calculate_team_power(self, team: FootballTeam, advantage: float, motivation: float) -> float:
        """Расчёт общей силы команды"""
        return (
            team.stats['avg_readiness'] * 0.4 +
            team.stats['attack_strength'] * 0.4 +
            team.stats['defense_strength'] * 0.2 +
            advantage +
            motivation
        )
    
    def _create_base_forecast(self, team1: FootballTeam, team2: FootballTeam, 
                             diff: float, weather_impact: float) -> Dict:
        """Создание базового прогноза"""
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
                "Да": min(0.95, max(0.05,
                    (team1.stats['attack_strength'] * 0.6 + team2.stats['attack_strength'] * 0.6) * 0.6 - weather_impact * 0.1
                )),
                "Нет": 1 - (team1.stats['attack_strength'] * 0.6 + team2.stats['attack_strength'] * 0.6) * 0.6 + weather_impact * 0.1
            }
        }
    
    def _apply_adjustments(self, team1: FootballTeam, team2: FootballTeam, forecasts: Dict):
        """Применение корректировок к прогнозу"""
        # Учёт звёздных игроков
        if team1.stats['top_attackers'] and team1.stats['top_attackers'][0] > 0.6:
            forecasts["1X2"]["П1"] *= 1.1
            forecasts["Тоталы"][">2.5"] *= 1.15
        
        if team2.stats['top_attackers'] and team2.stats['top_attackers'][0] > 0.6:
            forecasts["1X2"]["П2"] *= 1.1
            forecasts["Тоталы"][">2.5"] *= 1.15
        
        # TODO: Добавить корректировки на тактику и психологические факторы
    
    def _calibrate_forecasts(self, forecasts: Dict) -> Dict:
        """Калибровка всех вероятностей"""
        calibrated = {}
        for market, values in forecasts.items():
            if isinstance(values, dict):
                calibrated[market] = {k: self.calibrate_probability(v) for k, v in values.items()}
            else:
                calibrated[market] = values
        return calibrated
    
    def _find_value_bets(self, forecasts: Dict, bookmaker_odds: Dict) -> Dict:
        """Поиск value bets"""
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

# ==================== КЛАСС ДЛЯ УПРАВЛЕНИЯ БАНКРОЛЛОМ ====================
class BankrollManager:
    """Управление банкроллом по критерию Келли"""
    
    @staticmethod
    def kelly_criterion(prob: float, odds: float, bankroll: float) -> float:
        """Расчёт размера ставки по критерию Келли"""
        b = odds - 1
        q = 1 - prob
        fraction = (b * prob - q) / b
        return max(0, fraction) * bankroll * 0.5  # Пол-Келли для консервативности
    
    def calculate_stake_sizes(self, forecasts: Dict, bankroll: float, bookmaker_odds: Dict) -> Dict:
        """Расчёт размеров ставок для всех рынков"""
        stakes = {}
        for market, values in forecasts.items():
            if market in bookmaker_odds:
                for bet_type, model_prob in values.items():
                    if bet_type in bookmaker_odds[market]:
                        stake = self.kelly_criterion(
                            model_prob, 
                            bookmaker_odds[market][bet_type], 
                            bankroll
                        )
                        stakes[f"{market}_{bet_type}"] = stake
        return stakes

# ==================== ИСПОЛЬЗОВАНИЕ ====================
if __name__ == "__main__":
    # Инициализация команд
    team1 = FootballTeam("Команда 1", is_home=True)
    team2 = FootballTeam("Команда 2", is_home=False)
    
    # ЗАГРУЗКА ДАННЫХ ИГРОКОВ ИЗ JSON
    team1.load_players_from_json("output_with_readiness_1.json")
    team2.load_players_from_json("output_with_readiness_2.json")
    
  # РУЧНОЙ ВВОД СТАТИСТИКИ СЕЗОНА (будет парситься)
    team1.season_stats = SeasonStats(
        position=3, matches_played=36, wins=17, draws=8, losses=10,
        goals_scored=56, goals_conceded=49, points=60
    )
    
    team2.season_stats = SeasonStats(
        position=6, matches_played=36, wins=14, draws=13, losses=9,
        goals_scored=39, goals_conceded=30, points=55
    )
    
    # РУЧНОЙ ВВОД ТАКТИКИ (будет парситься)
    team1.tactics = TeamTactics(
        formation="3-4-3", possession_avg=0.5, press_intensity="medium",
        transition_speed=0.5, cross_accuracy=0.38, long_shots_per_match=5
    )
    
    team2.tactics = TeamTactics(
        formation="3-4-3", possession_avg=0.5, press_intensity="medium",
        transition_speed=0.5, cross_accuracy=0.38, long_shots_per_match=5
    )
    
    # Расчёт статистик
    team1.calculate_player_stats()
    team2.calculate_player_stats()
    team1.adjust_stats_with_season_data()
    team2.adjust_stats_with_season_data()
    
    # Коэффициенты букмекеров (пример)
    bookmaker_odds = {
        "1X2": {"П1": 3.5, "X": 3.2, "П2": 2.1},
        "Тоталы": {">2.5": 1.9, "<2.5": 1.9},
        "Форы": {"Ф1(-1.5)": 4.0, "Ф2(+1.5)": 1.3}
    }
    
    # Создание прогноза
    predictor = MatchPredictor()
    forecast = predictor.predict(team1, team2, "sunny", "еврокубки", bookmaker_odds)
    
    # Управление банкроллом
    bankroll_manager = BankrollManager()
    stakes = bankroll_manager.calculate_stake_sizes(forecast, 10000, bookmaker_odds)
    
    # Вывод результатов
    print("ПРОГНОЗ НА МАТЧ:")
    for market, values in forecast.items():
        print(f"\n{market}:")
        for bet_type, prob in values.items():
            print(f"  {bet_type}: {prob:.3f}")
    
    print("\nРЕКОМЕНДУЕМЫЕ СТАВКИ:")
    for bet, stake in stakes.items():
        print(f"  {bet}: {stake:.0f}₽")