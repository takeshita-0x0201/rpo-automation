// Debug script for BizReach scraper
// Add this to the console to debug data extraction

(function debugBizReachScraper() {
  console.log("=== BIZREACH SCRAPER DEBUG ===");
  
  // Check if scraper is loaded
  if (typeof window.BizReachScraper === 'undefined') {
    console.error("BizReachScraper is not loaded!");
    return;
  }
  
  const scraper = new window.BizReachScraper();
  
  // Override extractCandidateData to log what's being extracted
  const originalExtract = scraper.extractCandidateData;
  scraper.extractCandidateData = async function(element, index) {
    console.log(`\n--- Extracting candidate ${index + 1} ---`);
    
    // Log the element being processed
    console.log("Element:", element);
    
    // Try to find specific elements
    const selectors = {
      pageHeader: '.lapPageHeader.cf',
      resumePageId: '.resumePageID.fl',
      clipboardElement: '[data-clipboard-text]',
      companyByTitle: '[title="jsi_company_header_name_0_0"]',
      resumeBlock: '#jsi_resume_ja_block.resumeView',
      resumeView: '.resumeView'
    };
    
    console.log("Checking selectors:");
    Object.entries(selectors).forEach(([name, selector]) => {
      const el = element.querySelector(selector);
      console.log(`- ${name}: ${el ? '✓ Found' : '✗ Not found'}`);
      if (el && name === 'resumePageId') {
        console.log(`  Value: ${el.textContent.trim()}`);
      }
      if (el && name === 'clipboardElement') {
        console.log(`  Value: ${el.getAttribute('data-clipboard-text')}`);
      }
      if (el && name === 'companyByTitle') {
        console.log(`  Value: ${el.textContent.trim()}`);
      }
    });
    
    // Call original method
    const result = await originalExtract.call(this, element, index);
    
    console.log("Extracted data:", JSON.stringify(result, null, 2));
    
    // Validate required fields
    const requiredFields = ['candidate_id', 'candidate_link'];
    requiredFields.forEach(field => {
      if (!result[field]) {
        console.error(`Missing required field: ${field}`);
      }
    });
    
    return result;
  };
  
  // Override sendBatchData to log what's being sent
  const originalSend = scraper.sendBatchData;
  scraper.sendBatchData = async function() {
    console.log("\n=== SENDING BATCH DATA ===");
    console.log("Current batch:", JSON.stringify(this.currentBatch, null, 2));
    console.log("Session info:", JSON.stringify(this.sessionInfo, null, 2));
    
    // Check for missing session data
    if (!this.sessionInfo) {
      console.error("Session info is missing!");
    } else {
      ['sessionId', 'clientId', 'requirementId'].forEach(field => {
        if (!this.sessionInfo[field]) {
          console.error(`Missing session field: ${field}`);
        }
      });
    }
    
    // Call original method
    try {
      const result = await originalSend.call(this);
      console.log("Send result:", result);
      return result;
    } catch (error) {
      console.error("Send error:", error);
      throw error;
    }
  };
  
  console.log("Debug hooks installed. Start scraping to see detailed logs.");
  
  // Also check current page structure
  console.log("\n=== CURRENT PAGE ANALYSIS ===");
  
  // Check for drawer resume element
  const drawerResume = document.querySelector('.lapPageInner.ns-drawer-resume');
  const resumePageInner = document.querySelector('#jsi_resume_page_inner');
  
  console.log("Drawer resume element:", drawerResume ? "Found" : "Not found");
  console.log("Resume page inner:", resumePageInner ? "Found" : "Not found");
  
  // Try to find candidate info manually
  if (drawerResume || resumePageInner) {
    const container = drawerResume || resumePageInner;
    
    // Look for ID
    const idElement = container.querySelector('.resumePageID');
    if (idElement) {
      console.log("Found candidate ID:", idElement.textContent.trim());
    }
    
    // Look for clipboard link
    const clipboardLinks = container.querySelectorAll('[data-clipboard-text]');
    clipboardLinks.forEach((link, i) => {
      console.log(`Clipboard link ${i + 1}:`, link.getAttribute('data-clipboard-text'));
    });
    
    // Look for company
    const companyElements = container.querySelectorAll('[title*="company"]');
    companyElements.forEach((el, i) => {
      console.log(`Company element ${i + 1}:`, el.textContent.trim());
    });
  }
  
  // Expose scraper instance for manual testing
  window.debugScraper = scraper;
  console.log("\nScraper instance available as window.debugScraper");
  console.log("Try: debugScraper.extractCandidateData(document.querySelector('.lapPageInner'), 0)");
})();