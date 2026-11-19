---
name: geo-measurement
description: Generative search measurement. A transparent baseline and reporting plan for AI citations, brand mentions, referrals and outcomes.
role: Analyst
collection: SEO
triggers: GEO measurement,AI citation tracking,generative search analytics,AI visibility reporting
---

# Generative search measurement

## Method

Agree on engines, markets, languages, query tasks, brand aliases, competitors, period, and sampling method before measuring. Preserve a fixed prompt panel for trend comparisons and label exploratory prompts separately. Capture dates and answer/citation evidence; generated responses vary, and samples are not a census of all user experiences.

Track distinct signals without collapsing them into an unsupported single score:

- **Citation rate:** sampled eligible answers citing at least one owned URL ÷ sampled eligible answers.
- **Owned citation share:** owned-domain citations ÷ all recorded citations in the sample.
- **Brand accuracy:** sampled answers that describe the company/product correctly ÷ sampled answers that mention it.
- **Referral outcomes:** sessions, engaged visits, leads, or revenue attributed to identifiable AI referrals, using the analytics platform's available source/referrer data.

Use platform reporting where available. Bing Webmaster Tools AI Performance reports citation activity and grounding-query samples for supported AI experiences; label its scope and public-preview status where relevant. Google Search Console reports Google AI-feature traffic within the Web search type rather than as a separate AI-only channel. OpenAI documents OAI-SearchBot for search discovery, and ChatGPT referrals may be measured in analytics when referral data is present. Check current product documentation before interpreting each report.

Segment by engine, query task, locale, page, and time window. Compare like with like. Pair visibility measures with qualified referral and conversion data, while explaining that cited visibility does not prove causation or ranking.

## Deliverable

Produce a measurement plan or report with:

- Definitions, sources, prompt sample, dates, locale, and known coverage gaps.
- Baseline and trend for each metric, with numerator and denominator.
- Cited URLs and grounding questions where platform reports expose them.
- Referral and conversion results, attribution limits, and comparison window.
- Actions, owners, and a scheduled repeat using the same sampling method.

## Review

Do not compare raw counts from different platforms as if they share coverage. Do not call a small prompt panel market share, ranking, or a guaranteed visibility score. Label unavailable data and changes to the measurement method.
## References

- [Bing Webmaster Tools: AI Performance](https://blogs.bing.com/webmaster/2026/2/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview/)
- [Google Search: AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)
- [OpenAI crawler documentation](https://developers.openai.com/api/docs/bots)
- [OpenAI publisher FAQ](https://help.openai.com/en/articles/12627856-publishers-and-developers-faq)