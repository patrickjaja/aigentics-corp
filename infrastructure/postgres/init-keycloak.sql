-- Create Keycloak database
SELECT 'CREATE DATABASE keycloak'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak')\gexec

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE keycloak TO offer_agent;
