const puppeteer = require('puppeteer');

(async () => {
  try {
    console.log('✅ Swaggy Scraper is running!');

    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();

    await page.goto('https://swaggystocks.com/dashboard/unusual-options-activity', {
      waitUntil: 'domcontentloaded', // Faster and more reliable for dynamic sites
      timeout: 60000 // Increased timeout to 60 seconds
    });

    // Insert your scraping logic here (e.g., grabbing table data, screenshots, etc.)
    console.log('✅ Page loaded successfully!');

    await browser.close();
  } catch (err) {
    console.error('❌ Error:', err);
  }
})();
