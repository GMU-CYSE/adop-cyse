// Synthetic module for the ADOP testbed. Computes a cart total and creates
// a payment intent against the (fake) payments gateway client.

import { paymentsClient } from "./payments-client.js";

const DB_CONNECTION = process.env.CHECKOUT_DB_URL ?? "postgres://orders-db/orders";

export function computeTotal(cart) {
  const subtotal = cart.items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const tax = subtotal * cart.taxRate;
  return Math.round((subtotal + tax) * 100) / 100;
}

export async function createPaymentIntent(cart) {
  const amount = computeTotal(cart);
  return paymentsClient.createIntent({ amount, currency: cart.currency ?? "USD" });
}

// TODO(issue #142): checkout currently shares DB_CONNECTION with the
// fulfillment service. Split into its own database once provisioned.
