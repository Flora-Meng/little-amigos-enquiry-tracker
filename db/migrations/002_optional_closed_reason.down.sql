ALTER TABLE enquiries
  ADD CONSTRAINT enquiries_closed_requires_reason CHECK (
    status <> 'closed' OR closed_reason IS NOT NULL
  );
