BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE user_role AS ENUM ('admin', 'staff');
CREATE TYPE location_code AS ENUM ('southland', 'canberra');
CREATE TYPE enquiry_source AS ENUM ('online', 'store');
CREATE TYPE enquiry_status AS ENUM (
  'new',
  'contacted',
  'waiting_for_reply',
  'follow_up',
  'booked',
  'closed'
);
CREATE TYPE closed_reason AS ENUM (
  'unable_to_contact',
  'customer_no_longer_interested',
  'price',
  'other'
);
CREATE TYPE zumo_decision AS ENUM ('imported', 'ignored');

CREATE TABLE locations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code location_code NOT NULL UNIQUE,
  name text NOT NULL UNIQUE,
  timezone text NOT NULL DEFAULT 'Australia/Sydney',
  created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO locations (code, name)
VALUES
  ('southland', 'Little Amigos Southland'),
  ('canberra', 'Little Amigos Canberra');

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL,
  password_hash text,
  display_name text NOT NULL,
  role user_role NOT NULL,
  location_id uuid REFERENCES locations(id),
  is_active boolean NOT NULL DEFAULT true,
  password_reset_required boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT users_email_normalised CHECK (email = lower(btrim(email))),
  CONSTRAINT users_role_location_check CHECK (
    (role = 'admin' AND location_id IS NULL)
    OR (role = 'staff' AND location_id IS NOT NULL)
  ),
  CONSTRAINT users_password_hash_not_blank CHECK (
    password_hash IS NULL OR length(btrim(password_hash)) > 0
  )
);

CREATE UNIQUE INDEX users_email_unique_ci ON users (lower(email));

CREATE TABLE enquiries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  postcode text,
  party_date date,
  party_date_unknown boolean NOT NULL DEFAULT false,
  email text,
  phone text,
  normalised_email text GENERATED ALWAYS AS (lower(btrim(email))) STORED,
  normalised_phone text GENERATED ALWAYS AS (regexp_replace(coalesce(phone, ''), '[^0-9+]', '', 'g')) STORED,
  location_id uuid NOT NULL REFERENCES locations(id),
  source enquiry_source NOT NULL,
  status enquiry_status NOT NULL DEFAULT 'new',
  booking_amount_aud numeric(12,2),
  closed_reason closed_reason,
  closed_reason_details text,
  follow_up_due_date date,
  submitted_by_user_id uuid NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  archived boolean NOT NULL DEFAULT false,
  archived_at timestamptz,
  zumo_conversation_id text,
  original_zumo_message text,
  CONSTRAINT enquiries_name_not_blank CHECK (length(btrim(name)) > 0),
  CONSTRAINT enquiries_contact_required CHECK (
    nullif(btrim(coalesce(email, '')), '') IS NOT NULL
    OR nullif(btrim(coalesce(phone, '')), '') IS NOT NULL
  ),
  CONSTRAINT enquiries_party_date_state CHECK (
    NOT (party_date IS NOT NULL AND party_date_unknown)
  ),
  CONSTRAINT enquiries_booking_amount_nonnegative CHECK (
    booking_amount_aud IS NULL OR booking_amount_aud >= 0
  ),
  CONSTRAINT enquiries_booked_requires_amount CHECK (
    status <> 'booked' OR booking_amount_aud IS NOT NULL
  ),
  CONSTRAINT enquiries_closed_requires_reason CHECK (
    status <> 'closed' OR closed_reason IS NOT NULL
  ),
  CONSTRAINT enquiries_other_reason_requires_details CHECK (
    closed_reason <> 'other'
    OR nullif(btrim(coalesce(closed_reason_details, '')), '') IS NOT NULL
  ),
  CONSTRAINT enquiries_archive_timestamp_check CHECK (
    (archived AND archived_at IS NOT NULL)
    OR (NOT archived AND archived_at IS NULL)
  ),
  CONSTRAINT enquiries_zumo_fields_online_only CHECK (
    source = 'online'
    OR (zumo_conversation_id IS NULL AND original_zumo_message IS NULL)
  )
);

CREATE UNIQUE INDEX enquiries_zumo_conversation_unique
  ON enquiries (zumo_conversation_id)
  WHERE zumo_conversation_id IS NOT NULL;
CREATE INDEX enquiries_location_idx ON enquiries (location_id);
CREATE INDEX enquiries_source_idx ON enquiries (source);
CREATE INDEX enquiries_status_idx ON enquiries (status);
CREATE INDEX enquiries_follow_up_due_date_idx ON enquiries (follow_up_due_date);
CREATE INDEX enquiries_created_at_idx ON enquiries (created_at DESC);
CREATE INDEX enquiries_updated_at_idx ON enquiries (updated_at DESC);
CREATE INDEX enquiries_archived_idx ON enquiries (archived);
CREATE INDEX enquiries_normalised_phone_idx
  ON enquiries (normalised_phone)
  WHERE normalised_phone <> '';
CREATE INDEX enquiries_normalised_email_idx
  ON enquiries (normalised_email)
  WHERE normalised_email IS NOT NULL AND normalised_email <> '';
CREATE INDEX enquiries_party_date_idx ON enquiries (party_date);

CREATE TABLE notes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  enquiry_id uuid NOT NULL REFERENCES enquiries(id),
  body text NOT NULL,
  author_user_id uuid NOT NULL REFERENCES users(id),
  author_display_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT notes_body_not_blank CHECK (length(btrim(body)) > 0),
  CONSTRAINT notes_author_name_not_blank CHECK (length(btrim(author_display_name)) > 0)
);

CREATE INDEX notes_enquiry_created_at_idx ON notes (enquiry_id, created_at);
CREATE INDEX notes_author_user_idx ON notes (author_user_id);

CREATE TABLE zumo_import_decisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  zumo_conversation_id text NOT NULL UNIQUE,
  zumo_conversation_url text NOT NULL,
  decision zumo_decision NOT NULL,
  linked_enquiry_id uuid REFERENCES enquiries(id),
  detected_postcode text,
  detected_location_id uuid REFERENCES locations(id),
  reviewed_by_user_id uuid NOT NULL REFERENCES users(id),
  reviewed_at timestamptz NOT NULL DEFAULT now(),
  original_message_snapshot text,
  CONSTRAINT zumo_decisions_conversation_not_blank CHECK (
    length(btrim(zumo_conversation_id)) > 0
  ),
  CONSTRAINT zumo_decisions_link_check CHECK (
    (decision = 'imported' AND linked_enquiry_id IS NOT NULL)
    OR (decision = 'ignored' AND linked_enquiry_id IS NULL)
  )
);

CREATE INDEX zumo_decisions_decision_idx ON zumo_import_decisions (decision);
CREATE INDEX zumo_decisions_reviewed_at_idx ON zumo_import_decisions (reviewed_at DESC);
CREATE INDEX zumo_decisions_detected_location_idx ON zumo_import_decisions (detected_location_id);

CREATE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER enquiries_set_updated_at
BEFORE UPDATE ON enquiries
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON COLUMN users.password_hash IS
  'Nullable during initial provisioning; authentication setup must store only a secure hash.';
COMMENT ON TABLE notes IS
  'Append-only at the application/authorisation layer; no update or delete UI is permitted.';

COMMIT;
