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
        missing="READY\nMetrics such as impressions, clicks and CTR are unknown."
        self.assertEqual(enforce_review(brief,[],missing),missing)
        held=enforce_review(brief,[{"role":"CMO","body":"This indicates no measurable organic traffic."}],"HOLD\nUnsupported claim of zero organic impressions.")
        self.assertIn("CMO asserted",held)
        self.assertNotIn("Analyst asserted",held)
        measured=annotate({"search_console":{"status":"available","rows":[{"clicks":0,"impressions":12}]}})
        self.assertEqual(measured["search_console"]["metric_basis"],"returned rows")
        self.assertEqual(enforce_review({"website_audit":measured},[],"READY\nReported 0 clicks."),"READY\nReported 0 clicks.")

    def test_missing_channel_metrics_even_when_other_sources_report_zero(self):
        brief={"website_audit":annotate({"search_console":{"status":"available","rows":[{"clicks":0}]}}),
               "measured_prior_posts":[{"network":"linkedin","metrics":{"clickCount":0}}]}
        for claim in ("Baseline is zero known organic social visits.", "Email opens were zero.",
                      "Recorded 0 paid conversions.", "Reported 0 Instagram clicks.",
                      "We recorded 4 LinkedIn sessions."):
            result=enforce_review(brief,[{"role":"CMO","body":claim}],"READY\nReviewed.")
            self.assertIn("CMO asserted",result,claim)
        for sentence in ("The LinkedIn post recorded 0 clicks.", "Search Console reported 0 clicks.",
                         "Our goal is 25 social visits.", "Social visits are unknown."):
            self.assertEqual(enforce_review(brief,[{"role":"CMO","body":sentence}],"READY"),"READY",sentence)
        self.assertIn("Analyst asserted",enforce_review({},[],"READY\nBaseline is zero known organic social visits."))
