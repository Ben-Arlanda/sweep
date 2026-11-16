"""What an LLM call cost, worked out from its tokens and the model that served it.

Not "pricing": Sweep has no grocery prices (ADR 0010). This is only what we pay Anthropic.

We store tokens, never dollars, and price them here when asked. If a price changes,
only this table changes and old token counts are still right.

The four token kinds cost different amounts. Cached input is the big one: an agent turn
re-sends the same tools, system prompt and history on every step, and reading that back
from the cache costs a small fraction of sending it fresh.
"""

from dataclasses import dataclass
from decimal import Decimal

MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class Usage:
    model: str  # the model that actually answered (a fallback can differ from the asked one)
    input_tokens: int  # fresh input, full price
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def all_input(self) -> int:
        """Every input token, whatever it cost. The daily budget counts these."""
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens


@dataclass(frozen=True)
class Rates:
    """US dollars per million tokens."""

    input: Decimal
    output: Decimal
    cache_read: Decimal
    # Some models charge more once the prompt passes a size: (threshold, input, output).
    long_prompt: tuple[int, Decimal, Decimal] | None = None

    @property
    def cache_write(self) -> Decimal:
        # 5-minute cache writes cost 1.25x fresh input (the TTL we use).
        return self.input * Decimal("1.25")


# Anthropic API list prices, checked 2026-11-15. Update the date when you change them.
PRICES_CHECKED = "2026-11-15"
RATES: dict[str, Rates] = {
    "claude-opus-5-5": Rates(Decimal("4"), Decimal("20"), Decimal("0.20")),
    "claude-sonnet-5-5": Rates(Decimal("2"), Decimal("10"), Decimal("0.10")),
    "claude-sonnet-5": Rates(Decimal("2"), Decimal("10"), Decimal("0.20")),
    # ⚠️ Haiku 5.5's cache-read price wasn't in the docs we checked; 0.1x input is the
    # usual rate. It's a tiny share of any bill either way.
    "claude-haiku-5-5": Rates(
        Decimal("0.10"),
        Decimal("0.50"),
        Decimal("0.01"),
        long_prompt=(100_000, Decimal("0.50"), Decimal("2.50")),
    ),
}


def rates_for(model: str) -> Rates | None:
    """The longest matching name wins, so "claude-sonnet-5-5-2026..." isn't Sonnet 5."""
    matches = [name for name in RATES if model == name or model.startswith(name + "-")]
    return RATES[max(matches, key=len)] if matches else None


def cost_usd(usage: Usage) -> Decimal | None:
    """None for a model we have no price for: no number beats a wrong number."""
    rates = rates_for(usage.model)
    if rates is None:
        return None
    input_rate, output_rate = rates.input, rates.output
    if rates.long_prompt and usage.all_input > rates.long_prompt[0]:
        _, input_rate, output_rate = rates.long_prompt
    total = (
        usage.input_tokens * input_rate
        + usage.output_tokens * output_rate
        + usage.cache_read_tokens * rates.cache_read
        + usage.cache_write_tokens * rates.cache_write
    )
    return total / MILLION
