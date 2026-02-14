import json
import numpy as np
from math import factorial, exp
from typing import Dict, List, Optional, Tuple

def poisson_probability(mean, goals):
    """Расчет вероятности по распределению Пуассона"""
    return (mean ** goals) * exp(-mean) / factorial(goals)

def calculate_exact_scores(team1: Dict, team2: Dict, max_goals=5):
    """Расчет вероятностей точного счета с улучшенной логикой"""
    # Базовые средние голы с учетом баланса атаки и защиты
    mean_team1 = 1.4 * team1["attack_power"] / (team2["defense_power"] + 0.2)
    mean_team2 = 1.4 * team2["attack_power"] / (team1["defense_power"] + 0.2)
    
    # Домашнее преимущество
    if team1["is_home"]:
        mean_team1 *= 1.25
        mean_team2 *= 0.85
    else:
        mean_team1 *= 0.85
        mean_team2 *= 1.25
    
    # Корректировка на форму и мотивацию
    mean_team1 *= team1["form_coefficient"]
    mean_team2 *= team2["form_coefficient"]
    
    # Гарантируем минимальную продуктивность
    mean_team1 = max(0.6, mean_team1)
    mean_team2 = max(0.6, mean_team2)
    
    scores = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_probability(mean_team1, i) * poisson_probability(mean_team2, j)
            scores[f"{i}-{j}"] = round(prob, 4)
    
    total = sum(scores.values())
    return {score: prob/total for score, prob in scores.items()}

def calculate_team_strengths(players: List[Dict]) -> Tuple[float, float, float, List[float]]:
    """Расчет силы команды по позициям с улучшенной логикой"""
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
            attackers.append(readiness * 0.4)  # Полузащитники влияют на атаку
        else:
            # Универсальные игроки
            midfielders.append(readiness * 0.6)
            attackers.append(readiness * 0.4)
    
    # Расчет общей готовности
    all_players = goalkeepers + defenders + midfielders + attackers
    avg_readiness = np.mean(all_players) if all_players else 0.5
    
    # Расчет силы атаки (топ-3 атакующих + полузащитники)
    attacking_players = sorted(attackers, reverse=True)[:3]
    if midfielders:
        attacking_players.append(np.mean(midfielders) * 0.6)
    attack_power = np.mean(attacking_players) if attacking_players else 0.3
    
    # Расчет силы защиты (вратари + защитники + часть полузащитников)
    defense_players = goalkeepers + defenders
    if midfielders:
        defense_players.append(np.mean(midfighters) * 0.4)
    defense_power = np.mean(defense_players) if defense_players else 0.5
    
    # Топ-атакующие для анализа звездных игроков
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
    
    # Учет формы (последние 5 матчей)
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
    if position >= 16:  # Зона вылета
        base_motivation += 0.12
    elif position <= 4:  # Лига чемпионов
        base_motivation += 0.10
    elif position <= 6:  # Лига Европы
        base_motivation += 0.07
    elif position <= 8:  # Конференционная лига
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
        analysis["key_advantages"].append(
            f"{team1['name']} имеет значительное атакующее преимущество"
        )
        analysis["betting_insights"].append("Рассмотреть ставки на атаку первой команды")
    
    if team2["attack_power"] > team1["defense_power"] * 1.4:
        analysis["key_advantages"].append(
            f"{team2['name']} может быть опасна в атаке"
        )
        analysis["betting_insights"].append("Обе команды могут забить")
    
    # Анализ слабостей
    if team1["defense_power"] < 0.4:
        analysis["potential_weaknesses"].append(
            f"У {team1['name']} проблемы в защите"
        )
        analysis["betting_insights"].append(f"ИТБ2 (индивидуальный тотал второй команды)")
    
    if team2["defense_power"] < 0.4:
        analysis["potential_weaknesses"].append(
            f"У {team2['name']} слабая оборона"
        )
        analysis["betting_insights"].append(f"ИТБ1 (индивидуальный тотал первой команды)")
    
    # Ожидаемая динамика матча
    total_attack = team1["attack_power"] + team2["attack_power"]
    total_defense = team1["defense_power"] + team2["defense_power"]
    
    if total_attack > total_defense * 1.3:
        analysis["expected_dynamics"] = "атакующий матч с голами"
        analysis["betting_insights"].append("Тотал больше 2.5")
    elif total_defense > total_attack * 1.3:
        analysis["expected_dynamics"] = "оборонительный матч"
        analysis["betting_insights"].append("Тотал меньше 2.5")
    else:
        analysis["expected_dynamics"] = "уравновешенная игра"
    
    # Домашнее преимущество
    if team1["is_home"]:
        analysis["key_advantages"].append(f"{team1['name']} играет дома")
    
    # Звездные игроки
    if team1["top_attackers"] and team1["top_attackers"][0] > 0.7:
        analysis["key_advantages"].append(f"У {team1['name']} есть ключевой атакующий игрок")
    
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.7:
        analysis["key_advantages"].append(f"У {team2['name']} есть опасный нападающий")
    
    return analysis

def calculate_match_probabilities(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
    """Расчет вероятностей с улучшенной логикой"""
    
    # Базовые корректировки
    home_advantage = 0.08
    weather_impact = {
        "rain": -0.02, "sunny": 0.01, "windy": -0.01, "snow": -0.03, None: 0.0
    }.get(weather, 0.0)
    
    # Мотивация
    team1_motivation = calculate_motivation(team1, match_type)
    team2_motivation = calculate_motivation(team2, match_type)
    
    # Итоговые показатели силы
    team1_power = (
        team1["avg_readiness"] * 0.25 +
        team1["attack_power"] * 0.40 +
        team1["defense_power"] * 0.35 +
        (home_advantage if team1["is_home"] else -home_advantage * 0.7) +
        team1_motivation
    )
    
    team2_power = (
        team2["avg_readiness"] * 0.25 +
        team2["attack_power"] * 0.40 +
        team2["defense_power"] * 0.35 +
        (-home_advantage * 0.7 if team1["is_home"] else home_advantage) +
        team2_motivation
    )
    
    # Разница в силе с учетом погоды
    diff = (team1_power - team2_power) * (1 + weather_impact)
    
    # Базовые вероятности
    forecasts = {
        "1X2": {
            "П1": max(0.1, min(0.9, 0.42 + diff * 0.7)),
            "X": max(0.1, min(0.9, 0.32 - abs(diff) * 0.8)),
            "П2": max(0.1, min(0.9, 0.26 - diff * 0.7))
        },
        "Тоталы": {
            ">1.5": 0.65 + (team1["attack_power"] + team2["attack_power"] - 1.0) * 0.3,
            "<1.5": 0.35 - (team1["attack_power"] + team2["attack_power"] - 1.0) * 0.3,
            ">2.5": 0.45 + (team1["attack_power"] + team2["attack_power"] - 1.0) * 0.4,
            "<2.5": 0.55 - (team1["attack_power"] + team2["attack_power"] - 1.0) * 0.4,
        },
        "Форы": {
            "Ф1(-1.5)": max(0.1, 0.35 + diff * 0.5),
            "Ф2(+1.5)": max(0.1, 0.65 - diff * 0.5),
            "Ф1(-0.5)": max(0.1, 0.55 + diff * 0.6),
            "Ф2(+0.5)": max(0.1, 0.45 - diff * 0.6)
        },
        "Обе забьют": {
            "Да": min(0.9, max(0.1, 
                (team1["attack_power"] * 0.7 + team2["attack_power"] * 0.7) * 0.8
            )),
            "Нет": min(0.9, max(0.1, 
                1 - (team1["attack_power"] * 0.7 + team2["attack_power"] * 0.7) * 0.8
            ))
        },
        "Индивидуальные тоталы": {
            "ИТБ1 1.5": team1["attack_power"] * 0.9 - team2["defense_power"] * 0.3,
            "ИТМ1 1.5": 1 - (team1["attack_power"] * 0.9 - team2["defense_power"] * 0.3),
            "ИТБ2 1.5": team2["attack_power"] * 0.9 - team1["defense_power"] * 0.3,
            "ИТМ2 1.5": 1 - (team2["attack_power"] * 0.9 - team1["defense_power"] * 0.3),
        }
    }
    
    # Корректировки на звездных игроков
    star_bonus = 1.08
    if team1["top_attackers"] and team1["top_attackers"][0] > 0.7:
        forecasts["1X2"]["П1"] *= star_bonus
        forecasts["Тоталы"][">2.5"] *= 1.1
        forecasts["Индивидуальные тоталы"]["ИТБ1 1.5"] *= 1.15
    
    if team2["top_attackers"] and team2["top_attackers"][0] > 0.7:
        forecasts["1X2"]["П2"] *= star_bonus
        forecasts["Тоталы"][">2.5"] *= 1.1
        forecasts["Индивидуальные тоталы"]["ИТБ2 1.5"] *= 1.15
    
    # Нормализация основных рынков
    total_1x2 = sum(forecasts["1X2"].values())
    forecasts["1X2"] = {k: v/total_1x2 for k, v in forecasts["1X2"].items()}
    
    # Расчет точных счетов
    forecasts["Точный счет"] = calculate_exact_scores(team1, team2)
    forecasts["Точный счет"] = dict(sorted(
        forecasts["Точный счет"].items(),
        key=lambda item: item[1],
        reverse=True
    )[:10])
    
    # Анализ противостояния
    forecasts["Анализ матча"] = analyze_matchup(team1, team2)
    
    # Общая информация о командах
    forecasts["Команда 1"] = team1["characteristics"]
    forecasts["Команда 2"] = team2["characteristics"]
    
    return forecasts

def print_detailed_analysis(forecast, team1, team2):
    """Детальный вывод анализа матча"""
    print(f"\n{'='*60}")
    print(f"📊 ДЕТАЛЬНЫЙ АНАЛИЗ МАТЧА: {team1['name']} vs {team2['name']}")
    print(f"{'='*60}")
    
    print(f"\n🏆 РЕЙТИНГ СИЛЫ:")
    print(f"{team1['name']}: {team1['attack_power']:.2f} (атака) / {team1['defense_power']:.2f} (защита)")
    print(f"{team2['name']}: {team2['attack_power']:.2f} (атака) / {team2['defense_power']:.2f} (защита)")
    
    print(f"\n🎯 СТИЛЬ КОМАНД:")
    print(f"{team1['name']}: {team1['characteristics']['style']} ({team1['characteristics']['attack_level']} атака, {team1['characteristics']['defense_level']} защита)")
    print(f"{team2['name']}: {team2['characteristics']['style']} ({team2['characteristics']['attack_level']} атака, {team2['characteristics']['defense_level']} защита)")
    
    print(f"\n🔍 КЛЮЧЕВЫЕ ФАКТОРЫ:")
    analysis = forecast["Анализ матча"]
    print(f"Стилевое противостояние: {analysis['style_matchup']}")
    print(f"Ожидаемая динамика: {analysis['expected_dynamics']}")
    
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
    
    print(f"\nФОРЫ:")
    for bet_type, prob in forecast["Форы"].items():
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
        position_in_league=8,
        last_results=[0.5, 1, 1, 1, 0.5]
    )
    
    team2 = load_team_data(
        "output_with_readiness_2.json",
        is_home=False,
        position_in_league=3,
        last_results=[0, 0, 0.5, 0, 0.5]
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