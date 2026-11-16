# Social publishing in VOS

Register the exact OAuth redirect URL https://viralmarketstrategy.com/vos/dashboard on both provider apps. For another installation, set VOS_PUBLIC_URL to the public VOS mount and register its /dashboard URL. Use a LinkedIn app with Community Management access and a Meta app with Facebook Login and the required approved permissions for companies outside your app roles.

On the VPS, set LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, META_CLIENT_ID and META_CLIENT_SECRET in /etc/vos/social.env (root-owned, mode 600). From the deployment folder run docker compose up -d --no-deps api. Keep the JWT signing secret stable as it also protects saved provider credentials. The Compose override loads the social settings separately from AI provider keys.

In the dashboard, a company administrator opens Publishing channels, connects each network, selects a company destination and enables publishing. LinkedIn requires a company Page administrator. Instagram requires a professional account linked to a Facebook Page in this flow. Provider revocation or expiry can require reconnection. Facebook and Instagram are separate connections.

The scheduler submits approved content once per campaign and channel, and generates a square JPEG from the approved copy for Instagram. Check the provider before retrying an ambiguous delivery. For delivered posts the scheduler requests platform metrics after 15 minutes and every six hours for up to 30 days. Recent post copy and measured results are included in subsequent scheduled agent briefs. Missing data remains unknown.

LinkedIn permissions: rw_organization_admin, w_organization_social, r_organization_social. Facebook: pages_show_list, pages_manage_posts, pages_read_engagement. Instagram: pages_show_list, pages_read_engagement, instagram_basic, instagram_content_publish, instagram_manage_insights.
