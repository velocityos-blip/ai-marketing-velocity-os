# First deployment

On a Docker host, point the DNS A record for vos-api.viralmarketstrategy.com to the host. Permit inbound HTTP and HTTPS. In a full checkout run:

```sh
VOS_API_HOST=vos-api.viralmarketstrategy.com sh deploy/bootstrap.sh
curl -fsS https://vos-api.viralmarketstrategy.com/api/health
```

The bootstrap creates server-local credentials once. MongoDB is private to the Compose network. Accounts and campaigns use persistent volumes. Back up the volumes and deploy/.env together. The default roles use local templates. Configure provider settings on the api service to enable paid inference.

On the existing Hostinger Node deployment, preserve the site's current environment and campaign data, set VOS_BACKEND_ORIGIN to the verified HTTPS backend origin and deploy the main website bundle containing public/vos/. The homepage displays its dashboard link when the origin is set. Verify company signup, dashboard refresh, one campaign run and the homepage link through /vos/ before announcing launch.
