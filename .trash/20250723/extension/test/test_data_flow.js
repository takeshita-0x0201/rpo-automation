// Test script to debug data flow from Chrome Extension to Supabase
// This script simulates the data flow and helps identify where the issue might be

console.log("=== TESTING DATA FLOW ===");

// 1. Test data extraction (what BizReachScraper should extract)
const testExtractedData = {
  candidate_id: "1079961",
  candidate_link: "https://cr-support.jp/resume/pdf?candidate=1079961",
  candidate_company: "株式会社サンプル",
  candidate_resume: "レジュメテキストまたはURL",
  platform: "bizreach",
  client_id: "test-client-uuid",
  requirement_id: "test-requirement-uuid",
  scraping_session_id: "test-session-uuid",
  scraped_at: new Date().toISOString()
};

console.log("1. Expected extracted data from BizReach page:");
console.log(JSON.stringify(testExtractedData, null, 2));

// 2. Test sendBatchData message format
const testMessageData = {
  type: "SEND_CANDIDATES",
  data: {
    candidates: [testExtractedData],
    platform: "bizreach",
    sessionId: "test-session-uuid",
    clientId: "test-client-uuid",
    requirementId: "test-requirement-uuid"
  }
};

console.log("\n2. Message sent from content script to background:");
console.log(JSON.stringify(testMessageData, null, 2));

// 3. Test API request body (what service-worker.js sends)
const testApiRequestBody = {
  candidates: [{
    candidate_id: "1079961",
    candidate_link: "https://cr-support.jp/resume/pdf?candidate=1079961",
    candidate_company: "株式会社サンプル",
    candidate_resume: "レジュメテキストまたはURL",
    platform: "bizreach",
    client_id: "test-client-uuid",
    requirement_id: "test-requirement-uuid",
    scraping_session_id: "test-session-uuid"
  }],
  session_id: "test-session-uuid"
};

console.log("\n3. API request body sent to /api/extension/candidates/batch:");
console.log(JSON.stringify(testApiRequestBody, null, 2));

// 4. Expected Supabase insert data
const testSupabaseData = {
  // Auto-generated by Supabase
  id: "auto-generated-uuid",
  created_at: "auto-generated-timestamp",
  updated_at: "auto-generated-timestamp",
  
  // From request
  candidate_id: "1079961",
  candidate_link: "https://cr-support.jp/resume/pdf?candidate=1079961",
  candidate_company: "株式会社サンプル",
  candidate_resume: "レジュメテキストまたはURL",
  platform: "bizreach",
  
  // Metadata
  scraped_at: "2025-07-16T...",
  scraped_by: "user-uuid-from-auth",
  
  // Relations
  client_id: "test-client-uuid",
  requirement_id: "test-requirement-uuid",
  scraping_session_id: "test-session-uuid"
};

console.log("\n4. Expected data in Supabase candidates table:");
console.log(JSON.stringify(testSupabaseData, null, 2));

// 5. Validation checks
console.log("\n=== VALIDATION CHECKS ===");

const requiredFields = [
  'candidate_id',
  'candidate_link',
  'platform',
  'client_id',
  'requirement_id'
];

console.log("\nRequired fields check:");
requiredFields.forEach(field => {
  const hasField = testExtractedData.hasOwnProperty(field);
  const value = testExtractedData[field];
  console.log(`- ${field}: ${hasField ? '✓' : '✗'} (value: ${value || 'undefined'})`);
});

console.log("\n=== COMMON ISSUES TO CHECK ===");
console.log("1. Are client_id and requirement_id being passed correctly from popup to content script?");
console.log("2. Is the scraping_session_id being generated and passed?");
console.log("3. Are the extracted values (candidate_id, link, company, resume) not null/undefined?");
console.log("4. Is the API endpoint returning success or an error?");
console.log("5. Check browser console for any error messages during data sending");

console.log("\n=== DEBUGGING STEPS ===");
console.log("1. Open Chrome DevTools while scraping");
console.log("2. Go to Network tab and filter for 'candidates/batch' requests");
console.log("3. Check the request payload and response");
console.log("4. Look for any 400/500 errors from the API");
console.log("5. Check Supabase logs for any database errors");