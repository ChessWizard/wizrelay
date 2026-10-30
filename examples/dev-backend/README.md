# example api-service (backend)

A deliberately small Python project, connected to `../hub` with the `backend` role. It has
just enough structure for the scope globs to mean something: `app/quota/` is in scope,
`app/billing/` is explicitly denied, and `app/api/` is a critical path.

Nothing here is meant to run. It exists so `wizrelay pull`, `route` and `audit` have a
real repository to work on.
