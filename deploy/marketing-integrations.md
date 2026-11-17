# Marketing measurement connections

The dashboard's **Analytics and social profiles** section reads account metrics. Publishing permissions are managed separately under **Publishing channels**. Workspace admins authorize each source. VOS verifies access before saving the encrypted credential, refreshes reports daily, and supplies successful reports with their account and reporting period to scheduled campaign agents.

Configure OAuth apps with the public dashboard callback (by default https://viralmarketstrategy.com/vos/dashboard). Store server credentials in the existing root-owned provider environment file and recreate the API service after updating it.

| Source | Operator setup | Workspace connection |
| --- | --- | --- |
| Google Analytics 4 | Enable the Google Analytics Data API and approve the analytics.readonly scope for the existing Google OAuth client (GSC_CLIENT_ID and GSC_CLIENT_SECRET). | Enter the numeric GA4 property ID and authorize an account with access. |
| YouTube | Enable YouTube Data API v3 and approve the youtube.readonly scope on the same client. | Authorize the Google identity associated with the company channel. |
| X | Configure X_CLIENT_ID and X_CLIENT_SECRET for a confidential OAuth 2.0 client with API access, users.read, tweet.read and offline.access. | Authorize the company X profile. |
| TikTok | Configure TIKTOK_CLIENT_ID (client key) and TIKTOK_CLIENT_SECRET. Enable Login Kit and user.info.basic and user.info.stats. | Authorize the company account. |
| Pinterest | Configure PINTEREST_CLIENT_ID and PINTEREST_CLIENT_SECRET and obtain approved user_accounts:read access. | Authorize the business account. |
| Threads | Provide a Threads user token with threads_basic and threads_manage_insights access. | Enter the token in the masked field. Reconnect when access expires. |
| Bing Webmaster Tools | Use an account with a verified site and Webmaster API access. | Enter the exact verified site URL and Webmaster API key. |
| Microsoft Clarity | A project admin generates a Data Export API token in Clarity project settings. | Enter the token in the masked field. |

Ready to connect indicates that VOS can start the connection flow. Provider-side API enablement and consent are verified when a report is fetched. Disconnect removes the locally stored account credential and report. To revoke a provider-side grant, use the provider's authorized apps settings.
