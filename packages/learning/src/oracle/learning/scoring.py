import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ForecastScore:
    brier: float
    log_loss: float


def evaluate_forecast(probability: float, outcome: bool) -> ForecastScore:
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between zero and one")
    actual = float(outcome)
    clipped = min(1 - 1e-15, max(1e-15, probability))
    return ForecastScore((probability - actual) ** 2, -(actual * math.log(clipped) + (1 - actual) * math.log(1 - clipped)))
