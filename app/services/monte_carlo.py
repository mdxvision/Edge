"""
Monte Carlo Simulation Service

Bankroll growth projections using Monte Carlo simulation.
Provides risk of ruin calculations, expected trajectories, and variance analysis.
"""

import random
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from statistics import mean, stdev, median

from app.utils.logging import get_logger
from app.utils.odds import american_to_probability, american_to_decimal

logger = get_logger(__name__)


class BetSizingStrategy(str, Enum):
    """Available bet sizing strategies."""
    FLAT = "flat"           # Fixed unit size
    KELLY = "kelly"         # Full Kelly criterion
    HALF_KELLY = "half_kelly"  # Half Kelly (more conservative)
    QUARTER_KELLY = "quarter_kelly"  # Quarter Kelly (very conservative)
    PERCENTAGE = "percentage"  # Fixed percentage of bankroll
    MARTINGALE = "martingale"  # Double after loss (risky!)


@dataclass
class BetScenario:
    """Represents a bet scenario for simulation."""
    probability: float      # True win probability
    odds: int               # American odds
    edge: float             # Edge over implied probability


@dataclass
class SimulationResult:
    """Result of a single simulation run."""
    final_bankroll: float
    max_bankroll: float
    min_bankroll: float
    peak_drawdown: float
    total_bets: int
    wins: int
    losses: int
    went_bust: bool
    trajectory: List[float]


def kelly_fraction(probability: float, odds: int) -> float:
    """
    Calculate Kelly criterion fraction.

    Kelly = (bp - q) / b
    Where:
        b = decimal odds - 1 (net profit per unit bet)
        p = probability of winning
        q = 1 - p (probability of losing)
    """
    decimal_odds = american_to_decimal(odds)
    b = decimal_odds - 1
    p = probability
    q = 1 - p

    kelly = (b * p - q) / b if b > 0 else 0

    # Never bet negative Kelly (no edge)
    return max(0, kelly)


def calculate_bet_size(
    bankroll: float,
    strategy: BetSizingStrategy,
    probability: float,
    odds: int,
    unit_size: float = 0.01,
    max_bet_pct: float = 0.05,
    consecutive_losses: int = 0
) -> float:
    """
    Calculate bet size based on strategy.

    Args:
        bankroll: Current bankroll
        strategy: Bet sizing strategy
        probability: Win probability
        odds: American odds
        unit_size: Base unit as fraction of bankroll (for flat/percentage)
        max_bet_pct: Maximum bet as fraction of bankroll
        consecutive_losses: For martingale strategy

    Returns:
        Bet size in dollars
    """
    if bankroll <= 0:
        return 0

    if strategy == BetSizingStrategy.FLAT:
        bet = bankroll * unit_size

    elif strategy == BetSizingStrategy.KELLY:
        kelly = kelly_fraction(probability, odds)
        bet = bankroll * kelly

    elif strategy == BetSizingStrategy.HALF_KELLY:
        kelly = kelly_fraction(probability, odds)
        bet = bankroll * kelly * 0.5

    elif strategy == BetSizingStrategy.QUARTER_KELLY:
        kelly = kelly_fraction(probability, odds)
        bet = bankroll * kelly * 0.25

    elif strategy == BetSizingStrategy.PERCENTAGE:
        bet = bankroll * unit_size

    elif strategy == BetSizingStrategy.MARTINGALE:
        base_bet = bankroll * unit_size
        bet = base_bet * (2 ** consecutive_losses)

    else:
        bet = bankroll * unit_size

    # Apply maximum bet cap
    max_bet = bankroll * max_bet_pct
    bet = min(bet, max_bet)

    # Don't bet more than we have
    bet = min(bet, bankroll)

    return round(bet, 2)


def simulate_single_bet(
    bankroll: float,
    bet_size: float,
    probability: float,
    odds: int
) -> Tuple[float, bool]:
    """
    Simulate a single bet.

    Returns:
        Tuple of (new_bankroll, won)
    """
    won = random.random() < probability

    if won:
        profit = bet_size * (american_to_decimal(odds) - 1)
        new_bankroll = bankroll + profit
    else:
        new_bankroll = bankroll - bet_size

    return new_bankroll, won


def run_simulation(
    starting_bankroll: float,
    bet_scenarios: List[BetScenario],
    strategy: BetSizingStrategy,
    num_bets: int,
    unit_size: float = 0.01,
    max_bet_pct: float = 0.05,
    bust_threshold: float = 0.0,
    track_trajectory: bool = True
) -> SimulationResult:
    """
    Run a single Monte Carlo simulation.

    Args:
        starting_bankroll: Initial bankroll
        bet_scenarios: List of possible bet scenarios (randomly selected)
        strategy: Bet sizing strategy
        num_bets: Number of bets to simulate
        unit_size: Base unit size (fraction of bankroll)
        max_bet_pct: Maximum bet (fraction of bankroll)
        bust_threshold: Bankroll level considered bust (default 0)
        track_trajectory: Whether to track bankroll at each step

    Returns:
        SimulationResult with final stats
    """
    bankroll = starting_bankroll
    max_bankroll = starting_bankroll
    min_bankroll = starting_bankroll
    peak = starting_bankroll
    max_drawdown = 0.0
    wins = 0
    losses = 0
    consecutive_losses = 0
    trajectory = [starting_bankroll] if track_trajectory else []

    for i in range(num_bets):
        # Check if bust
        if bankroll <= bust_threshold:
            # Fill remaining trajectory with bust value
            if track_trajectory:
                trajectory.extend([bust_threshold] * (num_bets - i))
            break

        # Select random bet scenario
        scenario = random.choice(bet_scenarios)

        # Calculate bet size
        bet_size = calculate_bet_size(
            bankroll=bankroll,
            strategy=strategy,
            probability=scenario.probability,
            odds=scenario.odds,
            unit_size=unit_size,
            max_bet_pct=max_bet_pct,
            consecutive_losses=consecutive_losses
        )

        # Skip if bet size is 0
        if bet_size <= 0:
            if track_trajectory:
                trajectory.append(bankroll)
            continue

        # Simulate bet
        bankroll, won = simulate_single_bet(
            bankroll, bet_size, scenario.probability, scenario.odds
        )

        if won:
            wins += 1
            consecutive_losses = 0
        else:
            losses += 1
            consecutive_losses += 1

        # Update tracking
        max_bankroll = max(max_bankroll, bankroll)
        min_bankroll = min(min_bankroll, bankroll)

        # Update peak and drawdown
        if bankroll > peak:
            peak = bankroll
        drawdown = (peak - bankroll) / peak if peak > 0 else 0
        max_drawdown = max(max_drawdown, drawdown)

        if track_trajectory:
            trajectory.append(bankroll)

    return SimulationResult(
        final_bankroll=round(bankroll, 2),
        max_bankroll=round(max_bankroll, 2),
        min_bankroll=round(min_bankroll, 2),
        peak_drawdown=round(max_drawdown * 100, 2),
        total_bets=wins + losses,
        wins=wins,
        losses=losses,
        went_bust=bankroll <= bust_threshold,
        trajectory=trajectory
    )


def run_monte_carlo(
    starting_bankroll: float,
    bet_scenarios: List[BetScenario],
    strategy: BetSizingStrategy,
    num_bets: int,
    num_simulations: int = 1000,
    unit_size: float = 0.01,
    max_bet_pct: float = 0.05,
    bust_threshold: float = 0.0
) -> Dict[str, Any]:
    """
    Run full Monte Carlo simulation with multiple iterations.

    Args:
        starting_bankroll: Initial bankroll
        bet_scenarios: List of possible bet scenarios
        strategy: Bet sizing strategy
        num_bets: Number of bets per simulation
        num_simulations: Number of simulation runs
        unit_size: Base unit size
        max_bet_pct: Maximum bet percentage
        bust_threshold: Bankroll level considered bust

    Returns:
        Comprehensive simulation results
    """
    logger.info(f"Running {num_simulations} Monte Carlo simulations with {strategy.value} strategy")

    results = []
    for i in range(num_simulations):
        # Only track full trajectory for a subset to save memory
        track_trajectory = i < 100

        result = run_simulation(
            starting_bankroll=starting_bankroll,
            bet_scenarios=bet_scenarios,
            strategy=strategy,
            num_bets=num_bets,
            unit_size=unit_size,
            max_bet_pct=max_bet_pct,
            bust_threshold=bust_threshold,
            track_trajectory=track_trajectory
        )
        results.append(result)

    # Analyze results
    final_bankrolls = [r.final_bankroll for r in results]
    bust_count = sum(1 for r in results if r.went_bust)

    # Calculate percentiles
    sorted_finals = sorted(final_bankrolls)
    p5 = sorted_finals[int(num_simulations * 0.05)]
    p25 = sorted_finals[int(num_simulations * 0.25)]
    p50 = sorted_finals[int(num_simulations * 0.50)]
    p75 = sorted_finals[int(num_simulations * 0.75)]
    p95 = sorted_finals[int(num_simulations * 0.95)]

    # Average trajectory (from tracked simulations)
    tracked_results = [r for r in results if r.trajectory]
    avg_trajectory = []
    if tracked_results:
        trajectory_length = len(tracked_results[0].trajectory)
        for i in range(trajectory_length):
            avg_at_step = mean(r.trajectory[i] for r in tracked_results if i < len(r.trajectory))
            avg_trajectory.append(round(avg_at_step, 2))

    # Drawdown analysis
    max_drawdowns = [r.peak_drawdown for r in results]

    return {
        "simulation_params": {
            "starting_bankroll": starting_bankroll,
            "num_bets": num_bets,
            "num_simulations": num_simulations,
            "strategy": strategy.value,
            "unit_size": unit_size,
            "max_bet_pct": max_bet_pct,
            "bust_threshold": bust_threshold
        },
        "final_bankroll": {
            "mean": round(mean(final_bankrolls), 2),
            "median": round(median(final_bankrolls), 2),
            "std_dev": round(stdev(final_bankrolls), 2) if len(final_bankrolls) > 1 else 0,
            "min": round(min(final_bankrolls), 2),
            "max": round(max(final_bankrolls), 2),
            "percentiles": {
                "5th": round(p5, 2),
                "25th": round(p25, 2),
                "50th": round(p50, 2),
                "75th": round(p75, 2),
                "95th": round(p95, 2)
            }
        },
        "risk_analysis": {
            "risk_of_ruin": round(bust_count / num_simulations * 100, 2),
            "bust_count": bust_count,
            "survival_rate": round((num_simulations - bust_count) / num_simulations * 100, 2),
            "avg_max_drawdown": round(mean(max_drawdowns), 2),
            "max_drawdown_95th": round(sorted(max_drawdowns)[int(num_simulations * 0.95)], 2)
        },
        "performance": {
            "expected_roi": round((mean(final_bankrolls) - starting_bankroll) / starting_bankroll * 100, 2),
            "profitable_simulations": sum(1 for f in final_bankrolls if f > starting_bankroll),
            "profitable_rate": round(sum(1 for f in final_bankrolls if f > starting_bankroll) / num_simulations * 100, 2),
            "avg_win_rate": round(mean(r.wins / r.total_bets * 100 if r.total_bets > 0 else 0 for r in results), 2)
        },
        "trajectory": {
            "average": avg_trajectory[::max(1, len(avg_trajectory)//50)]  # Downsample for response
        } if avg_trajectory else None
    }


def calculate_risk_of_ruin(
    win_probability: float,
    odds: int,
    bet_fraction: float,
    target_multiple: float = 2.0,
    bust_fraction: float = 0.0
) -> Dict[str, Any]:
    """
    Calculate theoretical risk of ruin.

    Uses the formula for geometric random walk.

    Args:
        win_probability: Probability of winning each bet
        odds: American odds
        bet_fraction: Fraction of bankroll bet each time
        target_multiple: Target bankroll multiple (e.g., 2.0 = double)
        bust_fraction: Fraction considered bust (0 = complete bust)

    Returns:
        Risk of ruin analysis
    """
    decimal_odds = american_to_decimal(odds)
    p = win_probability
    q = 1 - p

    # Calculate edge
    implied_prob = american_to_probability(odds)
    edge = p - implied_prob

    # Win/loss amounts as fraction of bankroll
    win_amount = bet_fraction * (decimal_odds - 1)
    loss_amount = bet_fraction

    # Calculate expected growth rate (Kelly growth)
    if p > 0 and q > 0 and win_amount > 0:
        growth_rate = p * math.log(1 + win_amount) + q * math.log(1 - loss_amount)
    else:
        growth_rate = 0

    # Simplified risk of ruin approximation
    # RoR ≈ ((1-edge)/(1+edge))^(bankroll_units)
    if edge > 0:
        units_to_target = math.log(target_multiple) / math.log(1 + win_amount)
        ror_approx = ((1 - edge) / (1 + edge)) ** (1 / bet_fraction) if bet_fraction > 0 else 0
        ror_approx = min(1.0, max(0.0, ror_approx))
    else:
        ror_approx = 1.0  # Negative edge = eventual ruin

    return {
        "win_probability": round(p * 100, 2),
        "implied_probability": round(implied_prob * 100, 2),
        "edge": round(edge * 100, 2),
        "bet_fraction": round(bet_fraction * 100, 2),
        "risk_of_ruin_estimate": round(ror_approx * 100, 2),
        "expected_growth_rate": round(growth_rate * 100, 4),
        "kelly_fraction": round(kelly_fraction(p, odds) * 100, 2),
        "is_overbetting": bet_fraction > kelly_fraction(p, odds),
        "recommendation": get_ror_recommendation(ror_approx, edge, bet_fraction)
    }


def get_ror_recommendation(ror: float, edge: float, bet_fraction: float) -> str:
    """Generate recommendation based on risk of ruin analysis."""
    kelly = kelly_fraction(0.5 + edge/2, 100)  # Approximate Kelly

    if edge <= 0:
        return "No edge detected - avoid betting"
    elif ror > 0.5:
        return "High risk of ruin - reduce bet size significantly"
    elif ror > 0.2:
        return "Moderate risk of ruin - consider reducing bet size"
    elif bet_fraction > kelly:
        return f"Overbetting Kelly criterion - reduce to {kelly*100:.1f}% or less"
    elif ror < 0.05:
        return "Conservative sizing - low risk of ruin"
    else:
        return "Acceptable risk level"


def compare_strategies(
    starting_bankroll: float,
    bet_scenarios: List[BetScenario],
    num_bets: int,
    num_simulations: int = 500
) -> Dict[str, Any]:
    """
    Compare different bet sizing strategies.

    Returns comparison of key metrics across strategies.
    """
    strategies = [
        BetSizingStrategy.FLAT,
        BetSizingStrategy.QUARTER_KELLY,
        BetSizingStrategy.HALF_KELLY,
        BetSizingStrategy.KELLY,
        BetSizingStrategy.PERCENTAGE
    ]

    comparisons = []

    for strategy in strategies:
        result = run_monte_carlo(
            starting_bankroll=starting_bankroll,
            bet_scenarios=bet_scenarios,
            strategy=strategy,
            num_bets=num_bets,
            num_simulations=num_simulations,
            unit_size=0.01 if strategy in [BetSizingStrategy.FLAT, BetSizingStrategy.PERCENTAGE] else 0.01,
            max_bet_pct=0.10
        )

        comparisons.append({
            "strategy": strategy.value,
            "expected_roi": result["performance"]["expected_roi"],
            "risk_of_ruin": result["risk_analysis"]["risk_of_ruin"],
            "median_final": result["final_bankroll"]["median"],
            "std_dev": result["final_bankroll"]["std_dev"],
            "profitable_rate": result["performance"]["profitable_rate"],
            "avg_max_drawdown": result["risk_analysis"]["avg_max_drawdown"]
        })

    # Sort by expected ROI
    comparisons.sort(key=lambda x: x["expected_roi"], reverse=True)

    # Determine best strategy for different goals
    best_growth = max(comparisons, key=lambda x: x["expected_roi"])
    best_safety = min(comparisons, key=lambda x: x["risk_of_ruin"])
    best_balanced = min(comparisons, key=lambda x: x["risk_of_ruin"] - x["expected_roi"] * 5)

    return {
        "comparisons": comparisons,
        "recommendations": {
            "best_for_growth": best_growth["strategy"],
            "best_for_safety": best_safety["strategy"],
            "best_balanced": best_balanced["strategy"]
        },
        "simulation_params": {
            "starting_bankroll": starting_bankroll,
            "num_bets": num_bets,
            "num_simulations": num_simulations
        }
    }


def create_bet_scenarios_from_edge(
    avg_edge: float,
    edge_variance: float = 0.02,
    avg_odds: int = -110,
    odds_range: Tuple[int, int] = (-200, 200),
    num_scenarios: int = 10
) -> List[BetScenario]:
    """
    Create diverse bet scenarios from average edge parameters.

    Args:
        avg_edge: Average edge (e.g., 0.03 for 3%)
        edge_variance: Variance in edge
        avg_odds: Average American odds
        odds_range: Range of odds (min, max)
        num_scenarios: Number of scenarios to generate

    Returns:
        List of BetScenario objects
    """
    scenarios = []

    for _ in range(num_scenarios):
        # Random odds within range
        if avg_odds > 0:
            odds = random.randint(max(100, odds_range[0]), odds_range[1])
        else:
            odds = random.randint(odds_range[0], min(-100, odds_range[1]))

        # Implied probability from odds
        implied = american_to_probability(odds)

        # Edge with variance
        edge = avg_edge + random.uniform(-edge_variance, edge_variance)
        edge = max(0, edge)  # No negative edge scenarios

        # True probability = implied + edge
        probability = min(0.95, implied + edge)

        scenarios.append(BetScenario(
            probability=probability,
            odds=odds,
            edge=edge
        ))

    return scenarios


def analyze_variance(
    starting_bankroll: float,
    bet_scenarios: List[BetScenario],
    strategy: BetSizingStrategy,
    num_bets: int,
    num_simulations: int = 1000
) -> Dict[str, Any]:
    """
    Detailed variance analysis of bankroll outcomes.
    """
    results = []
    for _ in range(num_simulations):
        result = run_simulation(
            starting_bankroll=starting_bankroll,
            bet_scenarios=bet_scenarios,
            strategy=strategy,
            num_bets=num_bets,
            track_trajectory=False
        )
        results.append(result)

    final_bankrolls = [r.final_bankroll for r in results]
    returns = [(f - starting_bankroll) / starting_bankroll * 100 for f in final_bankrolls]

    # Calculate various variance metrics
    variance = stdev(returns) ** 2 if len(returns) > 1 else 0

    # Downside deviation (only negative returns)
    negative_returns = [r for r in returns if r < 0]
    downside_dev = stdev(negative_returns) if len(negative_returns) > 1 else 0

    # Sortino ratio (return / downside deviation)
    avg_return = mean(returns)
    sortino = avg_return / downside_dev if downside_dev > 0 else float('inf')

    # Sharpe-like ratio (assuming 0 risk-free rate)
    sharpe = avg_return / stdev(returns) if stdev(returns) > 0 else 0

    return {
        "variance_analysis": {
            "mean_return": round(avg_return, 2),
            "variance": round(variance, 2),
            "std_deviation": round(stdev(returns), 2) if len(returns) > 1 else 0,
            "downside_deviation": round(downside_dev, 2),
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3) if sortino != float('inf') else "Infinite (no losses)"
        },
        "distribution": {
            "min_return": round(min(returns), 2),
            "max_return": round(max(returns), 2),
            "range": round(max(returns) - min(returns), 2),
            "skewness": calculate_skewness(returns),
            "positive_outcomes": sum(1 for r in returns if r > 0),
            "negative_outcomes": sum(1 for r in returns if r < 0),
            "break_even": sum(1 for r in returns if r == 0)
        }
    }


def calculate_skewness(data: List[float]) -> float:
    """Calculate skewness of distribution."""
    if len(data) < 3:
        return 0

    n = len(data)
    avg = mean(data)
    std = stdev(data)

    if std == 0:
        return 0

    skew = sum((x - avg) ** 3 for x in data) / (n * std ** 3)
    return round(skew, 3)
