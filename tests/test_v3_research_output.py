import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))

from serenity_scorecard import score, to_markdown
from runtime_common import SKILL_VERSION
from validate_research_output import validate_component, validate_output, validate_schema_document


FIXTURE_PATH = SOURCE_ROOT / "evals" / "fixtures" / "research-output.synthetic.json"


class SurohaSerenityV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_synthetic_research_output_is_valid(self):
        self.assertEqual(validate_output(self.fixture, SOURCE_ROOT / "schemas"), [])

    def test_runtime_manifest_version_matches_skill_release(self):
        skill_text = (SOURCE_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(SKILL_VERSION, "8.2.2")
        self.assertIn('version: "8.2.2"', skill_text)

    def test_future_as_of_is_rejected(self):
        value = copy.deepcopy(self.fixture)
        value["as_of"] = "2026-09-13T00:00:00Z"
        errors = validate_output(value, SOURCE_ROOT / "schemas")
        self.assertIn("research_output:as_of_after_research_cutoff", errors)

    def test_composite_score_is_rejected(self):
        value = copy.deepcopy(self.fixture)
        value["final_score"] = 87
        errors = validate_output(value, SOURCE_ROOT / "schemas")
        self.assertTrue(any("forbidden additive" in error for error in errors))

    def test_access_partition_mismatch_is_rejected(self):
        value = copy.deepcopy(self.fixture)
        value["source_partition"] = "public"
        errors = validate_output(value, SOURCE_ROOT / "schemas")
        self.assertIn("research_output:access_partition_mismatch", errors)

    def test_method_card_must_be_reviewed_and_map_to_evidenced_questions(self):
        value = copy.deepcopy(self.fixture)
        value["method_application"] = {
            "status": "applied",
            "cards": [
                {
                    "method_card_id": "method:synthetic-1",
                    "review_status": "human_reviewed",
                    "reasoning_pattern": "Qualification can delay usable supply.",
                    "validation_questions": [
                        {
                            "question": "Does qualification constrain current shipments?",
                            "verification_status": "supported",
                            "evidence_ids": [],
                        }
                    ],
                }
            ],
        }
        errors = validate_output(value, SOURCE_ROOT / "schemas")
        self.assertIn(
            "research_output:method_question_status_requires_evidence:0:0", errors
        )

    def test_applied_method_status_requires_at_least_one_card(self):
        value = copy.deepcopy(self.fixture)
        value["method_application"] = {"status": "applied", "cards": []}
        errors = validate_output(value, SOURCE_ROOT / "schemas")
        self.assertIn("research_output:applied_methods_require_cards", errors)

    def test_candidate_card_cannot_be_claimed_as_applied(self):
        value = copy.deepcopy(self.fixture)
        value["method_application"] = {
            "status": "applied",
            "cards": [
                {
                    "method_card_id": "method:draft-1",
                    "review_status": "candidate",
                    "reasoning_pattern": "A candidate pattern.",
                    "validation_questions": [
                        {
                            "question": "Does this pattern apply?",
                            "verification_status": "unknown",
                            "evidence_ids": [],
                        }
                    ],
                }
            ],
        }
        errors = validate_output(value, SOURCE_ROOT / "schemas")
        self.assertIn(
            "research_output:unreviewed_method_card_applied:0", errors
        )

    def test_nested_evidence_ids_must_exist_in_output_ledger(self):
        value = copy.deepcopy(self.fixture)
        value["validation_ladder"][0]["evidence_ids"] = ["evidence:not-in-ledger"]
        self.assertTrue(
            any(
                "evidence_id_not_in_output_ledger:evidence:not-in-ledger" in error
                for error in validate_output(value, SOURCE_ROOT / "schemas")
            )
        )

    def test_schema_max_items_constraint_is_enforced(self):
        value = copy.deepcopy(self.fixture)
        value["historical_thesis_timeline"] = {
            "status": "events_found",
            "event_ids": [f"event:{index}" for index in range(7)],
        }
        errors = validate_schema_document(
            value, SOURCE_ROOT / "schemas" / "research-output.schema.json"
        )
        self.assertTrue(
            any("historical_thesis_timeline.event_ids:maxItems violation" in error for error in errors)
        )

    def test_manifest_integer_and_minimum_constraints_are_enforced(self):
        manifest = {
            "manifest_version": "2",
            "pipeline_version": "test",
            "created_at": "2026-09-12T00:00:00Z",
            "input": {
                "path": "normalized/public/posts.jsonl",
                "sha256": "0" * 64,
                "record_count": 0,
                "source_record_count": 0,
            },
            "partition": "public",
            "cutoff": None,
            "counts": {},
            "output_files": {},
            "raw_archive_read": False,
            "outcomes_read": False,
            "access_policy": "taint-preserving",
            "holdout_excluded": False,
            "excluded_holdout_count": 0,
        }
        schema = SOURCE_ROOT / "schemas" / "manifest.schema.json"
        self.assertEqual(validate_schema_document(manifest, schema), [])
        manifest["replacement_backup"] = "synthetic://previous-generated-output"
        self.assertEqual(validate_schema_document(manifest, schema), [])

        invalid_type = copy.deepcopy(manifest)
        invalid_type["input"]["record_count"] = 1.5
        self.assertTrue(
            any("input.record_count:type" in error for error in validate_schema_document(invalid_type, schema))
        )

        invalid_minimum = copy.deepcopy(manifest)
        invalid_minimum["input"]["record_count"] = -1
        self.assertTrue(
            any("input.record_count:minimum violation" in error for error in validate_schema_document(invalid_minimum, schema))
        )

    def test_unsupported_schema_keywords_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_path = Path(temp_dir) / "schema.json"
            schema_path.write_text(
                json.dumps({"type": "object", "minProperties": 1}),
                encoding="utf-8",
            )
            errors = validate_schema_document({}, schema_path)
        self.assertIn("schema:unsupported schema keyword:minProperties", errors)

    def test_all_repository_schemas_use_enforced_keywords(self):
        for schema_path in sorted((SOURCE_ROOT / "schemas").glob("*.schema.json")):
            errors = validate_schema_document({}, schema_path)
            unsupported = [error for error in errors if "unsupported schema keyword" in error]
            self.assertEqual(unsupported, [], schema_path.name)

    def test_historical_timeline_status_must_match_event_ids(self):
        value = copy.deepcopy(self.fixture)
        value["historical_thesis_timeline"] = {
            "status": "events_found",
            "event_ids": [],
        }
        errors = validate_output(value, SOURCE_ROOT / "schemas")
        self.assertIn("research_output:events_found_requires_event_ids", errors)

    def test_scorecard_keeps_dimensions_separate(self):
        result, priority = score(
            {
                "ticker": "EXAMPLE",
                "dimensions": {
                    "bottleneck_strength": {"rating": 4},
                    "evidence_quality": {"rating": 4},
                    "economic_value_capture": {"rating": 3},
                    "valuation_context": {"rating": None},
                    "catalyst_timing": {"rating": 2},
                    "risk": {"rating": 3},
                },
            }
        )
        self.assertEqual(priority, "low")
        self.assertNotIn("final_score", result)
        self.assertNotIn("overall_score", result)
        self.assertIn("No composite conviction score", to_markdown(result))

    def test_component_invariants_cover_dimensions_and_current_market_data(self):
        components = json.loads(
            (SOURCE_ROOT / "evals" / "fixtures" / "company-research-components.synthetic.json").read_text(
                encoding="utf-8"
            )
        )
        schema_names = {
            "bottleneck_assessment": "bottleneck-assessment.schema.json",
            "company_profile": "company-profile.schema.json",
            "market_snapshot": "market-snapshot.schema.json",
            "valuation_snapshot": "valuation-snapshot.schema.json",
        }
        for key, schema_name in schema_names.items():
            errors = validate_component(components[key], SOURCE_ROOT / "schemas" / schema_name)
            self.assertEqual(errors, [], key)

        market = copy.deepcopy(components["market_snapshot"])
        market["price"] = None
        self.assertIn(
            "market:current_or_delayed_price_requires_value_and_as_of",
            validate_component(market, SOURCE_ROOT / "schemas" / "market-snapshot.schema.json"),
        )

        bottleneck = copy.deepcopy(components["bottleneck_assessment"])
        bottleneck["dimensions"] = bottleneck["dimensions"][:-1]
        self.assertTrue(
            any(
                error.startswith("bottleneck:missing_dimension:")
                for error in validate_component(
                    bottleneck, SOURCE_ROOT / "schemas" / "bottleneck-assessment.schema.json"
                )
            )
        )

    def test_v4_validation_ladder_is_ordered_and_gates_supported_conclusion(self):
        value = copy.deepcopy(self.fixture)
        value["research_conclusion"] = "supported"
        value["validation_ladder"][0]["status"] = "unknown"
        errors = validate_output(value, SOURCE_ROOT / "schemas")
        self.assertIn(
            "research_output:supported_conclusion_requires_ladder_stage:architecture_necessity",
            errors,
        )

    def test_v4_reflexivity_does_not_promote_post_price_action(self):
        value = copy.deepcopy(self.fixture)
        value["reflexivity_check"] = {
            "social_originated": True,
            "author_market_influence": "high",
            "post_precedes_price_move": "yes",
            "independent_fundamental_confirmation": "no",
            "price_action_is_independent_evidence": "yes",
            "evidence_ids": ["evidence:synthetic-3"],
            "notes": "The price move followed the post, but no independent confirmation exists.",
        }
        self.assertIn(
            "research_output:reflexive_price_action_cannot_be_independent_without_fundamental_confirmation",
            validate_output(value, SOURCE_ROOT / "schemas"),
        )

    def test_v4_component_requires_all_capacity_states(self):
        components = json.loads(
            (SOURCE_ROOT / "evals" / "fixtures" / "company-research-components.synthetic.json").read_text(
                encoding="utf-8"
            )
        )
        value = copy.deepcopy(components["bottleneck_assessment"])
        value["capacity_states"] = value["capacity_states"][:-1]
        errors = validate_component(value, SOURCE_ROOT / "schemas" / "bottleneck-assessment.schema.json")
        self.assertIn("bottleneck:missing_capacity_state:available", errors)


if __name__ == "__main__":
    unittest.main()
