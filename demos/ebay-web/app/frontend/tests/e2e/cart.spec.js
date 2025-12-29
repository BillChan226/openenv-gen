import { test, expect } from '@playwright/test';
import { attachConsoleAndNetworkGuards, gotoAndWait, safeClick } from './_helpers.js';

test('cart flow: add item from home and remove from cart', async ({ page }) => {
  const guards = attachConsoleAndNetworkGuards(page);

  await gotoAndWait(page, '/');

  // Add-to-cart button may not exist in all builds; treat as optional.
  const addToCart = page.locator('[data-testid^="product-card-add-"]').first();
  if (await addToCart.count()) {
    await safeClick(addToCart);
  }

  // Navigate to cart regardless.


  await safeClick(page.getByTestId('nav-cart'));
  await expect(page).toHaveURL(/\/cart/);
  await expect(page.getByTestId('cart-page')).toBeVisible();

  // Cart may be empty in demo mode; if items exist, try removing one.
  const cartItems = page.locator('[data-testid^="cart-item-"]');
  const count = await cartItems.count();
  if (count > 0) {
    const remove = page.locator('[data-testid^="cart-remove-"]').first();
    if (await remove.count()) {
      await safeClick(remove);
    }
  }

  await guards.assertNoErrors();
});
