db.getSiblingDB("vos").createUser({
  user: "vos",
  pwd: process.env.VOS_DB_PASSWORD,
  roles: [{role: "readWrite", db: "vos"}]
});
