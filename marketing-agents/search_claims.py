"""Match campaign performance claims to the source that could measure them."""
import re

METRIC = (r"clicks?|impressions?|visits?|visitors?|sessions?|conversions?|leads?|bookings?|"
          r"traffic|visibility|presence|CTR|rankings?|reach|likes?|shares?|comments?|reactions?|engagements?|opens?")
NUMBER = r"no|none|zero|\d[\d,]*(?:\.\d+)?%?"
MODIFIER = (r"current|known|visible|organic|paid|social|search|website|site|referral|email|direct|unique|"
            r"recorded|measured|measurable|total|tracked|LinkedIn|Instagram|Facebook|Mastodon")
CLAIM = re.compile(
    rf"\b(?P<n1>{NUMBER})[\s-]+(?:(?:{MODIFIER})[\s-]+){{0,5}}(?P<m1>{METRIC})\b"
    rf"|\b(?P<m2>{METRIC})\s*(?:(?:is|was|were|are|of|at|equals?|totaled|:|=)\s*)+(?P<n2>{NUMBER})\b", re.I)
NETWORKS = ("linkedin", "instagram", "facebook", "mastodon")
METRIC_KEYS = {"click":("clicks","clickCount"),"impression":("impressions","impressionCount"),
               "like":("likes","likeCount"),"share":("shares","shareCount"),"comment":("comments","commentCount"),
               "reaction":("reactions",),"reach":("reach",),"ctr":("ctr",)}
OBSERVED = re.compile(r"\b(?:currently|recorded|received|reported|had|confirmed|shows?|baseline (?:is|was|of)|data (?:shows?|indicates?))\b",re.I)
FUTURE = re.compile(r"\b(?:goal|target|aim|if|threshold|hypothesis|at least|propose|success criterion)\b",re.I)


def annotate(audit):
    report = audit.get("search_console", {})
    measured = report.get("status") == "available" and bool(report.get("rows"))
    return {**audit, "search_console": {**report, "metric_basis": "returned rows" if measured else "unknown"}}


def channel_basis(brief):
    report = brief.get("website_audit", {}).get("search_console", {})
    posts = brief.get("measured_prior_posts", [])
    return {"search_console": "query/page rows" if report.get("status") == "available" and report.get("rows") else "unknown",
            "social_posts": sorted({p["network"] for p in posts if p.get("metrics")}) or "unknown",
            "site_visits_by_channel": "unknown", "email_performance": "unknown", "qualified_conversions": "unknown"}


def supported(brief, sentence, match):
    metric = (match["m1"] or match["m2"]).lower().rstrip("s")
    value = (match["n1"] or match["n2"]).lower()
    number = 0 if value in ("no","none","zero") else float(value.rstrip("%").replace(",",""))
    keys = METRIC_KEYS.get(metric, ())
    context = sentence.lower()
    networks = [n for n in NETWORKS if re.search(r"\b"+n+r"\b",context)]
    reports = brief.get('marketing_reports', {})
    if not networks and not re.search(r"\b(email|social|paid|referral|utm|direct)\b",context):
        for source, pattern, mapping in (
            ('bing',r'\bbing\b',{'click':'Clicks','impression':'Impressions'}),
            ('ga4',r'\b(?:ga4|google analytics)\b',{'session':'sessions'}),
        ):
            if re.search(pattern,context):
                key=mapping.get(metric)
                return bool(key and reports.get(source,{}).get('metrics',{}).get(key)==number)
    if re.search(r"\b(utm|referral|paid|email|newsletter|sitewide|site-wide)\b",context) or len(networks)>1:
        sources = []
    elif networks:
        sources = [p.get("metrics", {}) for p in brief.get("measured_prior_posts", []) if p["network"] in networks]
    elif re.search(r"\b(social|email|paid|referral|utm|direct|newsletter)\b",context):
        sources = []
    else:
        google = brief.get("website_audit", {}).get("search_console", {})
        sources = google.get("rows", []) if google.get("status") == "available" else []
    if metric == "ctr" and value.endswith("%"):
        number /= 100
    return any(row.get(key) == number for row in sources for key in keys)


def unsupported(text, brief=None):
    brief = brief or {}
    for sentence in re.split(r"(?<=[.!?;])\s+|\n+", text):
        sentence = sentence.replace("**","").replace("\u2011","-")
        for match in CLAIM.finditer(sentence):
            if re.match(r"\s+(?:data|rows|metrics|figures|counts|measurements)\b",sentence[match.end():],re.I):
                continue
            prefix = sentence[:match.start()]
            # Qualifiers only exempt the assertion they introduce.
            clause = re.split(r"[,;]|\b(?:but|however|although)\b",prefix,flags=re.I)[-1]
            if re.search(r"\b(?:cannot|can't|never|do not|does not|doesn't|not evidence of)\b[^,;]{0,70}$",clause,re.I):
                continue
            if FUTURE.search(sentence) and not OBSERVED.search(clause):
                continue
            suffix = sentence[match.end():]
            if re.match(r"\s+(?:target|goal|threshold|decision rule)\b",suffix,re.I):
                continue
            if not supported(brief,sentence,match):
                yield match.group().strip()


def enforce_review(brief, history, review):
    findings = []
    for msg in history:
        text = "\n".join([msg["body"]] + [task["instruction"] for task in msg.get("assignments",[])])
        claims = list(dict.fromkeys(unsupported(text, brief)))
        if claims:
            findings.append(msg["role"] + " asserted " + ", ".join(repr(c) for c in claims[:4]))
    # A HOLD may quote the very claim it rejects. Prefer the original offending
    # handoff when available; independently check the reviewer before release.
    if not findings and not review.startswith("HOLD\n"):
        claims = list(dict.fromkeys(unsupported(review, brief)))
        if claims:
            findings.append("Analyst asserted " + ", ".join(repr(c) for c in claims[:4]))
    if findings:
        return ("HOLD\nUnsupported channel-performance claim. " + "; ".join(findings) +
                ". No matching measurement supports the stated channel, metric and value. Treat the baseline as unknown. Remove these assertions before publication. "
                "Keep proposed targets and crawl observations separate from measured search performance.")
    return review
