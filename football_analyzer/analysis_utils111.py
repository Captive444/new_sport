from typing import Dict

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