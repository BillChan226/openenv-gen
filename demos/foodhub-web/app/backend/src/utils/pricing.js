export const roundHalfUpDiv = (numerator, denominator) => Math.floor((numerator + denominator / 2) / denominator);

export const computeServiceFeeCents = (subtotalCents) => {
  // spec: floor((subtotal_cents * 5 + 50) / 100)
  return Math.floor((subtotalCents * 5 + 50) / 100);
};

export const computeCartPricing = ({ subtotalCents, deliveryFeeCents, discountCents }) => {
  const serviceFeeCents = computeServiceFeeCents(subtotalCents);
  const totalCents = subtotalCents + deliveryFeeCents + serviceFeeCents - discountCents;
  return { subtotalCents, deliveryFeeCents, serviceFeeCents, discountCents, totalCents };
};
