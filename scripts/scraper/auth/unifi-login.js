/**
 * UniFi Authentication Module
 * Handles authentication to the UniFi API documentation portal
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const COOKIES_FILE = path.join(__dirname, '../../session-cookies.json');

/**
 * Load existing session cookies if available
 * @returns {Promise<Array|null>} Cookies or null if not found
 */
export async function loadSessionCookies() {
  try {
    const cookiesData = await fs.readFile(COOKIES_FILE, 'utf-8');
    const cookies = JSON.parse(cookiesData);
    console.log('✓ Loaded existing session cookies');
    return cookies;
  } catch (error) {
    console.log('No existing session cookies found');
    return null;
  }
}

/**
 * Save session cookies to file
 * @param {Array} cookies - Browser cookies
 */
export async function saveSessionCookies(cookies) {
  await fs.writeFile(COOKIES_FILE, JSON.stringify(cookies, null, 2));
  console.log('✓ Session cookies saved');
}

/**
 * Check if session cookies are still valid
 * @param {Page} page - Puppeteer page instance
 * @param {Array} cookies - Cookies to check
 * @returns {Promise<boolean>} True if cookies are valid
 */
export async function validateSessionCookies(page, cookies) {
  try {
    // Set cookies
    await page.setCookie(...cookies);

    // Navigate to API docs page
    await page.goto('https://unifi.ui.com/settings/api-docs', {
      waitUntil: 'networkidle2',
      timeout: 30000
    });

    // Wait a bit for redirects
    await page.waitForTimeout(2000);

    // Check if we're still authenticated (not redirected to login)
    const currentUrl = page.url();

    if (currentUrl.includes('login') || currentUrl.includes('auth')) {
      console.log('Session cookies expired or invalid');
      return false;
    }

    console.log('✓ Session cookies are valid');
    return true;
  } catch (error) {
    console.error('Error validating cookies:', error.message);
    return false;
  }
}

/**
 * Perform interactive login to UniFi portal
 * @param {Page} page - Puppeteer page instance
 * @param {Object} credentials - {email, password}
 * @returns {Promise<Array>} Session cookies
 */
export async function performLogin(page, credentials) {
  console.log('Starting authentication process...');

  // Navigate to API docs (will redirect to login if not authenticated)
  await page.goto('https://unifi.ui.com/settings/api-docs', {
    waitUntil: 'networkidle2',
    timeout: 30000
  });

  const currentUrl = page.url();

  // Check if already authenticated
  if (!currentUrl.includes('login') && !currentUrl.includes('auth')) {
    console.log('✓ Already authenticated');
    const cookies = await page.cookies();
    await saveSessionCookies(cookies);
    return cookies;
  }

  console.log('Authentication required...');

  // Wait for email input field
  try {
    await page.waitForSelector('input[type="email"], input[name="email"], input[placeholder*="email" i]', {
      timeout: 10000
    });
  } catch (error) {
    throw new Error('Could not find email input field. Page structure may have changed.');
  }

  // Find and fill email field
  const emailSelector = await page.evaluate(() => {
    const inputs = Array.from(document.querySelectorAll('input'));
    const emailInput = inputs.find(input =>
      input.type === 'email' ||
      input.name?.toLowerCase().includes('email') ||
      input.placeholder?.toLowerCase().includes('email')
    );
    if (!emailInput) return null;

    // Create unique selector
    if (emailInput.id) return `#${emailInput.id}`;
    if (emailInput.name) return `input[name="${emailInput.name}"]`;
    return 'input[type="email"]';
  });

  if (!emailSelector) {
    throw new Error('Could not determine email input selector');
  }

  // Fill in email
  await page.type(emailSelector, credentials.email);
  console.log('✓ Email entered');

  // Wait for password field
  await page.waitForSelector('input[type="password"]', { timeout: 5000 });

  // Fill in password
  await page.type('input[type="password"]', credentials.password);
  console.log('✓ Password entered');

  // Find and click submit button
  const submitButton = await page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
    const submitBtn = buttons.find(btn =>
      btn.type === 'submit' ||
      btn.textContent?.toLowerCase().includes('sign in') ||
      btn.textContent?.toLowerCase().includes('log in') ||
      btn.textContent?.toLowerCase().includes('continue')
    );
    if (!submitBtn) return null;

    // Create unique selector
    if (submitBtn.id) return `#${submitBtn.id}`;
    if (submitBtn.className) return `.${submitBtn.className.split(' ').join('.')}`;
    return 'button[type="submit"]';
  });

  if (!submitButton) {
    throw new Error('Could not find submit button');
  }

  // Click submit
  await page.click(submitButton);
  console.log('✓ Login submitted');

  // Wait for navigation after login
  await page.waitForNavigation({
    waitUntil: 'networkidle2',
    timeout: 30000
  }).catch(() => {
    console.log('Navigation timeout - checking if login succeeded anyway');
  });

  // Check if login succeeded
  const finalUrl = page.url();
  if (finalUrl.includes('login') || finalUrl.includes('auth')) {
    throw new Error('Login failed - still on login page. Check credentials.');
  }

  // Handle potential 2FA or additional verification
  await page.waitForTimeout(3000);

  // Check for 2FA prompts
  const has2FA = await page.evaluate(() => {
    const text = document.body.textContent?.toLowerCase() || '';
    return text.includes('verification') ||
           text.includes('two-factor') ||
           text.includes('2fa') ||
           text.includes('authenticator');
  });

  if (has2FA) {
    console.warn('\n⚠️  Two-factor authentication detected!');
    console.warn('Please complete 2FA manually in the browser window.');
    console.warn('Waiting 60 seconds for manual completion...\n');

    // Wait for user to complete 2FA
    await page.waitForTimeout(60000);
  }

  // Navigate to API docs to confirm access
  await page.goto('https://unifi.ui.com/settings/api-docs', {
    waitUntil: 'networkidle2',
    timeout: 30000
  });

  const cookies = await page.cookies();
  await saveSessionCookies(cookies);

  console.log('✓ Authentication successful');
  return cookies;
}

/**
 * Authenticate to UniFi portal with session management
 * @param {Page} page - Puppeteer page instance
 * @param {Object} credentials - {email, password}
 * @returns {Promise<Array>} Session cookies
 */
export async function authenticateUniFi(page, credentials) {
  // Try to load existing cookies
  const existingCookies = await loadSessionCookies();

  if (existingCookies && existingCookies.length > 0) {
    // Validate existing cookies
    const isValid = await validateSessionCookies(page, existingCookies);

    if (isValid) {
      return existingCookies;
    }
  }

  // Perform fresh login
  return await performLogin(page, credentials);
}

/**
 * Clear saved session cookies
 */
export async function clearSessionCookies() {
  try {
    await fs.unlink(COOKIES_FILE);
    console.log('✓ Session cookies cleared');
  } catch (error) {
    // File doesn't exist, nothing to clear
  }
}
