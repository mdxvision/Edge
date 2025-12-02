def american_to_implied_probability(american_odds: int) -> float:
    if american_odds > 0:
        return 100.0 / (american_odds + 100.0)
    else:
        return abs(american_odds) / (abs(american_odds) + 100.0)


def american_to_probability(american_odds: int) -> float:
    return american_to_implied_probability(american_odds)


def american_to_decimal(american_odds: int) -> float:
    if american_odds > 0:
        return 1.0 + (american_odds / 100.0)
    else:
        return 1.0 + (100.0 / abs(american_odds))


def decimal_to_american(decimal_odds: float) -> int:
    if decimal_odds >= 2.0:
        return int(round((decimal_odds - 1) * 100))
    else:
        return int(round(-100 / (decimal_odds - 1)))


def implied_probability_to_american(prob: float) -> int:
    if prob <= 0 or prob >= 1:
        raise ValueError("Probability must be between 0 and 1 (exclusive)")
    
    if prob >= 0.5:
        return int(round(-100 * prob / (1 - prob)))
    else:
        return int(round(100 * (1 - prob) / prob))


def calculate_payout(american_odds: int, stake: float = 1.0) -> float:
    if american_odds > 0:
        return stake * (american_odds / 100.0)
    else:
        return stake * (100.0 / abs(american_odds))


def expected_value(prob: float, american_odds: int, stake: float = 1.0) -> float:
    payout = calculate_payout(american_odds, stake)
    win_amount = payout
    loss_amount = stake
    return (prob * win_amount) - ((1 - prob) * loss_amount)


def edge(model_prob: float, implied_prob: float) -> float:
    return model_prob - implied_prob


def is_value_bet(model_prob: float, american_odds: int, min_edge: float = 0.03) -> bool:
    implied_prob = american_to_implied_probability(american_odds)
    return edge(model_prob, implied_prob) >= min_edge


def kelly_criterion(model_prob: float, american_odds: int, fraction: float = 0.25) -> float:
    implied_prob = american_to_implied_probability(american_odds)
    payout_multiplier = calculate_payout(american_odds) / 1.0
    
    if payout_multiplier <= 0:
        return 0.0
    
    kelly = (model_prob * (payout_multiplier + 1) - 1) / payout_multiplier
    
    if kelly <= 0:
        return 0.0
    
    return kelly * fraction
