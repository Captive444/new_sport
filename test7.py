import json
import numpy as np
from math import factorial, exp
from typing import Dict, List, Optional, Tuple

def poisson_probability(mean, goals):
    """Расчет вероятности по распределению Пуассона"""
    return (mean ** goals) * exp(-mean) / factorial(goals)

def calculate_dynamic_attack(team: Dict, opponent: Dict) -> float:
    """Динамический расчет атаки с учетом соперника"""
    base_attack = team["attack_power"]
    
    # Усиление атаки против слабой защиты
    defense_multiplier = 1.0 + (0.5 - opponent["defense_power"]) * 0.8
    
    # Учет формы (последние 5 матчей)
    form_boost = 1.0
    if team.get('last_results'):
        recent_goals = sum(team['last_results'])  # предполагаем, что результаты связаны с голами
        form_boost = 0.8 + (recent_goals / len(team['last_results'])) * 0.4
    
    # Учет мотивации для атаки
    motivation_boost = 1.0 + team.get('motivation', 0) * 2
    
    return base_attack * defense_multiplier * form_boost * motivation_boost

def calculate_goal_efficiency(team1: Dict, team2: Dict) -> Dict:
    """Расчет реальной голевой эффективности"""
    
    # Динамическая сила атаки против конкретной защиты
    team1_goal_potential = calculate_dynamic_attack(team1, team2)
    team2_goal_potential = calculate_dynamic_attack(team2, team1)
    
    # Корректировка на домашнее поле
    if team1["is_home"]:
        team1_goal_potential *= 1.3
        team2_goal_potential *= 0.9
    else:
        team1_goal_potential *= 0.9
        team2_goal_potential *= 1.3
    
    # Учет звездных игроков (могут решить матч)
    if team1["top_attackers"] and team1["top_attackers"][0] > 0.7:
        team1_goal_potential *= 1.25
    
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.7:
        team2_goal_potential *= 1.25
    
    return {
        "team1_goals": max(0.3, team1_goal_potential),
        "team2_goals": max(0.3, team2_goal_potential)
    }

def calculate_both_teams_to_score(team1: Dict, team2: Dict) -> float:
    """Улучшенный расчет 'Обе забьют'"""
    
    # Вероятность, что команда 1 забьет команде 2
    team1_scores = team1["attack_power"] * (1.3 - team2["defense_power"])
    
    # Вероятность, что команда 2 забьет команде 1  
    team2_scores = team2["attack_power"] * (1.3 - team1["defense_power"])
    
    # Общая вероятность, что обе забьют
    both_score_prob = team1_scores * team2_scores * 1.2
    
    # Корректировка на стиль команд
    if team1["characteristics"]["style"] == "атакующая" and team2["characteristics"]["style"] == "атакующая":
        both_score_prob *= 1.3
    elif team1["characteristics"]["style"] == "оборонительная" and team2["characteristics"]["style"] == "оборонительная":
        both_score_prob *= 0.7
    
    return min(0.85, max(0.15, both_score_prob))

def detect_upset_potential(team1: Dict, team2: Dict) -> Dict:
    """Обнаружение потенциала для неожиданного результата"""
    
    upset_factors = {
        "strong_attack_vs_weak_defense": False,
        "motivation_disparity": False,
        "star_player_impact": False,
        "recent_form_gap": False
    }
    
    # Сильная атака против слабой защиты
    if team2["attack_power"] > team1["defense_power"] * 1.4:
        upset_factors["strong_attack_vs_weak_defense"] = True
    
    # Разница в мотивации
    motivation_diff = abs(team1.get('motivation', 0) - team2.get('motivation', 0))
    if motivation_diff > 0.1:
        upset_factors["motivation_disparity"] = True
    
    # Влияние звездных игроков
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.75:
        upset_factors["star_player_impact"] = True
    
    # Разница в форме
    if team1.get('last_results') and team2.get('last_results'):
        form1 = sum(team1['last_results']) / len(team1['last_results'])
        form2 = sum(team2['last_results']) / len(team2['last_results'])
        if form2 > form1 * 1.5:
            upset_factors["recent_form_gap"] = True
    
    return upset_factors

def calculate_exact_scores_dynamic(team1: Dict, team2: Dict, mean_goals_team1: float, mean_goals_team2: float, max_goals=5):
    """Расчет точных счетов на основе динамических средних голов"""
    
    # Гарантируем минимальную продуктивность
    mean_goals_team1 = max(0.4, mean_goals_team1)
    mean_goals_team2 = max(0.4, mean_goals_team2)
    
    scores = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_probability(mean_goals_team1, i) * poisson_probability(mean_goals_team2, j)
            scores[f"{i}-{j}"] = round(prob, 4)
    
    total = sum(scores.values())
    return {score: prob/total for score, prob in scores.items()}

def calculate_1x2_from_poisson(exact_scores: Dict) -> Dict:
    """Расчет 1X2 на основе точных счетов"""
    p1 = 0.0
    draw = 0.0
    p2 = 0.0
    
    for score, prob in exact_scores.items():
        home_goals, away_goals = map(int, score.split('-'))
        if home_goals > away_goals:
            p1 += prob
        elif home_goals == away_goals:
            draw += prob
        else:
            p2 += prob
    
    return {"П1": p1, "X": draw, "П2": p2}

def calculate_totals_from_poisson(exact_scores: Dict) -> Dict:
    """Расчет тоталов на основе точных счетов"""
    over_15 = 0.0
    over_25 = 0.0
    
    for score, prob in exact_scores.items():
        home_goals, away_goals = map(int, score.split('-'))
        total_goals = home_goals + away_goals
        
        if total_goals > 1.5:
            over_15 += prob
        if total_goals > 2.5:
            over_25 += prob
    
    return {
        ">1.5": over_15,
        "<1.5": 1 - over_15,
        ">2.5": over_25,
        "<2.5": 1 - over_25
    }

def calculate_individual_totals(mean_goals_team1: float, mean_goals_team2: float) -> Dict:
    """Расчет индивидуальных тоталов"""
    # Вероятность, что команда забьет больше 1.5 голов
    itb1_15 = 1 - (poisson_probability(mean_goals_team1, 0) + poisson_probability(mean_goals_team1, 1))
    itb2_15 = 1 - (poisson_probability(mean_goals_team2, 0) + poisson_probability(mean_goals_team2, 1))
    
    return {
        "ИТБ1 1.5": max(0.05, min(0.95, itb1_15)),
        "ИТМ1 1.5": max(0.05, min(0.95, 1 - itb1_15)),
        "ИТБ2 1.5": max(0.05, min(0.95, itb2_15)),
        "ИТМ2 1.5": max(0.05, min(0.95, 1 - itb2_15))
    }

def calculate_team_strengths(players: List[Dict]) -> Tuple[float, float, float, List[float]]:
    """Расчет силы команды по позициям"""
    if not players:
        return 0.5, 0.5, 0.5, [0.3]
    
    goalkeepers = []
    defenders = []
    midfielders = []
    attackers = []
    
    for player in players:
        pos = player['position'].lower()
        readiness = player['readiness']
        
        if 'вратарь' in pos:
            goalkeepers.append(readiness * 1.3)
        elif 'защитник' in pos:
            defenders.append(readiness * 0.9)
        elif 'нап' in pos or 'вингер' in pos or 'форвард' in pos:
            attackers.append(readiness * 1.1)
        elif 'полузащитник' in pos or 'хав' in pos:
            midfielders.append(readiness * 0.7)
            attackers.append(readiness * 0.4)
        else:
            midfielders.append(readiness * 0.6)
            attackers.append(readiness * 0.4)
    
    # Расчет общей готовности
    all_players = goalkeepers + defenders + midfielders + attackers
    avg_readiness = np.mean(all_players) if all_players else 0.5
    
    # Расчет силы атаки
    attacking_players = sorted(attackers, reverse=True)[:3]
    if midfielders:
        attacking_players.append(np.mean(midfielders) * 0.6)
    attack_power = np.mean(attacking_players) if attacking_players else 0.3
    
    # Расчет силы защиты
    defense_players = goalkeepers + defenders
    if midfielders:
        defense_players.append(np.mean(midfielders) * 0.4)
    defense_power = np.mean(defense_players) if defense_players else 0.5
    
    # Топ-атакующие
    top_attackers = sorted(attackers, reverse=True)[:3]
    
    return avg_readiness, attack_power, defense_power, top_attackers




def analyze_team_characteristics(team: Dict) -> Dict:
    """Анализ характеристик команды"""
    readiness = team["avg_readiness"]
    attack = team["attack_power"]
    defense = team["defense_power"]
    
    characteristics = {
        "style": "",
        "attack_level": "",
        "defense_level": "",
        "balance": "",
        "weaknesses": [],
        "strengths": []
    }
    
    # Определение стиля
    attack_ratio = attack / (defense + 0.1)
    if attack_ratio > 1.3:
        characteristics["style"] = "атакующая"
    elif attack_ratio < 0.8:
        characteristics["style"] = "оборонительная"
    else:
        characteristics["style"] = "сбалансированная"
    
    # Уровень атаки
    if attack > 0.7:
        characteristics["attack_level"] = "сильная"
        characteristics["strengths"].append("эффективная атака")
    elif attack < 0.4:
        characteristics["attack_level"] = "слабая"
        characteristics["weaknesses"].append("проблемы в атаке")
    else:
        characteristics["attack_level"] = "средняя"
    
    # Уровень защиты
    if defense > 0.7:
        characteristics["defense_level"] = "надежная"
        characteristics["strengths"].append("крепкая защита")
    elif defense < 0.4:
        characteristics["defense_level"] = "уязвимая"
        characteristics["weaknesses"].append("слабая оборона")
    else:
        characteristics["defense_level"] = "стабильная"
    
    # Баланс команды
    total_power = attack + defense
    if total_power > 1.4:
        characteristics["balance"] = "сильная команда"
    elif total_power < 0.8:
        characteristics["balance"] = "слабая команда"
    else:
        characteristics["balance"] = "середняк"
    
    # Анализ звездных игроков
    if team["top_attackers"] and team["top_attackers"][0] > 0.7:
        characteristics["strengths"].append("есть звездный игрок")
    
    if readiness < 0.4:
        characteristics["weaknesses"].append("низкая готовность")
    
    return characteristics

def calculate_motivation(team: Dict, match_type: str) -> float:
    """Расчет мотивации команды"""
    base_motivation = {
        'вылет': 0.20,
        'еврокубки': 0.15,
        'дерби': 0.12,
        'кубок': 0.10,
        'обычный': 0.03
    }.get(match_type, 0.03)
    
    position = team.get('position_in_league', 1)
    
    # Мотивация в зависимости от положения в таблице
    if position >= 16:
        base_motivation += 0.12
    elif position <= 4:
        base_motivation += 0.10
    elif position <= 6:
        base_motivation += 0.07
    elif position <= 8:
        base_motivation += 0.04
    
    # Учет формы
    if team.get('last_results'):
        win_rate = sum(team['last_results']) / len(team['last_results'])
        if win_rate > 0.6:
            base_motivation += 0.04
        elif win_rate < 0.2:
            base_motivation -= 0.03
    
    return min(0.25, max(0.0, base_motivation))

def analyze_matchup(team1: Dict, team2: Dict) -> Dict:
    """Анализ противостояния команд"""
    analysis = {
        "style_matchup": "",
        "key_advantages": [],
        "potential_weaknesses": [],
        "expected_dynamics": "",
        "betting_insights": []
    }
    
    # Анализ стилей
    style1 = team1["characteristics"]["style"]
    style2 = team2["characteristics"]["style"]
    analysis["style_matchup"] = f"{style1} vs {style2}"
    
    # Ключевые преимущества
    if team1["attack_power"] > team2["defense_power"] * 1.4:
        analysis["key_advantages"].append(f"{team1['name']} имеет атакующее преимущество")
        analysis["betting_insights"].append("ИТБ1 1.5")
    
    if team2["attack_power"] > team1["defense_power"] * 1.4:
        analysis["key_advantages"].append(f"{team2['name']} может быть опасна в атаке")
        analysis["betting_insights"].append("ИТБ2 1.5")
    
    # Анализ слабостей
    if team1["defense_power"] < 0.4:
        analysis["potential_weaknesses"].append(f"У {team1['name']} проблемы в защите")
    
    if team2["defense_power"] < 0.4:
        analysis["potential_weaknesses"].append(f"У {team2['name']} слабая оборона")
    
    # Ожидаемая динамика матча
    total_attack = team1["attack_power"] + team2["attack_power"]
    if total_attack > 1.2:
        analysis["expected_dynamics"] = "атакующий матч с голами"
        analysis["betting_insights"].append("Тотал больше 2.5")
    elif total_attack < 0.8:
        analysis["expected_dynamics"] = "оборонительный матч"
        analysis["betting_insights"].append("Тотал меньше 2.5")
    else:
        analysis["expected_dynamics"] = "уравновешенная игра"
    
    # Домашнее преимущество
    if team1["is_home"]:
        analysis["key_advantages"].append(f"{team1['name']} играет дома")
    
    return analysis

def load_team_data(file_path: str, is_home: bool, position_in_league: int, 
                   last_results: Optional[List[int]] = None) -> Dict:
    """Загрузка и анализ данных команды"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            players = json.load(f)
    except:
        players = []
    
    # Расчет основных показателей
    avg_readiness, attack_power, defense_power, top_attackers = calculate_team_strengths(players)
    
    # Учет формы
    if last_results:
        form_coefficient = 0.85 + (sum(last_results) / len(last_results)) * 0.3
    else:
        form_coefficient = 1.0
    
    team_data = {
        'name': file_path.replace('.json', '').replace('output_with_readiness_', 'Команда '),
        'is_home': is_home,
        'position_in_league': position_in_league,
        'last_results': last_results or [],
        'players': players,
        'avg_readiness': avg_readiness,
        'attack_power': attack_power * form_coefficient,
        'defense_power': defense_power * form_coefficient,
        'top_attackers': top_attackers,
        'form_coefficient': form_coefficient
    }
    
    # Добавляем анализ характеристик
    team_data['characteristics'] = analyze_team_characteristics(team_data)
    
    return team_data

def calculate_match_probabilities(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
    """ПЕРЕПИСАННЫЙ расчет вероятностей с динамическим подходом"""
    
    # Расчет мотивации
    team1_motivation = calculate_motivation(team1, match_type)
    team2_motivation = calculate_motivation(team2, match_type)
    team1['motivation'] = team1_motivation
    team2['motivation'] = team2_motivation
    
    # 1. Динамический расчет голевого потенциала
    goal_potential = calculate_goal_efficiency(team1, team2)
    
    # 2. Детектор сенсаций
    upset_potential = detect_upset_potential(team1, team2)
    
    # 3. Расчет точных счетов через Пуассон
    exact_scores = calculate_exact_scores_dynamic(
        team1, team2, 
        goal_potential["team1_goals"], 
        goal_potential["team2_goals"]
    )
    
    # 4. Основные рынки на основе реальной силы
    forecasts = {
        "1X2": calculate_1x2_from_poisson(exact_scores),
        "Тоталы": calculate_totals_from_poisson(exact_scores),
        "Обе забьют": {
            "Да": calculate_both_teams_to_score(team1, team2),
            "Нет": 1 - calculate_both_teams_to_score(team1, team2)
        },
        "Индивидуальные тоталы": calculate_individual_totals(
            goal_potential["team1_goals"], 
            goal_potential["team2_goals"]
        ),
        "Точный счет": dict(sorted(exact_scores.items(), key=lambda x: x[1], reverse=True)[:10]),
        "Анализ матча": {
            **analyze_matchup(team1, team2),
            "upset_alert": any(upset_potential.values()),
            "upset_factors": upset_potential,
            "goal_potential": goal_potential
        }
    }
    
    return forecasts

def print_detailed_analysis(forecast, team1, team2):
    """Детальный вывод анализа матча"""
    print(f"\n{'='*60}")
    print(f"📊 ДЕТАЛЬНЫЙ АНАЛИЗ МАТЧА: {team1['name']} vs {team2['name']}")
    print(f"{'='*60}")
    
    print(f"\n🏆 РЕЙТИНГ СИЛЫ:")
    print(f"{team1['name']}: {team1['attack_power']:.2f} (атака) / {team1['defense_power']:.2f} (защита)")
    print(f"{team2['name']}: {team2['attack_power']:.2f} (атака) / {team2['defense_power']:.2f} (защита)")
    
    goal_potential = forecast["Анализ матча"]["goal_potential"]
    print(f"\n🎯 ОЖИДАЕМАЯ ГОЛЕВАЯ ЭФФЕКТИВНОСТЬ:")
    print(f"{team1['name']}: {goal_potential['team1_goals']:.2f} ожидаемых голов")
    print(f"{team2['name']}: {goal_potential['team2_goals']:.2f} ожидаемых голов")
    
    print(f"\n🎯 СТИЛЬ КОМАНД:")
    print(f"{team1['name']}: {team1['characteristics']['style']} ({team1['characteristics']['attack_level']} атака, {team1['characteristics']['defense_level']} защита)")
    print(f"{team2['name']}: {team2['characteristics']['style']} ({team2['characteristics']['attack_level']} атака, {team2['characteristics']['defense_level']} защита)")
    
    print(f"\n🔍 КЛЮЧЕВЫЕ ФАКТОРЫ:")
    analysis = forecast["Анализ матча"]
    print(f"Стилевое противостояние: {analysis['style_matchup']}")
    print(f"Ожидаемая динамика: {analysis['expected_dynamics']}")
    
    if analysis["upset_alert"]:
        print(f"🚨 ВНИМАНИЕ: Возможна сенсация!")
        for factor, active in analysis["upset_factors"].items():
            if active:
                print(f"   • {factor}")
    
    if analysis["key_advantages"]:
        print("\n✅ ПРЕИМУЩЕСТВА:")
        for advantage in analysis["key_advantages"]:
            print(f"  • {advantage}")
    
    if analysis["potential_weaknesses"]:
        print("\n⚠️ СЛАБЫЕ СТОРОНЫ:")
        for weakness in analysis["potential_weaknesses"]:
            print(f"  • {weakness}")
    
    print(f"\n💡 СТАТИСТИЧЕСКИЕ ВЫВОДЫ:")
    for insight in analysis["betting_insights"]:
        print(f"  • {insight}")

def print_forecasts(forecast):
    """Вывод прогнозов"""
    print(f"\n📈 ПРОГНОЗЫ НА МАТЧ:")
    
    print(f"\n1X2:")
    for bet_type, prob in forecast["1X2"].items():
        print(f"  {bet_type}: {prob:.2f}")
    
    print(f"\nТОТАЛЫ:")
    for bet_type, prob in forecast["Тоталы"].items():
        print(f"  {bet_type}: {prob:.2f}")
    
    print(f"\nОБЕ ЗАБЬЮТ:")
    for bet_type, prob in forecast["Обе забьют"].items():
        print(f"  {bet_type}: {prob:.2f}")
    
    print(f"\nИНДИВИДУАЛЬНЫЕ ТОТАЛЫ:")
    for bet_type, prob in forecast["Индивидуальные тоталы"].items():
        print(f"  {bet_type}: {prob:.2f}")
    
    print(f"\nТОЧНЫЙ СЧЕТ (ТОП-5):")
    for score, prob in list(forecast["Точный счет"].items())[:5]:
        print(f"  {score}: {prob:.4f}")

if __name__ == "__main__":
    # Пример использования


    team1 = load_team_data(
        "output_with_readiness_1.json",
        is_home=True,
        position_in_league=1,
        last_results=[0, 1, 0.5, 1, 1]
    )
    
    team2 = load_team_data(
        "output_with_readiness_2.json",
        is_home=False,
        position_in_league=14,
        last_results=[1, 0, 0, 1, 0.5]
    )

    
    # Расчет прогноза
    forecast = calculate_match_probabilities(
        team1=team1,
        team2=team2,
        weather="sunny",
        match_type="еврокубки"
    )
    
    # Вывод результатов
    print_detailed_analysis(forecast, team1, team2)
    print_forecasts(forecast)

    # =============================================================================
# ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ РАСЧЕТОВ (ДОБАВЬ ЭТО ПЕРЕД ОСНОВНЫМ БЛОКОМ)
# =============================================================================
# class FormulaLogger:
#     """Класс для детального логирования формул и расчетов"""
    
#     def __init__(self, log_file="formula_calculations.txt"):
#         self.log_file = log_file
#         self.log_data = []
        
#     def log_formula(self, function_name: str, formula: str, inputs: dict, calculation: str, result: any):
#         """Логирует формулу с детальными расчетами"""
#         log_entry = {
#             'function': function_name,
#             'formula': formula,
#             'inputs': inputs,
#             'calculation': calculation,
#             'result': result,
#             'timestamp': np.datetime64('now')
#         }
#         self.log_data.append(log_entry)
        
#     def save_detailed_calculations(self):
#         """Сохраняет все расчеты в файл с красивым форматированием"""
#         with open(self.log_file, 'w', encoding='utf-8') as f:
#             f.write("ДЕТАЛЬНЫЙ РАСЧЕТ ФОРМУЛ ФУТБОЛЬНОЙ МОДЕЛИ\n")
#             f.write("=" * 80 + "\n\n")
            
#             for i, entry in enumerate(self.log_data, 1):
#                 f.write(f"РАСЧЕТ #{i}: {entry['function']}\n")
#                 f.write("-" * 50 + "\n")
#                 f.write(f"ФОРМУЛА: {entry['formula']}\n")
#                 f.write(f"ВХОДНЫЕ ДАННЫЕ: {self._format_inputs(entry['inputs'])}\n")
#                 f.write(f"ВЫЧИСЛЕНИЕ: {entry['calculation']}\n")
#                 f.write(f"РЕЗУЛЬТАТ: {entry['result']}\n")
#                 f.write(f"ВРЕМЯ: {entry['timestamp']}\n")
#                 f.write("=" * 80 + "\n\n")
    
#     def _format_inputs(self, inputs: dict) -> str:
#         """Форматирует входные данные для читаемости"""
#         formatted = []
#         for key, value in inputs.items():
#             if isinstance(value, (int, float)):
#                 formatted.append(f"{key} = {value}")
#             elif isinstance(value, list):
#                 formatted.append(f"{key} = [{', '.join(map(str, value[:5]))}{'...' if len(value) > 5 else ''}]")
#             else:
#                 formatted.append(f"{key} = {value}")
#         return "; ".join(formatted)

# # Создаем глобальный логгер
# formula_logger = FormulaLogger()

# # Модифицируем ключевые функции для логирования формул
# def calculate_team_strengths_with_formulas(players: List[Dict]) -> Tuple[float, float, float, List[float]]:
#     """Расчет силы команды по позициям с детальным логированием формул"""
    
#     formula_logger.log_formula(
#         "calculate_team_strengths",
#         "Позиционные коэффициенты: вратари×1.3, защитники×0.9, нападающие×1.1, полузащитники×0.7+0.4",
#         {"количество_игроков": len(players), "игроки": [f"{p['position']}:{p['readiness']}" for p in players[:3]] + ["..."] if len(players) > 3 else []},
#         f"Обработка {len(players)} игроков по позиционным коэффициентам",
#         "В процессе расчета"
#     )
    
#     if not players:
#         result = (0.5, 0.5, 0.5, [0.3])
#         formula_logger.log_formula(
#             "calculate_team_strengths",
#             "Значения по умолчанию при отсутствии игроков",
#             {"игроки": "отсутствуют"},
#             "Возврат стандартных значений: (0.5, 0.5, 0.5, [0.3])",
#             result
#         )
#         return result
    
#     goalkeepers = []
#     defenders = []
#     midfielders = []
#     attackers = []
    
#     # Собираем данные по позициям
#     for player in players:
#         pos = player['position'].lower()
#         readiness = player['readiness']
        
#         if 'вратарь' in pos:
#             goalkeepers.append(readiness * 1.3)
#         elif 'защитник' in pos:
#             defenders.append(readiness * 0.9)
#         elif 'нап' in pos or 'вингер' in pos or 'форвард' in pos:
#             attackers.append(readiness * 1.1)
#         elif 'полузащитник' in pos or 'хав' in pos:
#             midfielders.append(readiness * 0.7)
#             attackers.append(readiness * 0.4)
#         else:
#             midfielders.append(readiness * 0.6)
#             attackers.append(readiness * 0.4)
    
#     # Расчет общей готовности
#     all_players = goalkeepers + defenders + midfielders + attackers
#     avg_readiness = np.mean(all_players) if all_players else 0.5
    
#     formula_logger.log_formula(
#         "Общая готовность команды",
#         "avg_readiness = mean(все_игроки_с_коэффициентами)",
#         {
#             "вратари": f"{len(goalkeepers)} игроков: {goalkeepers[:3]}{'...' if len(goalkeepers) > 3 else ''}",
#             "защитники": f"{len(defenders)} игроков: {defenders[:3]}{'...' if len(defenders) > 3 else ''}",
#             "полузащитники": f"{len(midfielders)} игроков: {midfielders[:3]}{'...' if len(midfielders) > 3 else ''}",
#             "нападающие": f"{len(attackers)} игроков: {attackers[:3]}{'...' if len(attackers) > 3 else ''}"
#         },
#         f"Среднее из {len(all_players)} значений с коэффициентами позиций",
#         f"avg_readiness = {avg_readiness:.3f}"
#     )
    
#     # Расчет силы атаки
#     attacking_players = sorted(attackers, reverse=True)[:3]
#     if midfielders:
#         mid_attack = np.mean(midfielders) * 0.6
#         attacking_players.append(mid_attack)
    
#     attack_power = np.mean(attacking_players) if attacking_players else 0.3
    
#     formula_logger.log_formula(
#         "Сила атаки",
#         "attack_power = mean(топ_3_нападающих + mean(полузащитники) × 0.6)",
#         {
#             "топ_3_нападающих": [f"{x:.3f}" for x in sorted(attackers, reverse=True)[:3]],
#             "вклад_полузащиты": f"{np.mean(midfielders) * 0.6:.3f}" if midfielders else "нет",
#             "все_компоненты_атаки": [f"{x:.3f}" for x in attacking_players]
#         },
#         f"Среднее {len(attacking_players)} компонентов атаки",
#         f"attack_power = {attack_power:.3f}"
#     )
    
#     # Расчет силы защиты
#     defense_players = goalkeepers + defenders
#     if midfielders:
#         mid_defense = np.mean(midfielders) * 0.4
#         defense_players.append(mid_defense)
    
#     defense_power = np.mean(defense_players) if defense_players else 0.5
    
#     formula_logger.log_formula(
#         "Сила защиты", 
#         "defense_power = mean(вратари + защитники + mean(полузащитники) × 0.4)",
#         {
#             "вратари_защитники": f"{len(goalkeepers + defenders)} игроков",
#             "вклад_полузащиты": f"{np.mean(midfielders) * 0.4:.3f}" if midfielders else "нет",
#             "все_компоненты_защиты": f"{len(defense_players)} компонентов"
#         },
#         f"Среднее {len(defense_players)} компонентов защиты",
#         f"defense_power = {defense_power:.3f}"
#     )
    
#     # Топ-атакующие
#     top_attackers = sorted(attackers, reverse=True)[:3]
    
#     result = (avg_readiness, attack_power, defense_power, top_attackers)
    
#     formula_logger.log_formula(
#         "Итоги силы команды",
#         "(avg_readiness, attack_power, defense_power, top_3_attackers)",
#         {
#             "готовность": f"{avg_readiness:.3f}",
#             "атака": f"{attack_power:.3f}", 
#             "защита": f"{defense_power:.3f}",
#             "топ_нападающие": [f"{x:.3f}" for x in top_attackers]
#         },
#         "Финальные показатели команды",
#         result
#     )
    
#     return result

# def calculate_dynamic_attack_with_formulas(team: Dict, opponent: Dict) -> float:
#     """Динамический расчет атаки с детальным логированием формул"""
    
#     base_attack = team["attack_power"]
    
#     # Формула защиты
#     defense_multiplier = 1.0 + (0.5 - opponent["defense_power"]) * 0.8
    
#     formula_logger.log_formula(
#         "Множитель защиты",
#         "defense_multiplier = 1.0 + (0.5 - defense_power_opponent) × 0.8",
#         {
#             "базовая_атака": base_attack,
#             "защита_соперника": opponent["defense_power"],
#             "расчет": f"1.0 + (0.5 - {opponent['defense_power']}) × 0.8"
#         },
#         f"Вычисление множителя против защиты соперника",
#         f"defense_multiplier = {defense_multiplier:.3f}"
#     )
    
#     # Формула формы
#     form_boost = 1.0
#     if team.get('last_results'):
#         recent_goals = sum(team['last_results'])
#         form_boost = 0.8 + (recent_goals / len(team['last_results'])) * 0.4
        
#         formula_logger.log_formula(
#             "Буст формы",
#             "form_boost = 0.8 + (sum(последние_результаты) / количество_матчей) × 0.4",
#             {
#                 "последние_результаты": team['last_results'],
#                 "сумма_результатов": recent_goals,
#                 "количество_матчей": len(team['last_results']),
#                 "расчет": f"0.8 + ({recent_goals} / {len(team['last_results'])}) × 0.4"
#             },
#             "Расчет буста на основе формы команды",
#             f"form_boost = {form_boost:.3f}"
#         )
    
#     # Формула мотивации
#     motivation_boost = 1.0 + team.get('motivation', 0) * 2
    
#     formula_logger.log_formula(
#         "Буст мотивации",
#         "motivation_boost = 1.0 + motivation × 2",
#         {
#             "мотивация_команды": team.get('motivation', 0),
#             "расчет": f"1.0 + {team.get('motivation', 0)} × 2"
#         },
#         "Расчет буста мотивации",
#         f"motivation_boost = {motivation_boost:.3f}"
#     )
    
#     # Итоговая формула
#     result = base_attack * defense_multiplier * form_boost * motivation_boost
    
#     formula_logger.log_formula(
#         "Динамическая атака - итог",
#         "dynamic_attack = base_attack × defense_multiplier × form_boost × motivation_boost",
#         {
#             "base_attack": base_attack,
#             "defense_multiplier": defense_multiplier,
#             "form_boost": form_boost,
#             "motivation_boost": motivation_boost,
#             "расчет": f"{base_attack} × {defense_multiplier:.3f} × {form_boost:.3f} × {motivation_boost:.3f}"
#         },
#         "Перемножение всех компонентов атаки",
#         f"dynamic_attack = {result:.3f}"
#     )
    
#     return result

# def calculate_goal_efficiency_with_formulas(team1: Dict, team2: Dict) -> Dict:
#     """Расчет голевой эффективности с детальным логированием формул"""
    
#     # Расчет базового потенциала
#     team1_potential = calculate_dynamic_attack_with_formulas(team1, team2)
#     team2_potential = calculate_dynamic_attack_with_formulas(team2, team1)
    
#     formula_logger.log_formula(
#         "Базовый голевой потенциал",
#         "goal_potential = dynamic_attack(team, opponent)",
#         {
#             "команда1_потенциал": team1_potential,
#             "команда2_потенциал": team2_potential,
#             "команда1_дома": team1["is_home"],
#             "команда2_дома": team2["is_home"]
#         },
#         "Базовый расчет до коррекций",
#         {"team1": team1_potential, "team2": team2_potential}
#     )
    
#     # Корректировка домашнего поля
#     if team1["is_home"]:
#         old_team1 = team1_potential
#         old_team2 = team2_potential
#         team1_potential *= 1.3
#         team2_potential *= 0.9
        
#         formula_logger.log_formula(
#             "Корректировка домашнего поля",
#             "home_team × 1.3, away_team × 0.9",
#             {
#                 "команда1_до": old_team1,
#                 "команда2_до": old_team2,
#                 "расчет_команда1": f"{old_team1} × 1.3",
#                 "расчет_команда2": f"{old_team2} × 0.9"
#             },
#             "Учет домашнего преимущества",
#             {"team1_новый": team1_potential, "team2_новый": team2_potential}
#         )
#     else:
#         old_team1 = team1_potential
#         old_team2 = team2_potential
#         team1_potential *= 0.9
#         team2_potential *= 1.3
        
#         formula_logger.log_formula(
#             "Корректировка гостевого поля", 
#             "away_team × 0.9, home_team × 1.3",
#             {
#                 "команда1_до": old_team1,
#                 "команда2_до": old_team2,
#                 "расчет_команда1": f"{old_team1} × 0.9",
#                 "расчет_команда2": f"{old_team2} × 1.3"
#             },
#             "Учет гостевого недостатка",
#             {"team1_новый": team1_potential, "team2_новый": team2_potential}
#         )
    
#     # Учет звездных игроков
#     if team1["top_attackers"] and team1["top_attackers"][0] > 0.7:
#         old_val = team1_potential
#         team1_potential *= 1.25
#         formula_logger.log_formula(
#             "Звездный игрок команды 1",
#             "goal_potential × 1.25",
#             {
#                 "топ_атакующие": team1["top_attackers"][:3],
#                 "лучший_игрок": team1["top_attackers"][0],
#                 "до_коррекции": old_val,
#                 "расчет": f"{old_val} × 1.25"
#             },
#             "Учет звездного игрока в атаке",
#             f"team1_после_звезды = {team1_potential:.3f}"
#         )
    
#     if team2["top_attackers"] and team2["top_attackers"][0] > 0.7:
#         old_val = team2_potential
#         team2_potential *= 1.25
#         formula_logger.log_formula(
#             "Звездный игрок команды 2",
#             "goal_potential × 1.25", 
#             {
#                 "топ_атакующие": team2["top_attackers"][:3],
#                 "лучший_игрок": team2["top_attackers"][0],
#                 "до_коррекции": old_val,
#                 "расчет": f"{old_val} × 1.25"
#             },
#             "Учет звездного игрока в атаке",
#             f"team2_после_звезды = {team2_potential:.3f}"
#         )
    
#     # Гарантия минимального значения
#     team1_final = max(0.3, team1_potential)
#     team2_final = max(0.3, team2_potential)
    
#     formula_logger.log_formula(
#         "Финальные ожидаемые голы",
#         "max(0.3, goal_potential)",
#         {
#             "команда1_до_ограничения": team1_potential,
#             "команда2_до_ограничения": team2_potential,
#             "минимальное_значение": 0.3
#         },
#         "Гарантия минимальной продуктивности",
#         {"team1_goals": team1_final, "team2_goals": team2_final}
#     )
    
#     return {
#         "team1_goals": team1_final,
#         "team2_goals": team2_final
#     }

# # Модифицируем основную функцию
# def calculate_match_probabilities_with_formulas(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
#     """Расчет вероятностей с детальным логированием всех формул"""
    
#     formula_logger.log_formula(
#         "Начало расчета матча",
#         "Полный расчет вероятностей матча",
#         {
#             "команда1": team1['name'],
#             "команда2": team2['name'], 
#             "погода": weather,
#             "тип_матча": match_type
#         },
#         "Инициализация расчета матча",
#         "Запуск процесса"
#     )
    
#     # Расчет мотивации
#     team1_motivation = calculate_motivation(team1, match_type)
#     team2_motivation = calculate_motivation(team2, match_type)
    
#     formula_logger.log_formula(
#         "Мотивация команд",
#         "base_motivation + position_bonus + form_bonus",
#         {
#             "команда1_мотивация": team1_motivation,
#             "команда2_мотивация": team2_motivation,
#             "тип_матча": match_type
#         },
#         "Расчет мотивации на основе типа матча и положения в таблице",
#         {"team1_motivation": team1_motivation, "team2_motivation": team2_motivation}
#     )
    
#     team1['motivation'] = team1_motivation
#     team2['motivation'] = team2_motivation
    
#     # Основной расчет
#     goal_potential = calculate_goal_efficiency_with_formulas(team1, team2)
    
#     # Сохраняем все расчеты
#     formula_logger.save_detailed_calculations()
    
#     # Возвращаем результат обычным способом
#     return calculate_match_probabilities(team1, team2, weather, match_type)

# # Добавляем в основной блок
# if __name__ == "__main__":
#     # Пример использования с детальным логированием формул
    
#     team1 = load_team_data(
#         "output_with_readiness_1.json",
#         is_home=True,
#         position_in_league=4,
#         last_results=[0.5, 1, 1, 0, 1]
#     )
    
#     team2 = load_team_data(
#         "output_with_readiness_2.json", 
#         is_home=False,
#         position_in_league=1,
#         last_results=[1, 1, 1, 1, 1]
#     )
    
#     # Используем версию с логированием формул
#     forecast = calculate_match_probabilities_with_formulas(
#         team1=team1,
#         team2=team2,
#         weather="sunny",
#         match_type="еврокубки"
#     )
    
#     print("✅ Все формулы и расчеты сохранены в 'formula_calculations.txt'")
    
#     # Вывод результатов
#     print_detailed_analysis(forecast, team1, team2)
#     print_forecasts(forecast)