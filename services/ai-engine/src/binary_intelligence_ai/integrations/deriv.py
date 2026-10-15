from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DerivIntegrationChecklist(BaseModel):
    model_config = ConfigDict(frozen=True)

    official_api_documented: bool = True
    app_registered: bool = False
    demo_credentials_configured: bool = False
    regional_eligibility_confirmed: bool = False
    terms_and_data_rights_confirmed: bool = False
    asset_and_contract_available: bool = False
    five_minute_duration_confirmed: bool = False
    settlement_rule_confirmed: bool = False
    payout_observed_before_purchase: bool = False
    rate_limits_tested: bool = False
    disconnect_recovery_tested: bool = False
    reconciliation_tested: bool = False


class DerivIntegrationDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    official_api_available: bool
    public_discovery_ready: bool
    demo_trading_ready: bool
    real_trading_ready: bool
    reasons: tuple[str, ...]


def evaluate_deriv_integration(checklist: DerivIntegrationChecklist) -> DerivIntegrationDecision:
    required_for_demo = {
        "app registration": checklist.app_registered,
        "demo credentials": checklist.demo_credentials_configured,
        "regional eligibility": checklist.regional_eligibility_confirmed,
        "terms and data rights": checklist.terms_and_data_rights_confirmed,
        "asset and contract availability": checklist.asset_and_contract_available,
        "five-minute duration": checklist.five_minute_duration_confirmed,
        "settlement rule": checklist.settlement_rule_confirmed,
        "payout observed before purchase": checklist.payout_observed_before_purchase,
        "rate-limit behavior": checklist.rate_limits_tested,
        "disconnect recovery": checklist.disconnect_recovery_tested,
        "reconciliation": checklist.reconciliation_tested,
    }
    reasons = (() if checklist.official_api_documented else ("pending: official API documentation",)) + tuple(
        f"pending: {name}" for name, complete in required_for_demo.items() if not complete
    )
    demo_ready = checklist.official_api_documented and not reasons
    return DerivIntegrationDecision(
        official_api_available=checklist.official_api_documented,
        public_discovery_ready=(
            checklist.official_api_documented
            and checklist.app_registered
            and checklist.regional_eligibility_confirmed
            and checklist.terms_and_data_rights_confirmed
        ),
        demo_trading_ready=demo_ready,
        real_trading_ready=False,
        reasons=reasons + (("real execution requires the independent Phase 12 review",) if demo_ready else ()),
    )
