"""Separate Google report availability from what its returned rows establish."""
import re

METRIC = r"(?:clicks?|impressions?|organic (?:search )?(?:traffic|visibility|presence)|search (?:visibility|traffic|presence)|CTR|rankings?)"
NUMBER = r"(?:no|none|zero|\d[\d,]*(?:\.\d+)?%?)"
CLAIM = re.compile(
    rf"\b{NUMBER}[\s-]+(?:(?:current|visible|organic|search|recorded|measured|measurable|total)\s+){{0,3}}{METRIC}\b"
    rf"|\b{METRIC}\s*(?:(?:is|was|were|are|of|at|equals?|totaled|:|=)\s*)+{NUMBER}\b"
    rf"|\b(?:no|zero|absent)\s+(?:current\s+)?organic search presence\b", re.I)
OBSERVED = re.compile(r"\b(?:currently|recorded|received|reported|had|confirmed|shows?|baseline (?:is|was|of)|data (?:shows?|indicates?))\b",re.I)
FUTURE = re.compile(r"\b(?:goal|target|aim|if|threshold|hypothesis|at least|propose|success criterion)\b",re.I)


def annotate(audit):
    report = audit.get("search_console", {})
    measured = report.get("status") == "available" and bool(report.get("rows"))
    return {**audit, "search_console": {**report, "metric_basis": "returned rows" if measured else "unknown"}}


def unsupported(text):
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
            numeric = re.search(r"\d[\d,]*(?:\.\d+)?",match.group())
            if numeric and float(numeric.group().replace(",","")) > 0 and not OBSERVED.search(sentence):
                continue
            yield match.group().strip()


def enforce_review(brief, history, review):
    report = brief.get("website_audit", {}).get("search_console", {})
    if report.get("metric_basis") != "unknown":
        return review
    findings = []
    for msg in history:
        claims = list(dict.fromkeys(unsupported(msg["body"])))
        if claims:
            findings.append(msg["role"] + " asserted " + ", ".join(repr(c) for c in claims[:4]))
    # A HOLD may quote the very claim it rejects. Prefer the original offending
    # handoff when available; independently check the reviewer before release.
    if not findings and not review.startswith("HOLD\n"):
        claims = list(dict.fromkeys(unsupported(review)))
        if claims:
            findings.append("Analyst asserted " + ", ".join(repr(c) for c in claims[:4]))
    if findings:
        return ("HOLD\nUnsupported search-performance claim. " + "; ".join(findings) +
                ". The report provides no measured baseline. Remove these assertions before publication. "
                "Keep proposed targets and crawl observations separate from measured search performance.")
    return review
