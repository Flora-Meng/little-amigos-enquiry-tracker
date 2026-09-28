# Database migrations

The MVP database targets PostgreSQL. Apply migrations in numeric order.

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f db/migrations/001_initial_schema.up.sql
```

For a database created with an earlier version of the initial migration, apply
the optional closed-reason change:

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f db/migrations/002_optional_closed_reason.up.sql
```

To roll back this migration in a development database:

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f db/migrations/002_optional_closed_reason.down.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f db/migrations/001_initial_schema.down.sql
```

The initial migration creates the two locations and the core `users`,
`enquiries`, `notes`, and `zumo_import_decisions` tables. It deliberately does
not create user accounts or credentials; that belongs to implementation step 2.
