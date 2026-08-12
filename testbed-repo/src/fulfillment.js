// Synthetic module for the ADOP testbed. Unrelated to checkout; present so
// the repository has more than one service, matching a realistic monorepo
// slice.

const DB_CONNECTION = process.env.FULFILLMENT_DB_URL ?? "postgres://orders-db/orders";

export function scheduleShipment(orderId) {
  return { orderId, status: "scheduled", carrier: "synthetic-carrier" };
}
