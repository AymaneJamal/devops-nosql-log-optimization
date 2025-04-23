db = db.getSiblingDB('admin');
if (!db.getUser("admin")) {
    db.createUser({
        user: "admin",
        pwd: "password",
        roles: [{ role: "root", db: "admin" }]
    });
}
db = db.getSiblingDB('logging');
if (!db.getCollectionNames().includes('logs')) {
    db.createCollection('logs');
}
db.logs.createIndex({ "service_type": 1 });
db.logs.createIndex({ "container_name": 1 });
db.logs.createIndex({ "timestamp": 1 });

db.createUser({
    user: 'logstash',
    pwd: 'logstash_password',
    roles: [
        { role: 'readWrite', db: 'logging' }
    ]
});