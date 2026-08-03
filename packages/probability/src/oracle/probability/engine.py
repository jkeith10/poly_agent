import math
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EvidenceSignal:
    likelihood_ratio: Decimal
    reliability: Decimal
    independence_group: str


@dataclass(frozen=True, slots=True)
class Posterior:
    probability: Decimal
    lower_bound: Decimal
    upper_bound: Decimal


class BayesianEngine:
    """Bayesian updater that shrinks repeated evidence from a common origin."""

    def update(self, prior: Decimal, evidence: list[EvidenceSignal]) -> Posterior:
        if not Decimal("0") < prior < Decimal("1"):
            raise ValueError("prior must be strictly between zero and one")
        log_odds = math.log(float(prior / (1 - prior)))
        occurrences: dict[str, int] = {}
        information = 0.0
        for item in evidence:
            if item.likelihood_ratio <= 0 or not Decimal(0) <= item.reliability <= Decimal(1):
                raise ValueError("invalid evidence signal")
            count = occurrences.get(item.independence_group, 0)
            dependence_discount = 1 / (count + 1)
            weight = float(item.reliability) * dependence_discount
            log_odds += math.log(float(item.likelihood_ratio)) * weight
            information += abs(math.log(float(item.likelihood_ratio))) * weight
            occurrences[item.independence_group] = count + 1
        posterior = 1 / (1 + math.exp(-log_odds))
        uncertainty = min(0.24, 0.18 / math.sqrt(1 + information))
        return Posterior(
            probability=Decimal(str(posterior)),
            lower_bound=Decimal(str(max(0.001, posterior - uncertainty))),
            upper_bound=Decimal(str(min(0.999, posterior + uncertainty))),
        )
