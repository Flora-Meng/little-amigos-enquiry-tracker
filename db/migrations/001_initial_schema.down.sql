BEGIN;

DROP TRIGGER IF EXISTS enquiries_set_updated_at ON enquiries;
DROP TRIGGER IF EXISTS users_set_updated_at ON users;
DROP FUNCTION IF EXISTS set_updated_at();
DROP TABLE IF EXISTS zumo_import_decisions;
DROP TABLE IF EXISTS notes;
DROP TABLE IF EXISTS enquiries;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS locations;
DROP TYPE IF EXISTS zumo_decision;
DROP TYPE IF EXISTS closed_reason;
DROP TYPE IF EXISTS enquiry_status;
DROP TYPE IF EXISTS enquiry_source;
DROP TYPE IF EXISTS location_code;
DROP TYPE IF EXISTS user_role;

COMMIT;
