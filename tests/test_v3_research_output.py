import copy
import json
import sys
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))

from serenity_scorecard import score, to_markdown
from validate_research_output import validate_component, validate_output


FIXTURE_PATH = SOURCE_ROOT / "evals" / "fixtures" / "research-output.synthetic.json"


class SurohaSerenityV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_synthetic_research_output_is_valid(self):
        self.assertEqual(validate_output(self.fixture, SOURCE_ROOT / "schemas"), [])

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
        self.assertEqual(priority, "medium")
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
