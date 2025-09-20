-- Initialize the database
CREATE DATABASE IF NOT EXISTS vigilanteye_db;
USE vigilanteye_db;

-- Create user if not exists (this is handled by environment variables in docker-compose)
-- But we can add any additional initialization here

-- Set timezone
SET time_zone = '+00:00';

-- Create any additional indexes or configurations
-- The tables will be created by SQLAlchemy when the FastAPI app starts
