from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PositionSide(StrEnum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class TradingCostModel(BaseModel):
    """Estimated round-trip costs, expressed in basis points.

    Values must come from the venue and account actually being studied. The
    defaults are deliberately zero so a caller cannot mistake them for quotes.
    """

    model_config = ConfigDict(frozen=True)

    spread_bps: Decimal = Field(default=Decimal("0"), ge=0)
    slippage_bps: Decimal = Field(default=Decimal("0"), ge=0)
    commission_bps: Decimal = Field(default=Decimal("0"), ge=0)
    financing_bps: Decimal = Field(default=Decimal("0"), ge=0)

    @property
    def total_bps(self) -> Decimal:
        return self.spread_bps + self.slippage_bps + self.commission_bps + self.financing_bps


def net_return_fraction(
    *, side: PositionSide, entry_price: Decimal, exit_price: Decimal, costs: TradingCostModel,
) -> Decimal:
    """Return per unit of notional after explicit estimated round-trip costs."""
    if entry_price <= 0 or exit_price <= 0:
        raise ValueError("entry and exit prices must be positive")
    if side is PositionSide.FLAT:
        return Decimal("0")
    raw = (exit_price - entry_price) / entry_price
    directional = raw if side is PositionSide.LONG else -raw
    return directional - (costs.total_bps / Decimal("10000"))
