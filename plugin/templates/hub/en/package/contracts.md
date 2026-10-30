# Contracts — {{TASK_ID}}

Required when the package covers more than one role. Implemented exactly as written; a
contract that needs to change is raised as a question, never adjusted on one side.

Give every contract an identifier. Acceptance criteria and role files refer to it as
`contracts.md#C-1`, so a field name or an error code is defined **once**, here.

## C-1 {{Contract name}}

- Producer: {{role}}
- Consumer: {{role}}

### Shape

```json
{{ "field": "type" }}
```

### Rules

- {{status codes, error shapes, idempotency, ordering}}

### Versioning

{{What happens to an existing client when this changes.}}
