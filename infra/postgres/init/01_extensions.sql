-- Enable required PostgreSQL extensions for MedServicePrice.
-- postgis: geo queries (distance sorting), pgvector: semantic search,
-- pg_trgm: trigram fuzzy matching, uuid-ossp: uuid generation.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
