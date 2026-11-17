import unittest
from search_claims import annotate,enforce_review


class SearchClaimsTests(unittest.TestCase):
    def test_empty_cached_and_disconnected_reports(self):
        for report in ({"status":"available","rows":[]},{"status":"not connected"}):
            brief={"website_audit":annotate({"search_console":report})}
            for role in ("CMO","Digital Marketing","Content","Analyst"):
                bad="The page currently records 0 impressions and 0 clicks."
                history=[] if role=="Analyst" else [{"role":role,"body":bad}]
                result=enforce_review(brief,history,"READY\n"+(bad if role=="Analyst" else "Reviewed."))
                self.assertTrue(result.startswith("HOLD\n"))
                self.assertIn(role+" asserted",result)

    def test_targets_unknowns_and_measured_zero(self):
        brief={"website_audit":annotate({"search_console":{"status":"available","rows":[]}})}
        good="READY\nSearch performance is unknown. Our target is 50 clicks."
        self.assertEqual(enforce_review(brief,[],good),good)
        self.assertTrue(enforce_review(brief,[{"role":"Digital Marketing","body":"Collect a **0-click baseline**."}],good).startswith("HOLD"))
        self.assertEqual(enforce_review(brief,[],"READY\nThe 25 clicks target is proposed."),"READY\nThe 25 clicks target is proposed.")
        measured=annotate({"search_console":{"status":"available","rows":[{"clicks":0,"impressions":12}]}})
        self.assertEqual(measured["search_console"]["metric_basis"],"returned rows")
        self.assertEqual(enforce_review({"website_audit":measured},[],"READY\nReported 0 clicks."),"READY\nReported 0 clicks.")
