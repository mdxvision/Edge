-- PostgreSQL initialization script for Edge
-- This runs automatically when the container starts for the first time

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Create indexes for common queries (SQLAlchemy creates tables, this adds extra indexes)
-- These will be created after the app runs init_db()

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE edge_db TO edge;
