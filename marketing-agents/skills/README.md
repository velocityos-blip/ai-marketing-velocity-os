# Native VOS marketing skills

The original 53 VOS-authored playbooks cover the skill topics in [Corey Haines’s Marketing Skills catalog](https://github.com/coreyhaines31/marketingskills/tree/1f837447b20bb6f0e72d87b80ece1c221c362c7d/skills). Each directory contains its agent role, triggers, working method, deliverable and review criteria. The app loads these files locally.

Campaigns select one playbook per role by matching the company brief, with a default for each role. The AI Tools library can also run an individual playbook against the saved brief and store its result in campaign activity. These runs consume the existing workspace allowance. Playbooks guide analysis and content generation. External delivery uses the existing authorized publishing connections.

## SEO collection

VOS implements native workflows for all 35 distinct skill topics in [Claude SEO](https://github.com/AgriciDaniel/claude-seo/tree/468ed5b0d9e3249394783710e54abb02837e326b). The FLOW topic draws on [Daniel Agrici’s FLOW framework](https://github.com/AgriciDaniel/flow). Provider-specific playbooks analyze supplied reports. Add a crawl excerpt, page markup or redacted export when running a skill.

| Source topic | VOS playbook |
|---|---|
| seo | [seo-overview](seo-overview/SKILL.md) |
| seo-agentic | [seo-agent-readiness](seo-agent-readiness/SKILL.md) |
| seo-ahrefs | [seo-ahrefs](seo-ahrefs/SKILL.md) |
| seo-audit | [seo-audit](seo-audit/SKILL.md) |
| seo-backlinks | [seo-backlinks](seo-backlinks/SKILL.md) |
| seo-bing | [seo-bing](seo-bing/SKILL.md) |
| seo-cluster | [seo-cluster](seo-cluster/SKILL.md) |
| seo-competitor-pages | [competitors](competitors/SKILL.md) |
| seo-content | [seo-content-quality](seo-content-quality/SKILL.md) |
| seo-content-brief | [seo-content-brief](seo-content-brief/SKILL.md) |
| seo-dataforseo | [seo-dataforseo](seo-dataforseo/SKILL.md) |
| seo-drift | [seo-drift](seo-drift/SKILL.md) |
| seo-ecommerce | [seo-ecommerce](seo-ecommerce/SKILL.md) |
| seo-firecrawl | [seo-firecrawl](seo-firecrawl/SKILL.md) |
| seo-flow | [seo-flow](seo-flow/SKILL.md) |
| seo-geo | [ai-seo](ai-seo/SKILL.md) |
| seo-google | [seo-google](seo-google/SKILL.md) |
| seo-hreflang | [seo-hreflang](seo-hreflang/SKILL.md) |
| seo-image-gen | [seo-image-brief](seo-image-brief/SKILL.md) |
| seo-images | [seo-images](seo-images/SKILL.md) |
| seo-local | [seo-local](seo-local/SKILL.md) |
| seo-maps | [seo-maps](seo-maps/SKILL.md) |
| seo-matomo | [seo-matomo](seo-matomo/SKILL.md) |
| seo-page | [seo-page](seo-page/SKILL.md) |
| seo-plan | [seo-plan](seo-plan/SKILL.md) |
| seo-posthog | [seo-posthog](seo-posthog/SKILL.md) |
| seo-profound | [seo-profound](seo-profound/SKILL.md) |
| seo-programmatic | [programmatic-seo](programmatic-seo/SKILL.md) |
| seo-schema | [schema](schema/SKILL.md) |
| seo-seranking | [seo-seranking](seo-seranking/SKILL.md) |
| seo-shopify | [seo-shopify](seo-shopify/SKILL.md) |
| seo-sitemap | [seo-sitemap](seo-sitemap/SKILL.md) |
| seo-sxo | [seo-sxo](seo-sxo/SKILL.md) |
| seo-technical | [seo-technical](seo-technical/SKILL.md) |
| seo-unlighthouse | [seo-unlighthouse](seo-unlighthouse/SKILL.md) |

## AEO and GEO workflows

These five workflows add answer-engine optimization (AEO) and generative-engine optimization (GEO) to the SEO collection. AEO focuses on making useful answers clear and well-supported; GEO measures where AI-generated answers mention or cite the brand. They complement the existing [AI search visibility check](ai-seo/SKILL.md). No playbook guarantees a mention, citation, or ranking.

| Workflow | Playbook |
|---|---|
| Answer-engine content brief | [aeo-content-brief](aeo-content-brief/SKILL.md) |
| Answer-engine page optimization | [aeo-page-optimization](aeo-page-optimization/SKILL.md) |
| AI crawler and index readiness | [aeo-crawler-readiness](aeo-crawler-readiness/SKILL.md) |
| Generative visibility and citation audit | [geo-visibility-audit](geo-visibility-audit/SKILL.md) |
| Generative search measurement | [geo-measurement](geo-measurement/SKILL.md) |

These playbooks follow current platform guidance: keep foundational SEO and people-first content, verify bot access using each platform's first-party documentation, and measure citations with explicit scope and sample limits. Google documents no special schema or AI text-file requirement for its AI search features. See the source links inside the relevant playbooks.

## Additional growth workflows

These 20 native playbooks expanded the collection from 83 to 103 distinct skills. Five AEO/GEO playbooks bring the current total to 108. The growth workflows cover strategic work, demand and product growth, customer lifecycle, campaign production and marketing operations.

| Workflow | Playbook |
|---|---|
| Brand strategy | [brand-strategy](brand-strategy/SKILL.md) |
| Positioning | [positioning](positioning/SKILL.md) |
| Messaging framework | [messaging](messaging/SKILL.md) |
| Demand generation | [demand-generation](demand-generation/SKILL.md) |
| Product-led growth | [product-led-growth](product-led-growth/SKILL.md) |
| Lifecycle marketing | [lifecycle-marketing](lifecycle-marketing/SKILL.md) |
| Customer marketing | [customer-marketing](customer-marketing/SKILL.md) |
| Customer success marketing | [customer-success-marketing](customer-success-marketing/SKILL.md) |
| Win-loss analysis | [win-loss-analysis](win-loss-analysis/SKILL.md) |
| Campaign brief | [campaign-brief](campaign-brief/SKILL.md) |
| Landing page | [landing-page](landing-page/SKILL.md) |
| Content repurposing | [content-repurposing](content-repurposing/SKILL.md) |
| Newsletter marketing | [newsletter](newsletter/SKILL.md) |
| Customer case studies | [case-studies](case-studies/SKILL.md) |
| Webinar marketing | [webinar-marketing](webinar-marketing/SKILL.md) |
| Podcast marketing | [podcast-marketing](podcast-marketing/SKILL.md) |
| Affiliate marketing | [affiliate-marketing](affiliate-marketing/SKILL.md) |
| Marketing operations | [marketing-operations](marketing-operations/SKILL.md) |
| Marketing budgeting | [marketing-budgeting](marketing-budgeting/SKILL.md) |
| Go-to-market strategy | [go-to-market](go-to-market/SKILL.md) |
