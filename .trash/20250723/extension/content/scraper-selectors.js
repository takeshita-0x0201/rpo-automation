// 実際のBizreachのセレクタを動的に検出するヘルパー

// 次ページボタンの候補セレクタ
const NEXT_PAGE_SELECTORS = [
  // 一般的なページネーションセレクタ
  '.pagination-next',
  '.next-page',
  '.pager-next',
  'a[rel="next"]',
  'button[aria-label*="次"]',
  'button[aria-label*="Next"]',
  'a[aria-label*="次"]',
  'a[aria-label*="Next"]',
  
  // テキストベースの検索
  'button:contains("次へ")',
  'button:contains("次のページ")',
  'a:contains("次へ")',
  'a:contains("次のページ")',
  'a:contains("Next")',
  'button:contains("Next")',
  
  // クラス名に"next"を含む要素
  '[class*="next"]:not([class*="prev"])',
  '[class*="Next"]:not([class*="Prev"])',
  
  // アイコンベースのボタン
  'button > svg[class*="right"]',
  'button > svg[class*="arrow"]',
  'a > svg[class*="right"]',
  'a > svg[class*="arrow"]',
  
  // data属性ベース
  '[data-test*="next"]',
  '[data-testid*="next"]',
  '[data-qa*="next"]'
];

// 候補者要素の候補セレクタ
const CANDIDATE_ITEM_SELECTORS = [
  '.candidate-item',
  '.candidate-card',
  '.search-result-item',
  '.result-item',
  '.list-item',
  '[class*="candidate"]',
  '[data-test*="candidate"]',
  '[data-testid*="candidate"]',
  'article[class*="result"]',
  'div[class*="result-item"]'
];

// 動的にセレクタを検出する関数
function detectSelectors() {
  const detected = {
    nextButton: null,
    candidateItem: null,
    candidateName: null,
    candidateCompany: null
  };
  
  // 次ページボタンを検出
  for (const selector of NEXT_PAGE_SELECTORS) {
    try {
      const elements = document.querySelectorAll(selector);
      for (const elem of elements) {
        // ボタンが表示されていて、"次"に関連するテキストを含むか確認
        if (elem.offsetParent !== null && 
            (elem.textContent?.includes('次') || 
             elem.textContent?.toLowerCase().includes('next') ||
             elem.getAttribute('aria-label')?.includes('次'))) {
          detected.nextButton = selector;
          console.log(`✓ Next button detected: ${selector}`);
          break;
        }
      }
      if (detected.nextButton) break;
    } catch (e) {
      // セレクタエラーを無視
    }
  }
  
  // 候補者要素を検出
  let maxCount = 0;
  for (const selector of CANDIDATE_ITEM_SELECTORS) {
    try {
      const elements = document.querySelectorAll(selector);
      if (elements.length > maxCount) {
        maxCount = elements.length;
        detected.candidateItem = selector;
      }
    } catch (e) {
      // セレクタエラーを無視
    }
  }
  
  if (detected.candidateItem) {
    console.log(`✓ Candidate items detected: ${detected.candidateItem} (${maxCount} items)`);
    
    // 候補者要素内の詳細セレクタを検出
    const sampleItem = document.querySelector(detected.candidateItem);
    if (sampleItem) {
      // 名前を検出
      const nameSelectors = ['h2', 'h3', 'h4', '[class*="name"]', '[class*="title"]'];
      for (const sel of nameSelectors) {
        const nameElem = sampleItem.querySelector(sel);
        if (nameElem && nameElem.textContent.trim()) {
          detected.candidateName = sel;
          break;
        }
      }
      
      // 会社名を検出
      const companySelectors = ['[class*="company"]', '[class*="employer"]', '[class*="organization"]'];
      for (const sel of companySelectors) {
        const companyElem = sampleItem.querySelector(sel);
        if (companyElem && companyElem.textContent.trim()) {
          detected.candidateCompany = sel;
          break;
        }
      }
    }
  }
  
  return detected;
}

// エクスポート
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { detectSelectors, NEXT_PAGE_SELECTORS, CANDIDATE_ITEM_SELECTORS };
}