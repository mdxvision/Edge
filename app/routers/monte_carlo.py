"""
Monte Carlo Simulation Router

Bankroll growth projections and risk analysis.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.monte_carlo import (
    BetSizingStrategy,
    BetScenario,
    run_monte_carlo,
    calculate_risk_of_ruin,
    compare_strategies,
    analyze_variance,
    create_bet_scenarios_from_edge,
    kelly_fraction,
    calculate_bet_size,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/monte-carlo", tags=["Monte Carlo Simulation"])


class BetScenarioInput(BaseModel):
    """Input for a bet scenario."""
    probability: float = Field(..., ge=0, le=1, description="True win probability (0-1)")
    odds: int = Field(..., description="American odds (e.g., -110, +150)")
    edge: Optional[float] = Field(None, ge=0, description="Edge over implied probability")


class SimulationRequest(BaseModel):
    """Request for Monte Carlo simulation."""
    starting_bankroll: float = Field(..., gt=0, description="Starting bankroll amount")
    bet_scenarios: List[BetScenarioInput] = Field(
        ..., min_length=1, description="Bet scenarios to simulate"
    )
    strategy: BetSizingStrategy = Field(
        BetSizingStrategy.HALF_KELLY, description="Bet sizing strategy"
    )
    num_bets: int = Field(100, ge=10, le=10000, description="Number of bets to simulate")
    num_simulations: int = Field(1000, ge=100, le=10000, description="Number of simulation runs")
    unit_size: float = Field(0.01, ge=0.001, le=0.1, description="Base unit size (fraction)")
    max_bet_pct: float = Field(0.05, ge=0.01, le=0.25, description="Max bet (fraction)")
    bust_threshold: float = Field(0.0, ge=0, description="Bankroll level considered bust")


class QuickSimulationRequest(BaseModel):
    """Quick simulation using average edge parameters."""
    starting_bankroll: float = Field(..., gt=0, description="Starting bankroll amount")
    avg_edge: float = Field(0.03, ge=0, le=0.15, description="Average edge (e.g., 0.03 for 3%)")
    edge_variance: float = Field(0.02, ge=0, le=0.1, description="Variance in edge")
    avg_odds: int = Field(-110, description="Average American odds")
    strategy: BetSizingStrategy = Field(BetSizingStrategy.HALF_KELLY, description="Strategy")
    num_bets: int = Field(100, ge=10, le=10000, description="Number of bets")
    num_simulations: int = Field(1000, ge=100, le=10000, description="Simulation runs")


class RiskOfRuinRequest(BaseModel):
    """Request for risk of ruin calculation."""
    win_probability: float = Field(..., ge=0, le=1, description="Win probability")
    odds: int = Field(..., description="American odds")
    bet_fraction: float = Field(..., ge=0.001, le=0.5, description="Bet fraction of bankroll")
    target_multiple: float = Field(2.0, ge=1.1, description="Target bankroll multiple")


class StrategyComparisonRequest(BaseModel):
    """Request for strategy comparison."""
    starting_bankroll: float = Field(..., gt=0, description="Starting bankroll")
    bet_scenarios: List[BetScenarioInput] = Field(..., min_length=1, description="Bet scenarios")
    num_bets: int = Field(100, ge=10, le=5000, description="Number of bets")
    num_simulations: int = Field(500, ge=100, le=5000, description="Simulations per strategy")


class KellyRequest(BaseModel):
    """Request for Kelly criterion calculation."""
    probability: float = Field(..., ge=0, le=1, description="Win probability")
    odds: int = Field(..., description="American odds")
    bankroll: Optional[float] = Field(None, gt=0, description="Bankroll for bet size calculation")


@router.post("/simulate")
def run_simulation(request: SimulationRequest):
    """
    Run Monte Carlo simulation for bankroll projections.

    Simulates thousands of betting sequences to project:
    - Expected bankroll growth
    - Risk of ruin (going bust)
    - Variance and drawdown analysis
    - Probability of reaching profit targets

    **Example Request:**
    ```json
    {
        "starting_bankroll": 10000,
        "bet_scenarios": [
            {"probability": 0.55, "odds": -110},
            {"probability": 0.52, "odds": -105}
        ],
        "strategy": "half_kelly",
        "num_bets": 500,
        "num_simulations": 1000
    }
    ```
    """
    try:
        scenarios = [
            BetScenario(
                probability=s.probability,
                odds=s.odds,
                edge=s.edge or (s.probability - 0.5)  # Default edge calculation
            )
            for s in request.bet_scenarios
        ]

        result = run_monte_carlo(
            starting_bankroll=request.starting_bankroll,
            bet_scenarios=scenarios,
            strategy=request.strategy,
            num_bets=request.num_bets,
            num_simulations=request.num_simulations,
            unit_size=request.unit_size,
            max_bet_pct=request.max_bet_pct,
            bust_threshold=request.bust_threshold
        )

        return result

    except Exception as e:
        logger.error(f"Simulation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/simulate-quick")
def run_quick_simulation(request: QuickSimulationRequest):
    """
    Run simulation with simplified inputs.

    Automatically generates diverse bet scenarios based on
    average edge and variance parameters.

    **Example Request:**
    ```json
    {
        "starting_bankroll": 5000,
        "avg_edge": 0.03,
        "strategy": "half_kelly",
        "num_bets": 200
    }
    ```
    """
    try:
        scenarios = create_bet_scenarios_from_edge(
            avg_edge=request.avg_edge,
            edge_variance=request.edge_variance,
            avg_odds=request.avg_odds,
            num_scenarios=10
        )

        result = run_monte_carlo(
            starting_bankroll=request.starting_bankroll,
            bet_scenarios=scenarios,
            strategy=request.strategy,
            num_bets=request.num_bets,
            num_simulations=request.num_simulations
        )

        return result

    except Exception as e:
        logger.error(f"Quick simulation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/risk-of-ruin")
def calculate_ror(request: RiskOfRuinRequest):
    """
    Calculate theoretical risk of ruin.

    Analyzes the probability of going bust given:
    - Win probability
    - Odds
    - Bet sizing (fraction of bankroll)

    Returns Kelly criterion comparison and recommendations.
    """
    result = calculate_risk_of_ruin(
        win_probability=request.win_probability,
        odds=request.odds,
        bet_fraction=request.bet_fraction,
        target_multiple=request.target_multiple
    )

    return result


@router.post("/compare-strategies")
def compare_betting_strategies(request: StrategyComparisonRequest):
    """
    Compare different bet sizing strategies.

    Runs simulations for each strategy:
    - Flat betting (fixed units)
    - Quarter Kelly (very conservative)
    - Half Kelly (balanced)
    - Full Kelly (aggressive)
    - Percentage betting

    Returns which strategy is best for growth, safety, or balance.
    """
    try:
        scenarios = [
            BetScenario(
                probability=s.probability,
                odds=s.odds,
                edge=s.edge or 0.03
            )
            for s in request.bet_scenarios
        ]

        result = compare_strategies(
            starting_bankroll=request.starting_bankroll,
            bet_scenarios=scenarios,
            num_bets=request.num_bets,
            num_simulations=request.num_simulations
        )

        return result

    except Exception as e:
        logger.error(f"Strategy comparison error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/analyze-variance")
def variance_analysis(request: SimulationRequest):
    """
    Detailed variance analysis of bankroll outcomes.

    Returns:
    - Standard deviation and variance
    - Downside deviation (volatility of losses)
    - Sharpe ratio (risk-adjusted returns)
    - Sortino ratio (downside risk-adjusted)
    - Distribution skewness
    """
    try:
        scenarios = [
            BetScenario(
                probability=s.probability,
                odds=s.odds,
                edge=s.edge or 0.03
            )
            for s in request.bet_scenarios
        ]

        result = analyze_variance(
            starting_bankroll=request.starting_bankroll,
            bet_scenarios=scenarios,
            strategy=request.strategy,
            num_bets=request.num_bets,
            num_simulations=request.num_simulations
        )

        return result

    except Exception as e:
        logger.error(f"Variance analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/kelly")
def calculate_kelly(request: KellyRequest):
    """
    Calculate Kelly criterion for optimal bet sizing.

    The Kelly criterion maximizes long-term growth rate.

    Returns:
    - Full Kelly fraction
    - Half and quarter Kelly recommendations
    - Actual bet size (if bankroll provided)
    """
    kelly = kelly_fraction(request.probability, request.odds)

    result = {
        "probability": request.probability,
        "odds": request.odds,
        "kelly_fraction": round(kelly * 100, 2),
        "half_kelly": round(kelly * 50, 2),
        "quarter_kelly": round(kelly * 25, 2),
        "recommendation": get_kelly_recommendation(kelly)
    }

    if request.bankroll:
        result["bet_sizes"] = {
            "full_kelly": round(request.bankroll * kelly, 2),
            "half_kelly": round(request.bankroll * kelly * 0.5, 2),
            "quarter_kelly": round(request.bankroll * kelly * 0.25, 2)
        }
        result["bankroll"] = request.bankroll

    return result


def get_kelly_recommendation(kelly: float) -> str:
    """Generate recommendation based on Kelly fraction."""
    if kelly <= 0:
        return "No edge - do not bet"
    elif kelly < 0.02:
        return "Small edge - consider if worth the variance"
    elif kelly < 0.05:
        return "Moderate edge - half Kelly recommended"
    elif kelly < 0.10:
        return "Good edge - half to full Kelly appropriate"
    elif kelly < 0.20:
        return "Strong edge - full Kelly reasonable, half Kelly safer"
    else:
        return "Large edge - verify analysis, consider half Kelly to reduce variance"


@router.get("/strategies")
def list_strategies():
    """
    List available bet sizing strategies with descriptions.
    """
    return {
        "strategies": [
            {
                "name": "flat",
                "description": "Fixed unit size regardless of edge",
                "risk_level": "low",
                "growth_potential": "low",
                "best_for": "Beginners or when unsure of edge accuracy"
            },
            {
                "name": "kelly",
                "description": "Optimal growth rate betting - bet proportional to edge",
                "risk_level": "high",
                "growth_potential": "maximum",
                "best_for": "Confident edge estimates, long-term growth"
            },
            {
                "name": "half_kelly",
                "description": "Half of Kelly criterion - reduced variance",
                "risk_level": "medium",
                "growth_potential": "high",
                "best_for": "Most bettors - good balance of growth and safety"
            },
            {
                "name": "quarter_kelly",
                "description": "Quarter of Kelly criterion - conservative",
                "risk_level": "low",
                "growth_potential": "medium",
                "best_for": "Risk-averse bettors, uncertain edge estimates"
            },
            {
                "name": "percentage",
                "description": "Fixed percentage of current bankroll",
                "risk_level": "medium",
                "growth_potential": "medium",
                "best_for": "Simple to implement, adjusts with bankroll"
            },
            {
                "name": "martingale",
                "description": "Double after each loss (DANGEROUS)",
                "risk_level": "extreme",
                "growth_potential": "varies",
                "best_for": "NOT RECOMMENDED - high risk of ruin",
                "warning": "Can lead to rapid bankroll depletion"
            }
        ],
        "recommendation": "half_kelly is recommended for most users"
    }


@router.get("/guide")
def simulation_guide():
    """
    Guide to understanding Monte Carlo simulation results.
    """
    return {
        "what_is_monte_carlo": (
            "Monte Carlo simulation runs thousands of possible betting sequences "
            "to understand the range of possible outcomes. It accounts for variance "
            "and helps you understand risk beyond just expected value."
        ),
        "key_metrics": {
            "risk_of_ruin": {
                "description": "Probability of going bust (losing entire bankroll)",
                "good_value": "< 5%",
                "concerning_value": "> 20%"
            },
            "expected_roi": {
                "description": "Average return on investment across simulations",
                "interpretation": "Your edge over time, but actual results vary"
            },
            "median_final_bankroll": {
                "description": "Middle outcome - 50% of simulations end above/below",
                "interpretation": "More realistic than mean when variance is high"
            },
            "max_drawdown": {
                "description": "Largest peak-to-trough decline",
                "interpretation": "Expect this decline at some point"
            },
            "sharpe_ratio": {
                "description": "Risk-adjusted return (return / volatility)",
                "good_value": "> 1.0",
                "excellent_value": "> 2.0"
            },
            "sortino_ratio": {
                "description": "Return / downside volatility (only considers losses)",
                "interpretation": "Higher is better - focuses on bad outcomes"
            }
        },
        "interpreting_results": [
            "Look at percentiles (5th, 25th, 50th, 75th, 95th) for outcome range",
            "Risk of ruin > 10% suggests bet sizing is too aggressive",
            "Large gap between mean and median indicates high variance",
            "Max drawdown shows worst-case scenario to prepare for"
        ],
        "tips": [
            "Use half Kelly for safer growth with lower variance",
            "More bets reduce variance but take longer",
            "Higher edge scenarios reduce risk of ruin",
            "Run multiple simulations to get stable estimates"
        ]
    }
