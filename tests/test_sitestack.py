"""Every site is built with config.SITE_STACK: the prompts say so, older plans are made to agree when read, and the
download states the rule."""
import copy
import re
import unittest
from datetime import date
from unittest import mock

from leadgen import config
from leadgen.enrichment import llm
from server import buildplan, enrich_job, sitestack

LEGACY = {
    "development_direction": {
        "summary": "A fast site.",
        "tech_stack": [
            {"layer": "Framework", "choice": "Astro static site, or plain HTML", "why": "no heavy framework"},
            {"layer": "Menu data", "choice": "menu.json fed by a Google Sheet", "why": "owner edits prices"},
            {"layer": "Styling", "choice": "Plain CSS with design tokens"},
            {"layer": "Hosting", "choice": "Vercel free tier"},
        ],
    },
}
STACK = config.SITE_STACK_TEXT


def stack(profile):
    return [(r["layer"], r["choice"]) for r in profile["development_direction"]["tech_stack"]]


class Apply(unittest.TestCase):
    def test_the_stack_is_next_and_tailwind(self):
        self.assertEqual(STACK, "Next.js and Tailwind CSS")

    def test_fixed_stack_comes_first_and_framework_and_styling_rows_are_replaced(self):
        self.assertEqual(stack(sitestack.apply(LEGACY)),
                         [("Framework", "Next.js"), ("Styling", "Tailwind CSS"), ("Menu data", "menu.json fed by a Google Sheet"), ("Hosting", "Vercel free tier")])

    def test_other_names_for_the_same_layers(self):
        prof = {"development_direction": {"tech_stack": [{"layer": "Front-end", "choice": "Vue"}, {"layer": "Front end framework", "choice": "Svelte"},
                                                         {"layer": "CSS", "choice": "Bootstrap"}, {"layer": "Stylesheets", "choice": "Sass"},
                                                         {"layer": "Analytics", "choice": "Plausible"}]}}
        self.assertEqual(stack(sitestack.apply(prof)), [("Framework", "Next.js"), ("Styling", "Tailwind CSS"), ("Analytics", "Plausible")])

    def test_does_not_mutate_and_is_idempotent(self):
        before = copy.deepcopy(LEGACY)
        once = sitestack.apply(LEGACY)
        self.assertEqual(LEGACY, before)
        self.assertEqual(sitestack.apply(once), once)

    def test_fixed_rows_say_why(self):
        rows = sitestack.apply(LEGACY)["development_direction"]["tech_stack"]
        self.assertEqual(rows[0]["why"], "Fixed: every site is built with it.")

    def test_plan_without_a_stack_gets_the_fixed_one(self):
        self.assertEqual(stack(sitestack.apply({"development_direction": {"summary": "x"}})), [("Framework", "Next.js"), ("Styling", "Tailwind CSS")])
        self.assertEqual(stack(sitestack.apply({"development_direction": {"summary": "x", "tech_stack": "junk"}})), [("Framework", "Next.js"), ("Styling", "Tailwind CSS")])

    def test_rows_it_cannot_read_are_kept(self):
        prof = {"development_direction": {"tech_stack": [None, "x", {"layer": ["Framework"], "choice": "Astro"}, {"choice": "no layer"}]}}
        self.assertEqual(len(sitestack.apply(prof)["development_direction"]["tech_stack"]), 2 + 4)

    def test_no_plan_means_nothing_to_change(self):
        for prof in (None, "x", [], {}, {"pitch_hooks": ["x"]}, {"development_direction": {}}, {"development_direction": None}):
            self.assertIs(sitestack.apply(prof), prof)


class Brief(unittest.TestCase):
    def md(self, profile):
        return buildplan.render({"key": "osm-node-1", "place": {"name": "La Parrilla"}, "profile": profile}, today=date(2026, 10, 2))

    def test_brief_of_an_older_plan_names_next_and_tailwind_and_no_astro(self):
        md = self.md(sitestack.apply(LEGACY))
        self.assertIn("- **Framework:** Next.js; why: Fixed: every site is built with it.", md)
        self.assertIn("- **Styling:** Tailwind CSS", md)
        self.assertIn("- **Menu data:** menu.json fed by a Google Sheet; why: owner edits prices", md)
        self.assertNotIn("Astro", md)
        self.assertNotIn("Plain CSS", md)

    def test_brief_states_the_rule_up_front(self):
        md = self.md(LEGACY)
        rule = f"Every page is built with {STACK}. That is fixed"
        self.assertIn(rule, md)
        self.assertLess(md.index(rule), md.index("## The restaurant"))


class Prompts(unittest.TestCase):
    def test_analysis_prompt_states_the_stack_and_leaves_no_placeholder(self):
        prompt = enrich_job.build_prompt("La Parrilla", "la-parrilla-1")
        self.assertIn(f"every site is built with {STACK}", prompt)
        self.assertIn("Restaurant: La Parrilla", prompt)
        self.assertEqual(re.findall(r"\{[a-z_]+\}", prompt), [])

    def test_api_synthesis_prompt_states_the_stack(self):
        with mock.patch.object(llm, "call", return_value={}) as call:
            llm.synthesize({"name": "La Parrilla"})
        text = call.call_args.args[2][0]["text"]
        self.assertIn(f"every site is built with {STACK}", text)
        self.assertIn("do not propose another framework", text)

    def test_schema_tells_the_model_the_stack_is_not_open(self):
        desc = llm.DEV_SCHEMA["properties"]["tech_stack"]["description"]
        self.assertIn(STACK, desc)
        self.assertIn("never an alternative", desc)


if __name__ == "__main__":
    unittest.main()
