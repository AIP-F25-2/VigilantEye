-- Database initialization script for VigilantEye
-- This script runs when the MySQL container starts for the first time

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS vigilanteye CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE vigilanteye;

-- Set default privileges for the vigilanteye user
-- Note: MySQL doesn't have the same privilege system as PostgreSQL
-- The user privileges are set during container initialization

-- Log initialization
SELECT 'VigilantEye database initialized successfully' as message;
