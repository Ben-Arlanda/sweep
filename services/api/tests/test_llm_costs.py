"""What a model call costs, worked out from its tokens (slice 8)."""

from decimal import Decimal

from app.llm import agent_request_options
from app.llm_costs import Usage, cost_usd


def priced(usage: Usage) -> Decimal:
    cost = cost_usd(usage)
    assert cost is not None
    return cost


def test_each_token_kind_has_its_own_price() -> None:
    usage = Usage(
        model="claude-sonnet-5-5",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        cache_write_tokens=1_000_000,
    )
    # $2 input + $10 output + $0.10 cache read + $2.50 cache write (1.25x input)
    assert cost_usd(usage) == Decimal("14.60")


def test_cached_input_is_much_cheaper_than_fresh_input() -> None:
    fresh = Usage(model="claude-sonnet-5-5", input_tokens=10_000, output_tokens=0)
    cached = Usage(
        model="claude-sonnet-5-5", input_tokens=0, output_tokens=0, cache_read_tokens=10_000
    )
    assert priced(cached) * 20 == priced(fresh)


def test_haiku_costs_a_twentieth_of_sonnet() -> None:
    sonnet = Usage(model="claude-sonnet-5-5", input_tokens=5_000, output_tokens=500)
    haiku = Usage(model="claude-haiku-5-5", input_tokens=5_000, output_tokens=500)
    assert priced(haiku) * 20 == priced(sonnet)


def test_haiku_long_prompts_cost_more() -> None:
    # Haiku 5.5 charges $0.50 / $2.50 when the prompt is over 100K tokens.
    usage = Usage(model="claude-haiku-5-5", input_tokens=200_000, output_tokens=1_000)
    assert cost_usd(usage) == Decimal("0.1025")


def test_all_input_counts_every_kind_for_the_daily_budget() -> None:
    usage = Usage(
        model="claude-sonnet-5-5",
        input_tokens=100,
        output_tokens=50,
        cache_read_tokens=1_000,
        cache_write_tokens=200,
    )
    assert usage.all_input == 1_300


def test_unknown_model_has_no_cost_rather_than_a_wrong_one() -> None:
    assert cost_usd(Usage(model="claude-made-up", input_tokens=10, output_tokens=10)) is None


def test_a_dated_model_name_from_the_api_still_prices() -> None:
    # The API can report the model it served with a suffix; price by the family.
    usage = Usage(model="claude-sonnet-5-5-20260901", input_tokens=1_000_000, output_tokens=0)
    assert cost_usd(usage) == Decimal("2.00")


def test_sonnet_asks_for_the_server_side_fallback() -> None:
    options = agent_request_options("claude-sonnet-5-5")
    assert options["fallbacks"] == "default"
    assert options["betas"] == ["server-side-fallback-2026-07-01"]


def test_haiku_does_not_ask_for_a_fallback_it_does_not_have() -> None:
    # Haiku 5.5 has no server-side fallback: sending one would be a 400.
    options = agent_request_options("claude-haiku-5-5")
    assert "fallbacks" not in options
    assert "betas" not in options
    assert "thinking" in options  # every model gets the thinking summary


def test_both_models_return_a_thinking_summary_for_traces() -> None:
    # Claude 5.5 models hide thinking by default ("omitted": empty blocks). A summary
    # costs no extra tokens and shows in Langfuse why the agent chose each step. It
    # never reaches the Member: the chat shows text blocks only.
    for model in ("claude-sonnet-5-5", "claude-haiku-5-5"):
        assert agent_request_options(model)["thinking"] == {
            "type": "adaptive",
            "display": "summarized",
        }
