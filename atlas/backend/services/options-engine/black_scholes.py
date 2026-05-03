"""
Black-Scholes Greeks computation for options without provided Greeks.
Used when Yahoo Finance or Tradier don't return delta/gamma.

CRITICAL GEX SIGN CONVENTION:
- Dealers are SHORT calls to customers → dealer delta = NEGATIVE for calls
- Dealers are SHORT puts to customers → dealer delta = POSITIVE for puts
- Call gamma exposure to dealer: POSITIVE (dealer is long gamma on calls? NO)
  Actually: Market makers are typically LONG options (buy from customers who buy puts for protection)
  Standard GEX convention:
  - Call OI: dealers typically SHORT → GEX_call = +gamma (they must buy as price rises)
  - Put OI: dealers typically LONG (bought puts from retail) → GEX_put = -gamma (they sell as price falls)

Net GEX > 0: dealers are long gamma → they SUPPRESS volatility (buy dips, sell rips)
Net GEX < 0: dealers are short gamma → they AMPLIFY volatility (sell dips, buy rips)
"""
import math
from typing import Optional


def _N(x: float) -> float:
    """Cumulative standard normal distribution."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _n(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def black_scholes_greeks(
    S: float,      # Underlying price
    K: float,      # Strike price
    T: float,      # Time to expiry in years
    r: float,      # Risk-free rate (annualized)
    sigma: float,  # Implied volatility (annualized)
    option_type: str = "call",  # "call" or "put"
) -> dict:
    """
    Compute Black-Scholes price and full Greeks.
    Returns dict with: price, delta, gamma, theta, vega, rho, d1, d2
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {"price": 0, "delta": 0, "gamma": 0, "theta": 0, "vega": 0}

    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        if option_type == "call":
            price = S * _N(d1) - K * math.exp(-r * T) * _N(d2)
            delta = _N(d1)
            rho = K * T * math.exp(-r * T) * _N(d2) / 100
        else:
            price = K * math.exp(-r * T) * _N(-d2) - S * _N(-d1)
            delta = _N(d1) - 1  # Negative for puts
            rho = -K * T * math.exp(-r * T) * _N(-d2) / 100

        gamma = _n(d1) / (S * sigma * math.sqrt(T))
        # Theta in daily terms (divide by 365)
        theta = (
            -S * _n(d1) * sigma / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T) * (_N(d2) if option_type == "call" else _N(-d2))
        ) / 365
        vega = S * _n(d1) * math.sqrt(T) / 100  # Per 1% vol change

        return {
            "price": round(price, 4),
            "delta": round(delta, 6),
            "gamma": round(gamma, 8),
            "theta": round(theta, 6),
            "vega": round(vega, 6),
            "rho": round(rho, 6),
            "d1": round(d1, 6),
            "d2": round(d2, 6),
            "iv": round(sigma, 6),
        }
    except (ValueError, ZeroDivisionError, OverflowError):
        return {"price": 0, "delta": 0, "gamma": 0, "theta": 0, "vega": 0}


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
    max_iterations: int = 100,
    precision: float = 1e-6,
) -> Optional[float]:
    """
    Compute implied volatility via Newton-Raphson method.
    Returns IV as decimal (e.g., 0.20 = 20%).
    """
    if market_price <= 0 or T <= 0 or S <= 0 or K <= 0:
        return None

    # Initial guess via Brenner-Subrahmanyam approximation
    sigma = math.sqrt(2 * math.pi / T) * market_price / S

    for _ in range(max_iterations):
        greeks = black_scholes_greeks(S, K, T, r, sigma, option_type)
        theo_price = greeks["price"]
        vega = greeks["vega"] * 100  # Convert back from per 1% move

        if vega < 1e-10:
            break

        diff = theo_price - market_price
        if abs(diff) < precision:
            break

        sigma -= diff / vega

        if sigma <= 0:
            sigma = 0.001
        elif sigma > 10:  # Cap at 1000% IV
            return None

    return round(sigma, 6) if 0.001 <= sigma <= 10 else None


def time_to_expiry_years(expiry_date: str, as_of_datetime=None) -> float:
    """
    Compute T (time to expiry in years) with second precision.
    Uses trading calendar: 252 trading days/year but actual calendar time.
    """
    from datetime import datetime
    import pytz

    ET = pytz.timezone("America/New_York")

    if as_of_datetime is None:
        as_of_datetime = datetime.now(ET)
    elif as_of_datetime.tzinfo is None:
        as_of_datetime = ET.localize(as_of_datetime)

    # Options expire at 4:00 PM ET on expiration day
    exp = datetime.strptime(expiry_date, "%Y-%m-%d")
    exp = ET.localize(exp.replace(hour=16, minute=0, second=0))

    delta = (exp - as_of_datetime).total_seconds()
    if delta <= 0:
        return 0.0

    # Use calendar days / 365 for precision (not trading days)
    return delta / (365 * 24 * 3600)
