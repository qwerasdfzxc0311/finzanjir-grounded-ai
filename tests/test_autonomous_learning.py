from finzanjir_ai.intel.autonomous_learning import (
    AutonomousResearchEngine, AutonomousResearchPolicy, CandidateStatus,
    KnowledgePromotionGate, ResearchSource,
)


class Discoverer:
    def discover(self, source, limit):
        return [("https://intel.example/advisory/1", "Security advisory")][:limit]


class Fetcher:
    def fetch(self, url):
        return ("A public security advisory.", "text/plain", url)


class NoNetwork:
    def discover(self, source, limit):
        raise AssertionError("offline mode must not discover over the network")


class NoFetch:
    def fetch(self, url):
        raise AssertionError("offline mode must not fetch over the network")


class OfflineStore:
    def iter_cached(self, source, limit):
        return [("cache://intel.example/advisory/1", "Cached advisory",
                 "A locally cached public advisory.", "text/plain",
                 "https://intel.example/advisory/1")][:limit]


def source():
    return ResearchSource("src-1", "intel.example", "official_advisory", enabled=True)


def test_autonomous_cycle_is_disabled_by_default():
    engine = AutonomousResearchEngine(AutonomousResearchPolicy(), Discoverer(), Fetcher())
    assert engine.run_cycle([source()]) == []


def test_online_cycle_requires_separate_online_enable():
    policy = AutonomousResearchPolicy(enabled=True, online_enabled=False)
    engine = AutonomousResearchEngine(policy, Discoverer(), Fetcher())
    assert engine.run_cycle([source()], offline=False) == []


def test_enabled_online_cycle_quarantines_candidates_for_review():
    policy = AutonomousResearchPolicy(enabled=True, online_enabled=True)
    engine = AutonomousResearchEngine(policy, Discoverer(), Fetcher())
    candidates = engine.run_cycle([source()])
    assert len(candidates) == 1
    assert candidates[0].status == CandidateStatus.QUARANTINED
    assert "human review required" in candidates[0].review_reasons[0]


def test_offline_cycle_uses_only_local_cache_and_never_network():
    policy = AutonomousResearchPolicy(enabled=True, online_enabled=False)
    engine = AutonomousResearchEngine(policy, NoNetwork(), NoFetch(), OfflineStore())
    candidates = engine.run_cycle([source()], offline=True)
    assert len(candidates) == 1
    assert candidates[0].url == "https://intel.example/advisory/1"


def test_offline_mode_without_local_store_fails_closed():
    policy = AutonomousResearchPolicy(enabled=True, online_enabled=True)
    engine = AutonomousResearchEngine(policy, Discoverer(), Fetcher())
    assert engine.run_cycle([source()], offline=True) == []


def test_promotion_requires_license_source_sensitive_review_and_human_review():
    policy = AutonomousResearchPolicy(enabled=True, online_enabled=True)
    candidate = AutonomousResearchEngine(policy, Discoverer(), Fetcher()).run_cycle([source()])[0]
    gate = KnowledgePromotionGate(required_reviewers=1, approved_license_ids={"CC-BY-4.0"})
    base = dict(reviewer_ids=["reviewer"], license_id="CC-BY-4.0", source_verified=True)
    assert not gate.approve(candidate, **base)
    assert not gate.approve(candidate, **base, sensitive_data_reviewed=True, reviewer_ids=[])
    assert gate.approve(candidate, **base, sensitive_data_reviewed=True)


def test_sensitive_data_never_passes_promotion_gate():
    policy = AutonomousResearchPolicy(enabled=True, online_enabled=True)
    candidate = AutonomousResearchEngine(policy, Discoverer(), Fetcher()).run_cycle([source()])[0]
    gate = KnowledgePromotionGate(required_reviewers=1, approved_license_ids={"CC-BY-4.0"})
    base = dict(reviewer_ids=["reviewer"], license_id="CC-BY-4.0",
                source_verified=True, sensitive_data_reviewed=True)
    assert not gate.approve(candidate, **base, contains_personal_data=True)
    assert not gate.approve(candidate, **base, contains_customer_or_bank_data=True)


def test_prohibited_collection_pattern_cannot_be_promoted():
    class ProhibitedFetcher:
        def fetch(self, url):
            return ("stolen credentials found", "text/plain", url)
    policy = AutonomousResearchPolicy(enabled=True, online_enabled=True)
    candidate = AutonomousResearchEngine(policy, Discoverer(), ProhibitedFetcher()).run_cycle([source()])[0]
    gate = KnowledgePromotionGate(required_reviewers=1, approved_license_ids={"CC-BY-4.0"})
    assert not gate.approve(candidate, reviewer_ids=["reviewer"], license_id="CC-BY-4.0",
                            source_verified=True, sensitive_data_reviewed=True)
