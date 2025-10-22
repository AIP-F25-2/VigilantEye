-- Database initialization script for VigilantEye
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create additional schemas if needed
-- CREATE SCHEMA IF NOT EXISTS ai_analysis;
-- CREATE SCHEMA IF NOT EXISTS surveillance;

-- Set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vigilanteye;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO vigilanteye;

-- Create indexes for better performance (will be created by SQLAlchemy, but can add custom ones here)
-- These will be created after tables are created by the application

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'VigilantEye database initialized successfully';
END $$;
