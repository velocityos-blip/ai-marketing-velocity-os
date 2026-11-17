"""Extract reproducible observations from supplied SEO evidence."""
from collections import Counter
from html.parser import HTMLParser
from xml.etree import ElementTree


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.counts = Counter()
        self.canonicals = []
        self.robots = []

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        self.counts[tag] += 1
        if tag == "img" and "alt" not in fields:
            self.counts["img_without_alt_attribute"] += 1
        if tag == "link" and "canonical" in (fields.get("rel") or "").lower().split():
            self.canonicals.append(fields.get("href"))
        if tag == "meta" and (fields.get("name") or "").lower() == "robots":
            self.robots.append(fields.get("content"))


def observations(slug, evidence):
    if slug == "seo-sitemap" and evidence.lstrip().startswith("<"):
        if "<!DOCTYPE" in evidence.upper():
            return {"xml":"Document type declarations are unsupported."}
        try:
            root = ElementTree.fromstring(evidence)
        except ElementTree.ParseError:
            return {"xml":"Incomplete or invalid supplied XML."}
        kind = root.tag.split("}")[-1]
        if kind not in {"urlset","sitemapindex"}:
            return {"xml":"Unrecognized sitemap root."}
        child = "url" if kind == "urlset" else "sitemap"
        locations = [(node.text or "").strip() for node in root.findall(f"{{*}}{child}/{{*}}loc")]
        return {"root":kind,"location_count":len(locations),"duplicate_locations":
                [url for url,count in Counter(locations).items() if count > 1][:20]}
    if slug in {"seo-page","seo-images","seo-technical","seo-agent-readiness"} and "<" in evidence:
        parser = Markup()
        try:
            parser.feed(evidence)
            parser.close()
        except (ValueError, AssertionError):
            return {"markup":"Could not parse the supplied excerpt."}
        if parser.counts:
            return {"scope":"supplied markup only","title_tags":parser.counts["title"],
                    "h1_tags":parser.counts["h1"],"images":parser.counts["img"],
                    "images_missing_alt_attribute":parser.counts["img_without_alt_attribute"],
                    "canonical_targets":parser.canonicals[:20],"robots_directives":parser.robots[:20]}
    return {}
