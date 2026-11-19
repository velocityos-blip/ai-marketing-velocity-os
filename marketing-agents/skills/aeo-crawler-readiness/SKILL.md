---
name: aeo-crawler-readiness
description: AI answer discovery technical check. An evidence-based crawler and indexability issue list for selected pages and platforms.
role: Digital Marketing
collection: SEO
triggers: AEO technical audit,AI crawler audit,answer engine crawlability,AI search indexing
---

# AI answer discovery technical check

## Method

Use supplied URLs, robots.txt, response headers, rendered HTML, crawl exports, CDN or WAF rules, and platform documentation. For each target page, check response status, indexability and preview controls, canonical destination, internal discovery, important text in rendered output, and whether robots or infrastructure blocks the relevant documented crawler.

Check crawler identity and purpose against the platform's current first-party documentation. Do not treat every AI crawler as interchangeable. For example, OpenAI documents OAI-SearchBot for search discovery separately from GPTBot for model training; site owners can make separate choices. Google AI search uses its existing Search eligibility and Googlebot controls, with no additional AI-feature technical requirement. Confirm current policies before changing access.

Respect the site's access preferences. Do not recommend disabling authentication, bypassing a paywall, weakening a WAF, or allowing all bots. Do not claim that llms.txt or a special schema is required for inclusion. If evidence is missing, request the relevant file, headers, rendered page, or crawl log rather than guessing.

## Deliverable

Return a page-by-page issue register with:

- URL and platform/crawler in scope.
- Observed evidence (status, directive, response, header, rendered text, or supplied log).
- Impact and affected URL pattern, with sample coverage.
- Recommended fix, owner, and verification step.
- Site-owner access decision and any unresolved policy question.

## Review

Separate observed blocks from potential risks. Cite the exact evidence and the current first-party crawler documentation used. State that technical eligibility does not guarantee crawling, indexing, ranking, or citation.
## References

- [Google Search: AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)
- [OpenAI crawler documentation](https://developers.openai.com/api/docs/bots)