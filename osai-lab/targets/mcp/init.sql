-- Postgres schema with juicy data for MCP SQLi attacks

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(255),
    role VARCHAR(20),
    api_key VARCHAR(100)
);

CREATE TABLE secrets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    value TEXT,
    classification VARCHAR(20)
);

CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    action VARCHAR(100),
    details TEXT
);

INSERT INTO users VALUES
    (1, 'admin', 'SuperSecret123!', 'admin', 'sk-admin-key-abc123'),
    (2, 'alice', 'Password1!', 'user', 'sk-alice-key-xyz789'),
    (3, 'bob', 'qwerty', 'user', 'sk-bob-key-def456'),
    (4, 'svc-account', 'service-pass-2026', 'service', 'sk-svc-key-svc999');

INSERT INTO secrets VALUES
    (1, 'OPENAI_API_KEY', 'sk-proj-FAKE-openai-key-for-lab', 'confidential'),
    (2, 'AWS_SECRET_KEY', 'AKIAIOSFODNN7EXAMPLE', 'confidential'),
    (3, 'DB_PASSWORD', 'prod-db-pass-2026', 'secret'),
    (4, 'STRIPE_SECRET', 'sk_live_FAKE-stripe-key-lab', 'confidential'),
    (5, 'JWT_SIGNING_KEY', 'super-secret-jwt-key-never-share', 'secret');
