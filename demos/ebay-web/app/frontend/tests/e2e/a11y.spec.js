import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// Basic a11y smoke checks.
// We run axe-core on key pages and assert no serious/critical issues.

test('a11y smoke: home page has no critical/serious violations', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });

  const results = await new AxeBuilder({ page })
    // Keep this lightweight; ignore color contrast which can be noisy in demos.
    .disableRules(['color-contrast'])
    .analyze();

  const serious = results.violations.filter((v) => ['serious', 'critical'].includes(v.impact || ''));

  expect(
    serious,
    `A11y violations (serious/critical):\n${JSON.stringify(serious, null, 2)}`,
  ).toEqual([]);
});
