"""Combines the ML score with the URLhaus blocklist signal and the RDAP
domain-age signal into one explainable verdict, instead of returning a
single raw ML confidence number.

A confirmed URLhaus hit overrides the ML score outright (it's a known-bad
URL, not a guess) -- checked first, same as before. Otherwise the verdict
follows the ML score, with one addition: an old, established domain (>=365
days, per RDAP) overrides a *borderline* ML phishing call (not an
overwhelming one -- see NEW_DOMAIN_THRESHOLD note below) to legitimate.
This directly targets the residual false positives documented in
PROJECT_PROGRESS.md (`github.com/anthropics`, `twitter.com/anthropicai`):
a lexical-only model has no way to know a domain is long-established, so
this is exactly the missing evidence.

A newly-registered domain does NOT get the symmetric treatment (auto-flip
a "legitimate" ML call to phishing) -- deliberately, to avoid a new class
of false positives on genuinely new legitimate sites (personal pages,
startups, etc.), which are common and untested here. It's surfaced in the
reason text instead, same asymmetric pattern as URLhaus's "not_listed"
(absence of confirming evidence doesn't invert a verdict, only a positive
hit does).
"""

# An ML score this confident is treated as solid evidence on its own --
# domain age only rescues genuinely borderline calls, not overwhelming ones.
ESTABLISHED_OVERRIDE_CEILING = 0.9

# A rescued call is a mitigated, moderate-confidence verdict by design --
# not the raw ML complement (which would read as a *low*-confidence "safe"
# verdict, since the ML score itself still leans phishing).
RESCUED_VERDICT_CONFIDENCE = 0.65


def combine_verdict(
    phishing_probability: float, urlhaus_status: str, domain_age_status: str = "unknown"
) -> dict:
    if urlhaus_status == "listed":
        return {
            "is_phishing": True,
            "confidence": max(phishing_probability, 0.99),
            "verdict_reason": "Confirmed malicious — found on the URLhaus blocklist",
        }

    is_phishing = phishing_probability >= 0.5
    confidence = phishing_probability if is_phishing else 1 - phishing_probability
    reason = "Flagged as phishing by the ML model" if is_phishing else "Looks safe"

    if (
        is_phishing
        and domain_age_status == "established"
        and phishing_probability < ESTABLISHED_OVERRIDE_CEILING
    ):
        is_phishing = False
        confidence = RESCUED_VERDICT_CONFIDENCE
        reason = "ML model flagged this, but the domain is long-established — likely a false positive"
    elif not is_phishing and domain_age_status == "new":
        reason += " (note: domain was registered very recently)"

    if urlhaus_status == "unknown":
        reason += " (URLhaus check unavailable)"
    if domain_age_status == "unknown":
        reason += " (domain age unavailable)"

    return {"is_phishing": is_phishing, "confidence": confidence, "verdict_reason": reason}
