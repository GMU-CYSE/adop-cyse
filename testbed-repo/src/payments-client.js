// Synthetic stub client for the ADOP testbed. No real network calls.
export const paymentsClient = {
  async createIntent({ amount, currency }) {
    return { id: `pi_fake_${Date.now()}`, amount, currency, status: "requires_confirmation" };
  },
};
