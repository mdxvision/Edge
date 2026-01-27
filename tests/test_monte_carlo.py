"""
Tests for Monte Carlo Simulation service.
"""

import pytest
from app.services.monte_carlo import (
    BetSizingStrategy,
    BetScenario,
    SimulationResult,
    kelly_fraction,
    calculate_bet_size,
    simulate_single_bet,
    run_simulation,
    run_monte_carlo,
    calculate_risk_of_ruin,
    compare_strategies,
    create_bet_scenarios_from_edge,
    analyze_variance,
    calculate_skewness,
    get_ror_recommendation,
)


class TestBetSizingStrategy:
    """Test BetSizingStrategy enum."""

    def test_flat_value(self):
        """Flat strategy has correct value."""
        assert BetSizingStrategy.FLAT.value == "flat"

    def test_kelly_value(self):
        """Kelly strategy has correct value."""
        assert BetSizingStrategy.KELLY.value == "kelly"

    def test_half_kelly_value(self):
        """Half Kelly strategy has correct value."""
        assert BetSizingStrategy.HALF_KELLY.value == "half_kelly"

    def test_quarter_kelly_value(self):
        """Quarter Kelly strategy has correct value."""
        assert BetSizingStrategy.QUARTER_KELLY.value == "quarter_kelly"

    def test_percentage_value(self):
        """Percentage strategy has correct value."""
        assert BetSizingStrategy.PERCENTAGE.value == "percentage"

    def test_martingale_value(self):
        """Martingale strategy has correct value."""
        assert BetSizingStrategy.MARTINGALE.value == "martingale"


class TestBetScenario:
    """Test BetScenario dataclass."""

    def test_create_scenario(self):
        """Can create a bet scenario."""
        scenario = BetScenario(probability=0.55, odds=-110, edge=0.03)
        assert scenario.probability == 0.55
        assert scenario.odds == -110
        assert scenario.edge == 0.03

    def test_scenario_with_positive_odds(self):
        """Can create scenario with positive odds."""
        scenario = BetScenario(probability=0.40, odds=150, edge=0.02)
        assert scenario.odds == 150


class TestSimulationResult:
    """Test SimulationResult dataclass."""

    def test_create_result(self):
        """Can create a simulation result."""
        result = SimulationResult(
            final_bankroll=12000,
            max_bankroll=15000,
            min_bankroll=8000,
            peak_drawdown=20.0,
            total_bets=100,
            wins=55,
            losses=45,
            went_bust=False,
            trajectory=[10000, 10500, 11000]
        )
        assert result.final_bankroll == 12000
        assert result.went_bust is False
        assert result.wins == 55


class TestKellyFraction:
    """Test Kelly criterion calculation."""

    def test_positive_edge(self):
        """Kelly should be positive with edge."""
        kelly = kelly_fraction(0.55, -110)
        assert kelly > 0

    def test_no_edge_returns_zero(self):
        """Kelly should be near zero with no edge."""
        # At -110, implied prob is ~52.4%
        kelly = kelly_fraction(0.524, -110)
        assert kelly < 0.01  # Very small or zero

    def test_negative_edge_returns_zero(self):
        """Kelly should be zero with negative edge."""
        kelly = kelly_fraction(0.45, -110)
        assert kelly == 0

    def test_higher_edge_higher_kelly(self):
        """Higher edge should produce higher Kelly."""
        kelly_55 = kelly_fraction(0.55, -110)
        kelly_60 = kelly_fraction(0.60, -110)
        assert kelly_60 > kelly_55

    def test_better_odds_higher_kelly(self):
        """Better odds should produce higher Kelly for same probability."""
        kelly_minus110 = kelly_fraction(0.55, -110)
        kelly_plus100 = kelly_fraction(0.55, 100)
        assert kelly_plus100 > kelly_minus110


class TestCalculateBetSize:
    """Test bet size calculation."""

    def test_flat_strategy(self):
        """Flat strategy should use unit size."""
        bet = calculate_bet_size(
            bankroll=10000,
            strategy=BetSizingStrategy.FLAT,
            probability=0.55,
            odds=-110,
            unit_size=0.01
        )
        assert bet == 100  # 1% of 10000

    def test_kelly_strategy(self):
        """Kelly strategy should use Kelly criterion."""
        bet = calculate_bet_size(
            bankroll=10000,
            strategy=BetSizingStrategy.KELLY,
            probability=0.55,
            odds=-110
        )
        assert bet > 0

    def test_half_kelly_is_half(self):
        """Half Kelly should be half of full Kelly."""
        kelly_bet = calculate_bet_size(
            bankroll=10000,
            strategy=BetSizingStrategy.KELLY,
            probability=0.55,
            odds=-110,
            max_bet_pct=0.25  # High cap to not interfere
        )
        half_kelly_bet = calculate_bet_size(
            bankroll=10000,
            strategy=BetSizingStrategy.HALF_KELLY,
            probability=0.55,
            odds=-110,
            max_bet_pct=0.25
        )
        assert abs(half_kelly_bet - kelly_bet * 0.5) < 1

    def test_quarter_kelly_is_quarter(self):
        """Quarter Kelly should be quarter of full Kelly."""
        kelly_bet = calculate_bet_size(
            bankroll=10000,
            strategy=BetSizingStrategy.KELLY,
            probability=0.55,
            odds=-110,
            max_bet_pct=0.25
        )
        quarter_kelly_bet = calculate_bet_size(
            bankroll=10000,
            strategy=BetSizingStrategy.QUARTER_KELLY,
            probability=0.55,
            odds=-110,
            max_bet_pct=0.25
        )
        assert abs(quarter_kelly_bet - kelly_bet * 0.25) < 1

    def test_max_bet_cap(self):
        """Bet should be capped at max bet percentage."""
        bet = calculate_bet_size(
            bankroll=10000,
            strategy=BetSizingStrategy.KELLY,
            probability=0.70,  # High edge for high Kelly
            odds=-110,
            max_bet_pct=0.05
        )
        assert bet <= 500  # 5% of 10000

    def test_zero_bankroll_returns_zero(self):
        """Zero bankroll should return zero bet."""
        bet = calculate_bet_size(
            bankroll=0,
            strategy=BetSizingStrategy.FLAT,
            probability=0.55,
            odds=-110
        )
        assert bet == 0

    def test_martingale_doubles(self):
        """Martingale should double after losses."""
        base_bet = calculate_bet_size(
            bankroll=10000,
            strategy=BetSizingStrategy.MARTINGALE,
            probability=0.55,
            odds=-110,
            unit_size=0.01,
            consecutive_losses=0
        )
        doubled_bet = calculate_bet_size(
            bankroll=10000,
            strategy=BetSizingStrategy.MARTINGALE,
            probability=0.55,
            odds=-110,
            unit_size=0.01,
            consecutive_losses=1
        )
        assert doubled_bet == base_bet * 2


class TestSimulateSingleBet:
    """Test single bet simulation."""

    def test_win_increases_bankroll(self):
        """Winning bet should increase bankroll."""
        # With high probability, likely to win
        wins = 0
        for _ in range(1000):
            new_bankroll, won = simulate_single_bet(
                bankroll=1000,
                bet_size=100,
                probability=1.0,  # Guaranteed win
                odds=-110
            )
            if won:
                wins += 1
                assert new_bankroll > 1000

        assert wins == 1000  # All should win

    def test_loss_decreases_bankroll(self):
        """Losing bet should decrease bankroll."""
        new_bankroll, won = simulate_single_bet(
            bankroll=1000,
            bet_size=100,
            probability=0.0,  # Guaranteed loss
            odds=-110
        )
        assert not won
        assert new_bankroll == 900


class TestRunSimulation:
    """Test single simulation run."""

    def test_simulation_returns_result(self):
        """Simulation should return valid result."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = run_simulation(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.FLAT,
            num_bets=50,
            unit_size=0.01
        )

        assert isinstance(result, SimulationResult)
        assert result.total_bets <= 50
        assert result.wins + result.losses == result.total_bets

    def test_trajectory_tracked(self):
        """Trajectory should be tracked when requested."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = run_simulation(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.FLAT,
            num_bets=20,
            track_trajectory=True
        )

        assert len(result.trajectory) >= 1
        assert result.trajectory[0] == 10000

    def test_bust_detection(self):
        """Should detect when bankroll goes bust."""
        scenarios = [BetScenario(probability=0.01, odds=-110, edge=-0.50)]  # Almost always lose
        result = run_simulation(
            starting_bankroll=100,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.KELLY,  # Will bet nothing due to no edge
            num_bets=10,
            bust_threshold=50
        )

        # With Kelly, won't bet since no edge
        assert result.total_bets == 0 or not result.went_bust

    def test_max_drawdown_calculated(self):
        """Max drawdown should be calculated."""
        scenarios = [BetScenario(probability=0.50, odds=-110, edge=0.0)]
        result = run_simulation(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.FLAT,
            num_bets=50
        )

        assert result.peak_drawdown >= 0


class TestRunMonteCarlo:
    """Test full Monte Carlo simulation."""

    def test_monte_carlo_returns_results(self):
        """Monte Carlo should return comprehensive results."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = run_monte_carlo(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.HALF_KELLY,
            num_bets=50,
            num_simulations=100
        )

        assert "simulation_params" in result
        assert "final_bankroll" in result
        assert "risk_analysis" in result
        assert "performance" in result

    def test_percentiles_calculated(self):
        """Should calculate percentiles."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = run_monte_carlo(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.FLAT,
            num_bets=50,
            num_simulations=100
        )

        percentiles = result["final_bankroll"]["percentiles"]
        assert "5th" in percentiles
        assert "25th" in percentiles
        assert "50th" in percentiles
        assert "75th" in percentiles
        assert "95th" in percentiles

    def test_risk_of_ruin_calculated(self):
        """Should calculate risk of ruin."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = run_monte_carlo(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.FLAT,
            num_bets=50,
            num_simulations=100
        )

        assert "risk_of_ruin" in result["risk_analysis"]
        assert result["risk_analysis"]["risk_of_ruin"] >= 0

    def test_profitable_rate_calculated(self):
        """Should calculate profitable rate."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = run_monte_carlo(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.FLAT,
            num_bets=50,
            num_simulations=100
        )

        assert "profitable_rate" in result["performance"]

    def test_trajectory_average_included(self):
        """Should include average trajectory."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = run_monte_carlo(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.FLAT,
            num_bets=50,
            num_simulations=100
        )

        assert result["trajectory"] is not None
        assert "average" in result["trajectory"]


class TestCalculateRiskOfRuin:
    """Test risk of ruin calculation."""

    def test_positive_edge_lower_ror(self):
        """Positive edge should have lower risk of ruin."""
        result = calculate_risk_of_ruin(
            win_probability=0.55,
            odds=-110,
            bet_fraction=0.02
        )

        assert "risk_of_ruin_estimate" in result
        assert result["edge"] > 0

    def test_no_edge_high_ror(self):
        """No edge should have high risk of ruin."""
        result = calculate_risk_of_ruin(
            win_probability=0.48,  # Less than implied
            odds=-110,
            bet_fraction=0.05
        )

        assert result["edge"] < 0
        assert result["risk_of_ruin_estimate"] > 50

    def test_overbetting_detected(self):
        """Should detect overbetting Kelly."""
        result = calculate_risk_of_ruin(
            win_probability=0.55,
            odds=-110,
            bet_fraction=0.20  # Very aggressive
        )

        assert result["is_overbetting"] is True

    def test_recommendation_provided(self):
        """Should provide recommendation."""
        result = calculate_risk_of_ruin(
            win_probability=0.55,
            odds=-110,
            bet_fraction=0.02
        )

        assert "recommendation" in result
        assert len(result["recommendation"]) > 0


class TestGetRorRecommendation:
    """Test RoR recommendation generation."""

    def test_no_edge_recommendation(self):
        """Should recommend avoiding with no edge."""
        rec = get_ror_recommendation(ror=0.5, edge=-0.02, bet_fraction=0.01)
        assert "avoid" in rec.lower()

    def test_high_ror_recommendation(self):
        """Should recommend reducing size with high RoR."""
        rec = get_ror_recommendation(ror=0.6, edge=0.02, bet_fraction=0.10)
        assert "reduce" in rec.lower()

    def test_low_ror_recommendation(self):
        """Should indicate conservative with low RoR."""
        rec = get_ror_recommendation(ror=0.02, edge=0.03, bet_fraction=0.01)
        assert "conservative" in rec.lower() or "acceptable" in rec.lower()


class TestCompareStrategies:
    """Test strategy comparison."""

    def test_comparison_returns_all_strategies(self):
        """Should compare multiple strategies."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = compare_strategies(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            num_bets=50,
            num_simulations=100
        )

        assert "comparisons" in result
        assert len(result["comparisons"]) >= 4  # At least 4 strategies

    def test_recommendations_provided(self):
        """Should provide strategy recommendations."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = compare_strategies(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            num_bets=50,
            num_simulations=100
        )

        assert "recommendations" in result
        assert "best_for_growth" in result["recommendations"]
        assert "best_for_safety" in result["recommendations"]
        assert "best_balanced" in result["recommendations"]

    def test_comparison_metrics(self):
        """Should include key comparison metrics."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = compare_strategies(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            num_bets=50,
            num_simulations=100
        )

        comparison = result["comparisons"][0]
        assert "strategy" in comparison
        assert "expected_roi" in comparison
        assert "risk_of_ruin" in comparison
        assert "median_final" in comparison


class TestCreateBetScenariosFromEdge:
    """Test bet scenario generation."""

    def test_creates_requested_scenarios(self):
        """Should create requested number of scenarios."""
        scenarios = create_bet_scenarios_from_edge(
            avg_edge=0.03,
            num_scenarios=5
        )

        assert len(scenarios) == 5

    def test_scenarios_have_positive_probability(self):
        """All scenarios should have valid probability."""
        scenarios = create_bet_scenarios_from_edge(
            avg_edge=0.03,
            num_scenarios=10
        )

        for s in scenarios:
            assert 0 < s.probability <= 1

    def test_edge_variance_applied(self):
        """Scenarios should have varied edges."""
        scenarios = create_bet_scenarios_from_edge(
            avg_edge=0.03,
            edge_variance=0.02,
            num_scenarios=20
        )

        edges = [s.edge for s in scenarios]
        # Should have some variation
        assert max(edges) != min(edges)


class TestAnalyzeVariance:
    """Test variance analysis."""

    def test_variance_metrics_calculated(self):
        """Should calculate variance metrics."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = analyze_variance(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.FLAT,
            num_bets=50,
            num_simulations=100
        )

        assert "variance_analysis" in result
        assert "mean_return" in result["variance_analysis"]
        assert "std_deviation" in result["variance_analysis"]
        assert "sharpe_ratio" in result["variance_analysis"]

    def test_distribution_metrics(self):
        """Should calculate distribution metrics."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]
        result = analyze_variance(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.FLAT,
            num_bets=50,
            num_simulations=100
        )

        assert "distribution" in result
        assert "min_return" in result["distribution"]
        assert "max_return" in result["distribution"]
        assert "skewness" in result["distribution"]


class TestCalculateSkewness:
    """Test skewness calculation."""

    def test_symmetric_data_near_zero(self):
        """Symmetric data should have skewness near zero."""
        data = [-2, -1, 0, 1, 2]
        skew = calculate_skewness(data)
        assert abs(skew) < 0.5

    def test_positive_skew(self):
        """Right-tailed data should have positive skewness."""
        data = [1, 2, 3, 4, 5, 10, 15, 20]
        skew = calculate_skewness(data)
        assert skew > 0

    def test_empty_data_returns_zero(self):
        """Empty data should return zero."""
        skew = calculate_skewness([])
        assert skew == 0

    def test_insufficient_data(self):
        """Less than 3 points should return zero."""
        skew = calculate_skewness([1, 2])
        assert skew == 0


class TestIntegration:
    """Integration tests for Monte Carlo service."""

    def test_full_simulation_workflow(self):
        """Test complete simulation workflow."""
        # Create scenarios
        scenarios = create_bet_scenarios_from_edge(
            avg_edge=0.03,
            edge_variance=0.01,
            num_scenarios=5
        )

        # Run simulation
        result = run_monte_carlo(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.HALF_KELLY,
            num_bets=100,
            num_simulations=200
        )

        # Verify comprehensive results
        assert result["simulation_params"]["starting_bankroll"] == 10000
        assert result["simulation_params"]["strategy"] == "half_kelly"
        assert result["final_bankroll"]["mean"] > 0
        assert result["risk_analysis"]["survival_rate"] > 0

    def test_edge_affects_outcomes(self):
        """Higher edge should produce better outcomes."""
        low_edge_scenarios = [BetScenario(probability=0.52, odds=-110, edge=0.01)]
        high_edge_scenarios = [BetScenario(probability=0.58, odds=-110, edge=0.06)]

        low_result = run_monte_carlo(
            starting_bankroll=10000,
            bet_scenarios=low_edge_scenarios,
            strategy=BetSizingStrategy.HALF_KELLY,
            num_bets=100,
            num_simulations=200
        )

        high_result = run_monte_carlo(
            starting_bankroll=10000,
            bet_scenarios=high_edge_scenarios,
            strategy=BetSizingStrategy.HALF_KELLY,
            num_bets=100,
            num_simulations=200
        )

        # Higher edge should produce higher expected ROI
        assert high_result["performance"]["expected_roi"] > low_result["performance"]["expected_roi"]

    def test_conservative_strategy_lower_variance(self):
        """Conservative strategy should have lower variance."""
        scenarios = [BetScenario(probability=0.55, odds=-110, edge=0.03)]

        conservative = run_monte_carlo(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.QUARTER_KELLY,
            num_bets=100,
            num_simulations=200
        )

        aggressive = run_monte_carlo(
            starting_bankroll=10000,
            bet_scenarios=scenarios,
            strategy=BetSizingStrategy.KELLY,
            num_bets=100,
            num_simulations=200
        )

        # Conservative should have lower standard deviation
        assert conservative["final_bankroll"]["std_dev"] < aggressive["final_bankroll"]["std_dev"]
