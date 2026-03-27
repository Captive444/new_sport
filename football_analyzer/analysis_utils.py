# analysis_utils.py (добавьте новые функции)

import json
from typing import Dict
import os
from datetime import datetime

def analyze_matchup(team1: Dict, team2: Dict) -> Dict:
    """Анализ противостояния команд"""
    analysis = {
        "style_matchup": "",
        "key_advantages": [],
        "potential_weaknesses": [],
        "expected_dynamics": "",
        "betting_insights": []
    }
    
    style1 = team1["characteristics"]["style"]
    style2 = team2["characteristics"]["style"]
    analysis["style_matchup"] = f"{style1} vs {style2}"
    
    if team1["attack_power"] > team2["defense_power"] * 1.4:
        analysis["key_advantages"].append(f"{team1['name']} имеет атакующее преимущество")
        analysis["betting_insights"].append("ИТБ1 1.5")
    
    if team2["attack_power"] > team1["defense_power"] * 1.4:
        analysis["key_advantages"].append(f"{team2['name']} может быть опасна в атаке")
        analysis["betting_insights"].append("ИТБ2 1.5")
    
    if team1["defense_power"] < 0.4:
        analysis["potential_weaknesses"].append(f"У {team1['name']} проблемы в защите")
    
    if team2["defense_power"] < 0.4:
        analysis["potential_weaknesses"].append(f"У {team2['name']} слабая оборона")
    
    total_attack = team1["attack_power"] + team2["attack_power"]
    if total_attack > 1.2:
        analysis["expected_dynamics"] = "атакующий матч с голами"
        analysis["betting_insights"].append("Тотал больше 2.5")
    elif total_attack < 0.8:
        analysis["expected_dynamics"] = "оборонительный матч"
        analysis["betting_insights"].append("Тотал меньше 2.5")
    else:
        analysis["expected_dynamics"] = "уравновешенная игра"
    
    if team1["is_home"]:
        analysis["key_advantages"].append(f"{team1['name']} играет дома")
    
    return analysis

def calculate_match_probabilities(team1: Dict, team2: Dict, weather: str, match_type: str) -> Dict:
    """Расчет вероятностей с динамическим подходом"""
    
    from probability_utils import calculate_motivation, calculate_goal_efficiency, detect_upset_potential, calculate_exact_scores_dynamic, calculate_1x2_from_poisson, calculate_totals_from_poisson, calculate_both_teams_to_score, calculate_individual_totals
    
    team1_motivation = calculate_motivation(team1, match_type)
    team2_motivation = calculate_motivation(team2, match_type)
    team1['motivation'] = team1_motivation
    team2['motivation'] = team2_motivation
    
    goal_potential = calculate_goal_efficiency(team1, team2)
    
    upset_potential = detect_upset_potential(team1, team2)
    
    exact_scores = calculate_exact_scores_dynamic(
        team1, team2, 
        goal_potential["team1_goals"], 
        goal_potential["team2_goals"]
    )
    
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

def get_detailed_analysis_str(forecast, team1, team2) -> str:
    """Возвращает строку с детальным анализом матча"""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"📊 ДЕТАЛЬНЫЙ АНАЛИЗ МАТЧА: {team1['name']} vs {team2['name']}")
    lines.append(f"{'='*60}")
    
    lines.append(f"\n🏆 РЕЙТИНГ СИЛЫ:")
    lines.append(f"{team1['name']}: {team1['attack_power']:.2f} (атака) / {team1['defense_power']:.2f} (защита)")
    lines.append(f"{team2['name']}: {team2['attack_power']:.2f} (атака) / {team2['defense_power']:.2f} (защита)")
    
    goal_potential = forecast["Анализ матча"]["goal_potential"]
    lines.append(f"\n🎯 ОЖИДАЕМАЯ ГОЛЕВАЯ ЭФФЕКТИВНОСТЬ:")
    lines.append(f"{team1['name']}: {goal_potential['team1_goals']:.2f} ожидаемых голов")
    lines.append(f"{team2['name']}: {goal_potential['team2_goals']:.2f} ожидаемых голов")
    
    lines.append(f"\n🎯 СТИЛЬ КОМАНД:")
    lines.append(f"{team1['name']}: {team1['characteristics']['style']} ({team1['characteristics']['attack_level']} атака, {team1['characteristics']['defense_level']} защита)")
    lines.append(f"{team2['name']}: {team2['characteristics']['style']} ({team2['characteristics']['attack_level']} атака, {team2['characteristics']['defense_level']} защита)")
    
    lines.append(f"\n🔍 КЛЮЧЕВЫЕ ФАКТОРЫ:")
    analysis = forecast["Анализ матча"]
    lines.append(f"Стилевое противостояние: {analysis['style_matchup']}")
    lines.append(f"Ожидаемая динамика: {analysis['expected_dynamics']}")
    
    if analysis["upset_alert"]:
        lines.append(f"🚨 ВНИМАНИЕ: Возможна сенсация!")
        for factor, active in analysis["upset_factors"].items():
            if active:
                lines.append(f"   • {factor}")
    
    if analysis["key_advantages"]:
        lines.append("\n✅ ПРЕИМУЩЕСТВА:")
        for advantage in analysis["key_advantages"]:
            lines.append(f"  • {advantage}")
    
    if analysis["potential_weaknesses"]:
        lines.append("\n⚠️ СЛАБЫЕ СТОРОНЫ:")
        for weakness in analysis["potential_weaknesses"]:
            lines.append(f"  • {weakness}")
    
    lines.append(f"\n💡 СТАТИСТИЧЕСКИЕ ВЫВОДЫ:")
    for insight in analysis["betting_insights"]:
        lines.append(f"  • {insight}")
    
    return "\n".join(lines)

def get_forecasts_str(forecast) -> str:
    """Возвращает строку с прогнозами"""
    lines = []
    lines.append(f"\n📈 ПРОГНОЗЫ НА МАТЧ:")
    
    lines.append(f"\n1X2:")
    for bet_type, prob in forecast["1X2"].items():
        lines.append(f"  {bet_type}: {prob:.2f}")
    
    lines.append(f"\nТОТАЛЫ:")
    for bet_type, prob in forecast["Тоталы"].items():
        lines.append(f"  {bet_type}: {prob:.2f}")
    
    lines.append(f"\nОБЕ ЗАБЬЮТ:")
    for bet_type, prob in forecast["Обе забьют"].items():
        lines.append(f"  {bet_type}: {prob:.2f}")
    
    lines.append(f"\nИНДИВИДУАЛЬНЫЕ ТОТАЛЫ:")
    for bet_type, prob in forecast["Индивидуальные тоталы"].items():
        lines.append(f"  {bet_type}: {prob:.2f}")
    
    lines.append(f"\nТОЧНЫЙ СЧЕТ (ТОП-5):")
    for score, prob in list(forecast["Точный счет"].items())[:5]:
        lines.append(f"  {score}: {prob:.4f}")
    
    return "\n".join(lines)

def save_forecast_to_json(forecast: Dict, team1: Dict, team2: Dict, match_data: Dict, output_dir: str = "forecasts") -> str:
    """
    Сохраняет прогноз в JSON файл
    
    Args:
        forecast: словарь с прогнозами
        team1: данные команды 1
        team2: данные команды 2
        match_data: данные матча (дата, лига и т.д.)
        output_dir: папка для сохранения
    
    Returns:
        Путь к сохраненному файлу
    """
    # Создаем папку, если её нет
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Формируем имя файла
    match_name = f"{team1['name']} vs {team2['name']}".replace(' ', '_').replace('-', '_')
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{output_dir}/{match_name}_{date_str}.json"
    
    # Подготавливаем данные для JSON
    json_data = {
        "match_info": {
            "home_team": team1['name'],
            "away_team": team2['name'],
            "league": match_data.get('league', 'Неизвестно'),
            "date": match_data.get('date_time', 'Неизвестно'),
            "analysis_date": datetime.now().isoformat()
        },
        "team_stats": {
            team1['name']: {
                "attack_power": round(team1['attack_power'], 3),
                "defense_power": round(team1['defense_power'], 3),
                "style": team1['characteristics']['style'],
                "attack_level": team1['characteristics']['attack_level'],
                "defense_level": team1['characteristics']['defense_level']
            },
            team2['name']: {
                "attack_power": round(team2['attack_power'], 3),
                "defense_power": round(team2['defense_power'], 3),
                "style": team2['characteristics']['style'],
                "attack_level": team2['characteristics']['attack_level'],
                "defense_level": team2['characteristics']['defense_level']
            }
        },
        "goal_potential": {
            team1['name']: round(forecast["Анализ матча"]["goal_potential"]["team1_goals"], 3),
            team2['name']: round(forecast["Анализ матча"]["goal_potential"]["team2_goals"], 3)
        },
        "probabilities": {
            "1x2": {
                "home": round(forecast["1X2"]["П1"], 3),
                "draw": round(forecast["1X2"]["X"], 3),
                "away": round(forecast["1X2"]["П2"], 3)
            },
            "totals": {
                "over_1.5": round(forecast["Тоталы"][">1.5"], 3),
                "under_1.5": round(forecast["Тоталы"]["<1.5"], 3),
                "over_2.5": round(forecast["Тоталы"][">2.5"], 3),
                "under_2.5": round(forecast["Тоталы"]["<2.5"], 3)
            },
            "both_teams_to_score": {
                "yes": round(forecast["Обе забьют"]["Да"], 3),
                "no": round(forecast["Обе забьют"]["Нет"], 3)
            },
            "individual_totals": {
                f"ИТБ1_1.5": round(forecast["Индивидуальные тоталы"]["ИТБ1 1.5"], 3),
                f"ИТМ1_1.5": round(forecast["Индивидуальные тоталы"]["ИТМ1 1.5"], 3),
                f"ИТБ2_1.5": round(forecast["Индивидуальные тоталы"]["ИТБ2 1.5"], 3),
                f"ИТМ2_1.5": round(forecast["Индивидуальные тоталы"]["ИТМ2 1.5"], 3)
            },
            "top_scores": [
                {"score": score, "probability": round(prob, 4)} 
                for score, prob in list(forecast["Точный счет"].items())[:5]
            ]
        },
        "analysis": {
            "style_matchup": forecast["Анализ матча"]["style_matchup"],
            "expected_dynamics": forecast["Анализ матча"]["expected_dynamics"],
            "upset_alert": forecast["Анализ матча"]["upset_alert"],
            "upset_factors": forecast["Анализ матча"]["upset_factors"],
            "key_advantages": forecast["Анализ матча"]["key_advantages"],
            "potential_weaknesses": forecast["Анализ матча"]["potential_weaknesses"],
            "betting_insights": forecast["Анализ матча"]["betting_insights"]
        }
    }
    
    # Сохраняем JSON
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    return filename

def save_all_forecasts_to_json(all_forecasts: list, output_dir: str = "forecasts") -> str:
    """
    Сохраняет все прогнозы в один JSON файл
    
    Args:
        all_forecasts: список всех прогнозов
        output_dir: папка для сохранения
    
    Returns:
        Путь к сохраненному файлу
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filename = f"{output_dir}/all_forecasts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_forecasts, f, ensure_ascii=False, indent=2)
    
    return filename