import { test, expect } from '@playwright/test';
import { attachConsoleAndNetworkGuards, gotoAndWait, safeClick } from './_helpers.js';

test('navigate through primary routes and ensure pages render', async ({ page }) => {
  const guards = attachConsoleAndNetworkGuards(page);

  await gotoAndWait(page, '/');
  await expect(page.getByTestId('header-search-input')).toBeVisible();

  // Home via logo
  await safeClick(page.getByTestId('nav-home-logo'));
  await expect(page).toHaveURL(/\/$/);

  // Cart
  await safeClick(page.getByTestId('nav-cart'));
  await expect(page).toHaveURL(/\/cart/);
  await expect(page.getByTestId('cart-page')).toBeVisible();

  // Wishlist (may redirect to login)
  await safeClick(page.getByTestId('nav-my-wishlist'));
  await expect(page).toHaveURL(/\/(account\/wishlist|login\?next=%2Faccount%2Fwishlist)/);

  // If redirected to login, go back home and continue.
  if ((page.url() || '').includes('/login')) {
    await safeClick(page.getByTestId('nav-home-logo'));
    await expect(page).toHaveURL(/\/$/);
  }

  // Category navigation: click first category link if present
  const firstCategory = page.locator('[data-testid^="category-link-"]').first();
  if (await firstCategory.count()) {
    await safeClick(firstCategory);
    await expect(page).toHaveURL(/\/category\//);
    await expect(page.getByTestId('category-page')).toBeVisible();
  }

  // Advanced search page
  const adv = page.getByTestId('nav-advanced-search');
  if (await adv.count()) {
    await safeClick(adv);
    await expect(page).toHaveURL(/\/(advanced-search|search\/advanced)/);
    await expect(page.getByTestId('advanced-search-page')).toBeVisible();
  }

  await guards.assertNoErrors();
});
