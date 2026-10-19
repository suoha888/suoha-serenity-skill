"""Behavioral regressions: plausible-looking reports must not bypass integrity gates."""
import copy
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_research_output import validate_output, validate_component
from validate_research_bundle import validate_bundle, object_hash
from serenity_scorecard import score
from build_local_index import build_index, search_index
from distill_archive import unique_lineage, event_type_for
from method_catalog import catalog
from test_v2 import normalized_record
from distill_archive import distill


def synthetic_bundle():
    output = json.loads((ROOT / "evals/fixtures/research-output.synthetic.json").read_text(encoding="utf-8"))
    components = json.loads((ROOT / "evals/fixtures/company-research-components.synthetic.json").read_text(encoding="utf-8"))
    bundle = {"research_output": output, "method_cards": [], "thesis_events": [], "method_reviews": []}
    for singular, plural in (("bottleneck_assessment", "bottleneck_assessments"), ("company_profile", "company_profiles"),
                             ("market_snapshot", "market_snapshots"), ("valuation_snapshot", "valuation_snapshots")):
        bundle[plural] = [components[singular]]
    time = output["research_cutoff"]
    bundle["evidence"] = [{"schema_version": "2", "evidence_id": eid, "source": "synthetic://source",
                           "source_type": "company_ir", "published_at": time, "known_at": time, "captured_at": time,
                           "content_hash": "0" * 64, "excerpt": "Synthetic fixture, not real market evidence.",
                           "provenance": {"adapter": "synthetic", "locator": "synthetic://source", "extraction_version": "test"},
                           "access_level": "synthetic", "source_partition": "synthetic", "evidence_grade": "primary",
                           "independence_group": eid, "review_status": "human_reviewed"} for eid in output["evidence_ids"]]
    bundle["claims"] = [{"schema_version": "2", "claim_id": "claim:synthetic-1", "text": "Synthetic partial claim",
                         "epistemic_type": "hypothesis", "entity_ids": [], "as_of": time, "asserted_at": time, "known_at": time,
                         "evidence_ids": [output["evidence_ids"][0]], "counterevidence_ids": [],
                         "evidence_state": "not_established", "confidence": "low", "access_level": "synthetic",
                         "source_partition": "synthetic", "source_record_ids": ["fixture:1"],
                         "source_lineage": [{"source_partition": "synthetic", "source_file": "synthetic://source",
                                             "source_record_id": "fixture:1", "source_sha256": "0" * 64}],
                         "review_status": "pending", "extraction_version": "test"}]
    return bundle


class ReleaseIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.bundle = synthetic_bundle()
        self.output = self.bundle["research_output"]

    def errors(self):
        return validate_bundle(self.bundle, ROOT / "schemas")

    def test_valid_bundle_resolves_all_references(self):
        self.assertEqual(self.errors(), [])
        published = json.loads((ROOT / "evals/fixtures/research-bundle.synthetic.json").read_text(encoding="utf-8"))
        self.assertEqual(published, self.bundle)

    def test_derived_index_rejects_access_downgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            posts = root / "normalized/public/posts.jsonl"
            posts.parent.mkdir(parents=True)
            posts.write_text(json.dumps(normalized_record("p1", "public", "2026-01-01T00:00:00Z", "test")) + "\n", encoding="utf-8")
            claims = root / "derived/public/claims.jsonl"
            claims.parent.mkdir(parents=True)
            claims.write_text(json.dumps({"claim_id": "c1", "source_partition": "public", "access_level": "subscription"}) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "partition mismatch"):
                build_index(root, root / "index.sqlite3", {"public"})

    def test_same_ticker_does_not_merge_independent_theses(self):
        records = [normalized_record("z", "public", "2026-01-01T00:00:00Z", "$TEST thesis bottleneck"),
                   normalized_record("a", "public", "2026-02-01T00:00:00Z", "$TEST invalidate thesis bottleneck")]
        layers = distill(records, "public", None, min_support=1)
        events = layers["thesis-events.jsonl"]
        self.assertEqual(len(events), 2)
        self.assertNotEqual(events[0]["thesis_id"], events[1]["thesis_id"])
        self.assertLess(events[0]["event_at"], events[1]["event_at"])

    def test_missing_evidence_objects_fail(self):
        self.bundle["evidence"] = []
        self.assertTrue(any("unresolved:evidence_ids" in e for e in self.errors()))

    def test_duplicate_objects_fail(self):
        self.bundle["company_profiles"] *= 2
        self.assertTrue(any("duplicate_id" in e for e in self.errors()))

    def test_component_issuer_mismatch_fails(self):
        self.bundle["market_snapshots"][0]["ticker"] = "OTHER"
        self.assertTrue(any("issuer_mismatch:ticker" in e for e in self.errors()))

    def test_primary_candidate_needs_its_own_snapshots(self):
        other = copy.deepcopy(self.bundle["company_profiles"][0])
        other["company_id"] = "company:other"
        self.bundle["company_profiles"].append(other)
        for key in ("market_snapshots", "valuation_snapshots"):
            self.bundle[key][0]["company_id"] = "company:other"
        self.assertTrue(any("primary_candidate_missing" in e for e in self.errors()))

    def test_evidence_reverse_claim_links_must_resolve(self):
        self.bundle["evidence"][0]["supports_claim_ids"] = ["claim:missing"]
        self.assertTrue(any("claim_not_found" in e for e in self.errors()))

    def test_assertion_dates_and_valuation_numbers_are_checked(self):
        self.bundle["claims"][0]["asserted_at"] = "2099-01-01T00:00:00Z"
        self.assertTrue(any("after_cutoff" in e for e in self.errors()))
        for number in (-1, "garbage", math.inf, 10**400):
            value = copy.deepcopy(self.bundle["valuation_snapshots"][0])
            value["market_cap"] = number
            self.assertTrue(validate_component(value, ROOT / "schemas/valuation-snapshot.schema.json"))

    def test_output_wrong_types_return_diagnostics(self):
        self.output["research_language"] = []
        self.assertTrue(validate_output(self.output, ROOT / "schemas"))

    def test_supported_conclusion_cannot_use_partial_rungs(self):
        self.output["research_conclusion"] = "supported"
        self.assertTrue(any("requires_ladder_stage" in e for e in self.errors()))

    def test_empty_evidence_cannot_support_rung(self):
        self.output["validation_ladder"][0].update(status="supported", evidence_ids=[], missing_proof=[])
        self.assertTrue(any("requires_evidence" in e for e in self.errors()))

    def test_supported_stage_cannot_retain_missing_proof(self):
        self.output["validation_ladder"][0]["status"] = "supported"
        self.assertTrue(any("supported_stage_has_missing_proof" in e for e in self.errors()))

    def test_social_evidence_cannot_confirm_operating_rung(self):
        self.output["validation_ladder"][0].update(status="supported", missing_proof=[])
        self.bundle["evidence"][0]["source_type"] = "social_post"
        self.assertTrue(any("independent_evidence" in e for e in self.errors()))

    def test_future_lineage_capacity_valuation_are_rejected(self):
        paths = [("bottleneck_assessments", "capacity_states"), ("valuation_snapshots", "metrics")]
        for collection, field in paths:
            with self.subTest(collection=collection):
                bundle = copy.deepcopy(self.bundle)
                bundle[collection][0][field][0]["as_of"] = "2099-01-01T00:00:00Z"
                self.assertTrue(any("after_cutoff" in e for e in validate_bundle(bundle, ROOT / "schemas")))
        self.output["source_lineage"][0]["known_at"] = "2099-01-01T00:00:00Z"
        self.assertTrue(any("after_cutoff" in e for e in self.errors()))

    def test_mixed_partition_in_component_fails(self):
        self.bundle["company_profiles"][0]["source_lineage"][0]["source_partition"] = "subscription"
        self.assertTrue(any("partition_mismatch" in e for e in self.errors()))

    def test_missing_components_and_candidate_fail(self):
        self.output["company_profile_ids"] = []
        self.assertTrue(any("required_component_ids" in e for e in self.errors()))

    def test_market_mutants_fail(self):
        mutations = {"price": [-1, math.nan, math.inf, 10**400, "42.5", True], "market_cap": [1],
                     "shares_basis": ["weighted_average_basic"], "market_cap_currency": ["JPY"],
                     "price_source_evidence_ids": [[]], "shares_as_of": [None], "price_as_of": ["2001-01-01T00:00:00Z"]}
        for field, values in mutations.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    market = copy.deepcopy(self.bundle["market_snapshots"][0])
                    market[field] = value
                    self.assertTrue(validate_component(market, ROOT / "schemas/market-snapshot.schema.json"))

    def test_null_collections_return_errors_not_crashes(self):
        for key in self.bundle:
            bundle = copy.deepcopy(self.bundle)
            bundle[key] = None
            self.assertTrue(validate_bundle(bundle, ROOT / "schemas"), key)

    def test_method_approval_is_bound_to_content_and_can_be_revoked(self):
        record = normalized_record("fixture:method", "public", "2026-01-01T00:00:00Z", "Qualification bottleneck capacity supply chain")
        card = distill([record], "public", None, min_support=1)["method-cards.jsonl"][0]
        # Entirely synthetic record, relabel fixture partition consistently.
        card.update(access_level="synthetic", source_partition="synthetic", review_status="human_reviewed", source_claim_ids=[])
        for item in card["source_lineage"]:
            item["source_partition"] = "synthetic"
        self.bundle["method_cards"] = [card]
        self.output["method_application"] = {"status": "applied", "cards": [{"method_card_id": card["method_id"],
            "review_status": "human_reviewed", "reasoning_pattern": card["reasoning_pattern"], "validation_questions": [
                {"question": "Is qualification a constraint?", "verification_status": "unknown", "evidence_ids": []}]}]}
        self.assertTrue(any("method_review_record_required" in e for e in self.errors()))
        review = {"method_id": card["method_id"], "decision": "approved", "reviewer": "synthetic-reviewer",
                  "reviewed_at": "2026-09-01T00:00:00Z", "card_sha256": object_hash(card)}
        self.bundle["method_reviews"] = [review]
        self.assertEqual(self.errors(), [])
        self.bundle["method_reviews"].append(dict(review, decision="rejected", reviewed_at="2026-09-02T00:00:00Z"))
        self.assertTrue(any("method_review_record_required" in e for e in self.errors()))
        self.bundle["method_reviews"] = [review]
        card["reasoning_pattern"] += " Changed."
        self.assertTrue(any("method_review_record_required" in e for e in self.errors()))

    def test_method_catalog_does_not_promote_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = [normalized_record("fixture:method", "public", "2026-01-01T00:00:00Z", "Qualification bottleneck capacity supply chain")]
            cards = distill(records, "public", None, min_support=1)["method-cards.jsonl"]
            posts = root / "normalized/public/posts.jsonl"
            methods = root / "derived/public/method-cards.jsonl"
            posts.parent.mkdir(parents=True)
            methods.parent.mkdir(parents=True)
            posts.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
            methods.write_text("\n".join(json.dumps(card) for card in cards), encoding="utf-8")
            result = catalog(root, "public", "2026-10-17T00:00:00Z", approved_only=True)
            self.assertEqual(result["cards"], [])
            self.assertEqual(result["status"], "no_approved_match")
            self.assertTrue(catalog(root, "public", "2026-10-17T00:00:00Z")["cards"])
            self.assertEqual(catalog(root, "public", "2025-10-17T00:00:00Z")["cards"], [])

    def test_contradiction_never_becomes_strong(self):
        value = {"dimensions": {key: {"status": "contradicted", "rating": 5, "evidence_ids": ["counter:1"]}
                                for key in ("architecture_necessity", "bottleneck_strength", "evidence_quality", "economic_value_capture")}}
        result, priority = score(value)
        self.assertEqual(priority, "low")
        self.assertEqual(result["dimensions"]["architecture_necessity"]["status"], "contradicted")

    def test_scorecard_requires_finite_ratings_and_evidence(self):
        for value in (math.nan, math.inf, True):
            with self.assertRaises(ValueError):
                score({"dimensions": {"risk": {"rating": value}}})
        with self.assertRaises(ValueError):
            score({"dimensions": {"risk": {"status": "supported", "rating": 5}}})

    def test_negation_does_not_invalidate_and_close_is_recognized(self):
        self.assertIsNone(event_type_for("This does not invalidate the thesis."))
        self.assertEqual(event_type_for("The thesis has closed."), "close")

    def test_provenance_taint_cannot_be_relabelled(self):
        record = {"id": "1", "access_level": "public", "source_partition": "public", "provenance": {
            "source_file": "test", "source_record_id": "1", "source_sha256": "0" * 64, "source_partition": "subscription"}}
        with self.assertRaises(ValueError):
            unique_lineage([record], "public")

    def test_index_normalizes_offsets_and_failed_build_preserves_old_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            posts = root / "normalized/public/posts.jsonl"
            posts.parent.mkdir(parents=True)
            record = {"id": "1", "access_level": "public", "source_partition": "public",
                      "created_at": "2026-09-11T23:30:00-02:00", "text": "bottleneck", "provenance": {}}
            posts.write_text(json.dumps(record) + "\n", encoding="utf-8")
            db = root / "index.sqlite3"
            build_index(root, db, {"public"})
            self.assertEqual(search_index(db, "bottleneck", "public", 10, as_of="2026-09-12T00:00:00Z"), [])
            self.assertEqual(len(search_index(db, "bottleneck", "public", 10, as_of="2026-09-12T02:00:00Z")), 1)
            original = db.read_bytes()
            posts.write_text("{invalid json", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_index(root, db, {"public"})
            self.assertEqual(db.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
