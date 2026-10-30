# example web-app (frontend)

A deliberately small TypeScript project, connected to the **same** `../hub` with the
`frontend` role.

Pull the same task here and in `../dev-backend` and compare `wizrelay route`: the package
lowers the signals for the frontend role, and this repository's profile adds no modifiers,
so the same task routes to `T1-routine` here and `T3-critical` there. That is design
invariant I3 — one hub, one package, two roles, two scopes — and the reason routing is
computed per role rather than per task.
