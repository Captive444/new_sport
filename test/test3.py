import json
import numpy as np
from math import factorial, exp
from typing import Dict, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

# ==================== БАЗОВЫЕ КЛАССЫ ====================
class DataLoader(ABC):
    """Абстрактный класс для загрузки данных"""
    @abstractmethod
    def load_data(self, file_path: str) -> Dict:
        pass

class TeamAnalyzer(ABC):
    """Абстрактный класс для анализа команд"""
    @abstractmethod
    def analyze_team(self, team_data: Dict) -> Dict:
        pass

# ==================== МОДЕЛИ ДАННЫХ ====================
@dataclass
class Player:
    """Модель игрока"""
    name: str
    position: str
    readiness: float
    # Дополнительные поля для парсинга:
    # goals: int = 0
    # assists: int = 0
    # minutes_played: int = 0

@dataclass
class TeamTactics:
    """Тактические показатели команды (заполнять вручную/парсить)"""
    formation: str = "4-3-3"
    possession_avg: float = 0.55  # Среднее владение мячом
    press_intensity: str = "medium"  # low/medium/high
    transition_speed: float = 0.7  # Скорость контратак
    cross_accuracy: float = 0.35  # Точность навесов
    long_shots_per_match: float = 5.1  # Дальние удары за матч

@dataclass
class TeamStats:
    """Статистические показатели команды"""
    attack_strength: float
    defense_strength: float
    avg_readiness: float
    form_coefficient: float
    top_attackers: List[float]

# ==================== ОСНОВНОЙ КЛАСС КОМАНДЫ ====================
class FootballTeam:
    def __init__(self, name: str, is_home: bool, position_in_league: int):
        self.name = name
        self.is_home = is_home
        self.position_in_league = position_in_league
        self.players: List[Player] = []
        self.last_results: List[float] = []
        self.tactics: TeamTactics = TeamTactics()  # Заполняется отдельно
        self.stats: Optional[TeamStats] = None
    
    def calculate_stats(self):
        """Расчет статистических показателей команды"""
        if not self.players:
            self.stats = TeamStats(0.5, 0.5, 0.5, 1.0, [0.3])
            return
        
        readiness = []
        defense = []
        attackers = []
        
        for player in self.players:
            pos = player.position.lower()
            readiness.append(player.readiness)
            
            if 'вратарь' in pos:
                defense.append(player.readiness * 1.2)
            elif 'защитник' in pos:
                defense.append(player.readiness * 0.8)
            elif 'нап' in pos or 'вингер' in pos:
                attackers.append(player.readiness)
            elif 'полузащитник' in pos:
                defense.append(player.readiness * 0.4)
                attackers.append(player.readiness * 0.6)
        
        top_attackers = sorted(attackers, reverse=True)[:3] if attackers else [0.3]
        form_coeff = 0.9 + (sum(self.last_results) / len(self.last_results)) * 0.2 if self.last_results else 1.0
        
        self.stats = TeamStats(
            attack_strength=np.mean(top_attackers) * form_coeff,
            defense_strength=np.mean(defense) if defense else 0.5,
            avg_readiness=np.mean(readiness) if readiness else 0.5,
            form_coefficient=form_coeff,
            top_attackers=top_attackers
        )
    
    def calculate_style_coefficients(self) -> Dict:
        """Расчет коэффициентов стиля игры"""
        if not hasattr(self, 'tactics'):
            return {}
        
        return {
            'attack_pressure': 0.3 * (1 if self.tactics.press_intensity == 'high' else 0.6) + 
                             0.2 * self.tactics.possession_avg,
            'defense_solidity': 0.4 * (1 - self.tactics.transition_speed) + 
                              0.3 * (1 - self.tactics.possession_avg),
            'total_goals_impact': 0.5 * self.tactics.transition_speed + 
                                0.2 * (self.tactics.long_shots_per_match / 10),
            'counter_attack_danger': 0.7 * (1 - self.tactics.possession_avg) + 
                                   0.3 * self.tactics.transition_speed
        }

# ==================== КЛАСС ДЛЯ ЗАГРУЗКИ ДАННЫХ ====================
class JSONDataLoader(DataLoader):
    def load_data(self, file_path: str) -> Dict:
        """Загрузка данных из JSON файла"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

class TeamDataProcessor:
    """Обработчик данных команды"""
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
    
    def create_team_from_file(self, file_path: str, is_home: bool, 
                            position_in_league: int, last_results: List[float]) -> FootballTeam:
        """Создание объекта команды из файла"""
        data = self.data_loader.load_data(file_path)
        team_name = file_path.replace('.json', '')
        team = FootballTeam(team_name, is_home, position_in_league)
        team.last_results = last_results
        
        # Загрузка игроков
        team.players = [
            Player(
                name=player['name'],
                position=player['position'],
                readiness=player['readiness']
            ) for player in data
        ]
        
        # TODO: Загрузить тактику из отдельного файла
        # team.tactics = self.load_tactics(f"tactics_{team_name}.json")
        
        team.calculate_stats()
        return team
    
    def load_tactics(self, tactics_file: str) -> TeamTactics:
        """Загрузка тактических данных (реализовать позже)"""
        # Пример ручного заполнения:
        return TeamTactics(
            formation="4-3-3",
            possession_avg=0.55,
            press_intensity="high",
            transition_speed=0.7,
            cross_accuracy=0.35,
            long_shots_per_match=5.1
        )

# ==================== КЛАСС ДЛЯ РАСЧЕТА ПРОГНОЗОВ ====================
class MatchPredictor:
    """Класс для расчета прогнозов матча"""
    
    def __init__(self):
        self.weather_impact = {
            "rain": -0.02, "sunny": 0.03, "windy": -0.01, "snow": -0.03, None: 0.0
        }
        self.motivation_rules = {
            'вылет': 0.25, 'еврокубки': 0.2, 'дерби': 0.15, 
            'кубок': 0.15, 'клубный_чемпионат': 0.2, 'обычный': 0.05
        }
    
    def calculate_motivation(self, team: FootballTeam, match_type: str) -> float:
        """Расчет мотивации команды"""
        base_motivation = self.motivation_rules.get(match_type, 0.05)
        position = team.position_in_league
        
        if position >= 18: base_motivation += 0.15
        elif 16 <= position <= 17: base_motivation += 0.10
        elif position <= 4: base_motivation += 0.12 if match_type != 'вылет' else 0.05
        elif 5 <= position <= 6: base_motivation += 0.08
        elif 7 <= position <= 9: base_motivation += 0.05
        elif 10 <= position <= 15: base_motivation += 0.02
        
        if team.last_results:
            win_rate = sum(team.last_results) / len(team.last_results)
            if win_rate > 0.7: base_motivation += 0.05
            elif win_rate < 0.3: base_motivation -= 0.03
        
        return min(0.35, max(0.0, base_motivation))
    
    def poisson_probability(self, mean, goals):
        """Расчет вероятности по Пуассону"""
        return (mean ** goals) * exp(-mean) / factorial(goals)
    
    def calculate_exact_scores(self, team1: FootballTeam, team2: FootballTeam, max_goals=5) -> Dict:
        """Расчет точных счетов"""
        mean_team1 = 0.8 * team1.stats.attack_strength / team2.stats.defense_strength
        mean_team2 = 1.2 * team2.stats.attack_strength / team1.stats.defense_strength
        
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
    
    def predict(self, team1: FootballTeam, team2: FootballTeam, 
               weather: str, match_type: str) -> Dict:
        """Основной метод прогнозирования"""
        # 1. Базовые расчеты
        home_advantage = 0.1 if team1.position_in_league < 10 else 0.05
        weather_impact = self.weather_impact.get(weather, 0.0)
        
        # 2. Мотивация
        team1_motivation = self.calculate_motivation(team1, match_type)
        team2_motivation = self.calculate_motivation(team2, match_type)
        
        # 3. Сила команд
        team1_power = (
            team1.stats.avg_readiness * 0.4 +
            team1.stats.attack_strength * 0.4 +
            team1.stats.defense_strength * 0.2 +
            home_advantage +
            team1_motivation
        )
        
        team2_power = (
            team2.stats.avg_readiness * 0.4 +
            team2.stats.attack_strength * 0.4 +
            team2.stats.defense_strength * 0.2 -
            home_advantage * 0.6 +
            team2_motivation
        )
        
        diff = (team1_power - team2_power) * (1 + weather_impact * 0.5)
        
        # 4. Базовый прогноз
        forecasts = self._create_base_forecast(team1, team2, diff, weather_impact)
        
        # 5. Корректировки
        self._apply_star_players_adjustment(team1, team2, forecasts)
        self._apply_style_adjustment(team1, team2, forecasts)
        
        # 6. Точные счета
        forecasts["Точный счет"] = self.calculate_exact_scores(team1, team2)
        forecasts["Точный счет"] = dict(sorted(
            forecasts["Точный счет"].items(),
            key=lambda item: item[1],
            reverse=True
        )[:10])
        
        return forecasts
    
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
                ">1.5": 0.65 + (team1.stats.attack_strength + team2.stats.attack_strength) * 0.25 + weather_impact,
                "<1.5": 0.35 - (team1.stats.attack_strength + team2.stats.attack_strength) * 0.25 - weather_impact,
                ">2.5": 0.55 + (team1.stats.attack_strength + team2.stats.attack_strength) * 0.2 + weather_impact * 0.7,
                "<2.5": 0.45 - (team1.stats.attack_strength + team2.stats.attack_strength) * 0.2 - weather_impact * 0.7,
                ">3.5": 0.4 + (team1.stats.attack_strength + team2.stats.attack_strength) * 0.15 + weather_impact * 0.5
            },
            "Форы": {
                "Ф1(-1.5)": max(0.1, 0.35 + diff * 0.4),
                "Ф2(+1.5)": max(0.1, 0.65 - diff * 0.4),
                "Ф1(-0.5)": max(0.1, 0.55 + diff * 0.5),
                "Ф2(+0.5)": max(0.1, 0.45 - diff * 0.5)
            },
            "Обе забьют": {
                "Да": min(0.95, max(0.05,
                    (team1.stats.attack_strength * 0.6 + team2.stats.attack_strength * 0.6) * 0.6 - weather_impact * 0.1
                )),
                "Нет": 1 - (team1.stats.attack_strength * 0.6 + team2.stats.attack_strength * 0.6) * 0.6 + weather_impact * 0.1
            },
            "Первый гол": {
                "1": team1.stats.attack_strength / (team1.stats.attack_strength + team2.stats.attack_strength + 1e-10),
                "2": team2.stats.attack_strength / (team1.stats.attack_strength + team2.stats.attack_strength + 1e-10),
                "Нет": 0.15
            }
        }
    
    def _apply_star_players_adjustment(self, team1: FootballTeam, team2: FootballTeam, forecasts: Dict):
        """Корректировка на звёздных игроков"""
        if team1.stats.top_attackers and team1.stats.top_attackers[0] > 0.6:
            forecasts["1X2"]["П1"] *= 1.1
            forecasts["Тоталы"][">2.5"] *= 1.15
        
        if team2.stats.top_attackers and team2.stats.top_attackers[0] > 0.6:
            forecasts["1X2"]["П2"] *= 1.1
            forecasts["Тоталы"][">2.5"] *= 1.15
    
    def _apply_style_adjustment(self, team1: FootballTeam, team2: FootballTeam, forecasts: Dict):
        """Корректировка на стиль игры (будет расширяться)"""
        # TODO: Добавить логику из предыдущего примера
        pass

# ==================== КЛАСС ДЛЯ ВЫВОДА РЕЗУЛЬТАТОВ ====================
class ResultPrinter:
    """Класс для красивого вывода результатов"""
    
    @staticmethod
    def print_forecast(team1: FootballTeam, team2: FootballTeam, forecast: Dict):
        """Вывод прогноза"""
        print(f"\nПрогноз на матч: {team1.name} vs {team2.name}")
        print(f"Рейтинг силы: {team1.name} {team1.stats.attack_strength:.2f} | {team2.name} {team2.stats.attack_strength:.2f}")
        
        for market, values in forecast.items():
            print(f"\n{market}:")
            for bet_type, prob in values.items():
                print(f"  {bet_type}: {prob:.4f}" if market == "Точный счет" else f"  {bet_type}: {prob:.2f}")

# ==================== ИСПОЛЬЗОВАНИЕ ====================
if __name__ == "__main__":
    # Инициализация компонентов
    data_loader = JSONDataLoader()
    data_processor = TeamDataProcessor(data_loader)
    predictor = MatchPredictor()
    printer = ResultPrinter()
    
    # Загрузка команд
    team1 = data_processor.create_team_from_file(
        "output_with_readiness_1.json",
        is_home=True,
        position_in_league=1,
        last_results=[1, 1, 0.5, 0.5, 0.5]
    )
    
    team2 = data_processor.create_team_from_file(
        "output_with_readiness_2.json",
        is_home=False,
        position_in_league=13,
        last_results=[0, 0, 0, 0.5, 0]
    )
    
    # Расчет прогноза
    forecast = predictor.predict(
        team1=team1,
        team2=team2,
        weather="sunny",
        match_type="еврокубки"
    )
    
    # Вывод результатов
    printer.print_forecast(team1, team2, forecast)