# Issue #142: checkout service needs its own database

**Reporter:** priya.eng
**Labels:** infra, checkout-service, priority-medium

## Description

The `checkout` service currently shares the `orders` database with the
`fulfillment` service. Under peak load this causes lock contention on the
`orders.line_items` table and intermittent 500s during checkout.

## Ask

Provision a dedicated database for `checkout` and update
`src/checkout.js` to point at the new connection string once it's ready.
No schema migration is required yet; this ticket only covers triage and a
draft patch outlining the change.

## Acceptance Criteria

- [ ] Patch drafted against `src/checkout.js` noting the new DB dependency
- [ ] No changes to `fulfillment` service required
- [ ] Issue triaged with a priority and owning team
