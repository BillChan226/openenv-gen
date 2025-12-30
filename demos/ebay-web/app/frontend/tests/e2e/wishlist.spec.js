import { test, expect } from '@playwright/test';
import { attachConsoleAndNetworkGuards, gotoAndWait, safeClick } from './_helpers.js';

test('wishlist flow: add from home and view wishlist (or login redirect)', async ({ page }) => {
  const guards = attachConsoleAndNetworkGuards(page);

  await gotoAndWait(page, '/');

  const addToWishlist = page.locator('[data-testid^="product-card-wishlist-"]').first();
  if (await addToWishlist.count()) {
    await safeClick(addToWishlist);
  }

  await safeClick(page.getByTestId('nav-my-wishlist'));

  // Some builds protect wishlist behind login.
  await expect(page).toHaveURL(/\/(account\/wishlist|login\?next=%2Faccount%2Fwishlist)/);

  if ((page.url() || '').includes('/login')) {
    await guards.assertNoErrors();
    test.skip(true, 'Wishlist is protected and auth backend may not be available; skipping');
  }

  await expect(page.getByTestId('wishlist-page')).toBeVisible();
  await guards.assertNoErrors();
});
