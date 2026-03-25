-- Create read-only PostgreSQL user for Claude-generated queries.
-- Run once against prod RDS (not an Alembic migration -- DB-level permission, not schema change).
--
-- Usage:
--   psql $DATABASE_URL -f scripts/create_dg_reader.sql
--
-- Replace 'CHANGE_ME' with the actual password before running.
-- Store the resulting connection string as DG_READER_URL in .env and Secrets Manager.

CREATE USER dg_reader WITH PASSWORD 'CHANGE_ME';
GRANT CONNECT ON DATABASE pdga_data TO dg_reader;
GRANT USAGE ON SCHEMA public TO dg_reader;
GRANT SELECT ON tournament, course, player, round, hole TO dg_reader;
GRANT SELECT ON vw_tournament_summary, vw_player_season, vw_classifications_per_season TO dg_reader;
