// デバッグ用スクリプト - Bizreachのセレクタを確認

console.log('=== Bizreach Scraper Debug ===');

// 現在のURL
console.log('Current URL:', window.location.href);

// 候補者要素を確認
const candidateSelectors = [
  '.candidate-item',
  '[class*="candidate"]',
  '[data-test*="candidate"]',
  '.search-result-item',
  '.result-item',
  '.list-item'
];

console.log('\n--- Checking candidate selectors ---');
candidateSelectors.forEach(selector => {
  const elements = document.querySelectorAll(selector);
  if (elements.length > 0) {
    console.log(`✓ Found ${elements.length} elements with selector: ${selector}`);
    console.log('  Sample element:', elements[0]);
  }
});

// ページネーション要素を確認
const paginationSelectors = [
  '.pagination-next',
  '[class*="next"]',
  '[aria-label*="次"]',
  'button:contains("次")',
  'a:contains("次")',
  '.pager-next',
  '.next-page'
];

console.log('\n--- Checking pagination selectors ---');
paginationSelectors.forEach(selector => {
  try {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
      console.log(`✓ Found ${elements.length} elements with selector: ${selector}`);
      console.log('  Sample element:', elements[0]);
      console.log('  Disabled:', elements[0].disabled);
      console.log('  Href:', elements[0].href);
    }
  } catch (e) {
    // セレクタエラーを無視
  }
});

// ページ情報を確認
const pageInfoSelectors = [
  '.page-info',
  '[class*="page-info"]',
  '[class*="result-count"]',
  '[class*="total"]',
  '.search-count'
];

console.log('\n--- Checking page info selectors ---');
pageInfoSelectors.forEach(selector => {
  const elements = document.querySelectorAll(selector);
  if (elements.length > 0) {
    console.log(`✓ Found ${elements.length} elements with selector: ${selector}`);
    console.log('  Text:', elements[0].textContent);
  }
});

// 実際の候補者数をカウント
console.log('\n--- Actual candidate count ---');
const allCandidates = document.querySelectorAll('[class*="candidate"]');
console.log('Total elements with "candidate" in class:', allCandidates.length);

// デバッグ情報を返す関数
window.debugScraperInfo = function() {
  return {
    url: window.location.href,
    candidateCount: document.querySelectorAll('.candidate-item').length,
    hasNextButton: !!document.querySelector('.pagination-next'),
    nextButtonDisabled: document.querySelector('.pagination-next')?.disabled,
    pageInfo: document.querySelector('.page-info')?.textContent
  };
};