# Age and Enrolled Company Count Update

## Summary
Added support for extracting and storing candidate age and enrolled company count from BizReach profiles.

## Changes Made

### 1. Chrome Extension (Scraper)
- **File**: `/extension/content/scrapers/bizreach.js`
- Added XPath extraction for age from `//*[@id="jsi_resume_detail"]/div[3]/ul/li[1]`
- Added XPath extraction for enrolled company count from `//*[@id="jsi_resume_ja_block"]/table/tbody/tr[1]/td/ul`
- Parse age from "XX歳" format to integer
- Count `<li>` elements for enrolled companies
- Include both fields in candidate data object

### 2. Database Schema
- **Migration**: `/webapp/migrations/add_age_enrolled_company_fields.sql`
- Added `age` column (INTEGER, nullable)
- Added `enrolled_company_count` column (INTEGER, default 0)

### 3. API Endpoint
- **File**: `/webapp/routers/extension_api.py`
- Updated `CandidateData` model to include `age` and `enrolled_company_count` fields
- Updated `save_candidates_batch` function to save these fields to database

### 4. UI Updates
- **File**: `/webapp/templates/admin/job_candidates.html`
- Added columns to display age and enrolled company count in candidate list
- Added these fields to the candidate detail modal

## How to Apply Database Migration

1. **Option A - Supabase Dashboard**:
   ```sql
   -- Run this SQL in your Supabase SQL editor
   ALTER TABLE candidates
   ADD COLUMN IF NOT EXISTS age INTEGER,
   ADD COLUMN IF NOT EXISTS enrolled_company_count INTEGER DEFAULT 0;

   COMMENT ON COLUMN candidates.age IS 'Candidate age extracted from profile';
   COMMENT ON COLUMN candidates.enrolled_company_count IS 'Number of companies the candidate has worked at';
   ```

2. **Option B - Using Migration Script**:
   ```bash
   cd webapp
   python apply_migration.py
   ```

## Testing

1. Reload the Chrome extension
2. Navigate to a BizReach candidate profile
3. Start scraping session
4. Verify that age and enrolled company count are extracted
5. Check the WebAPP to see these fields displayed in the candidate list

## Data Flow

1. Chrome extension extracts age and enrolled company count using XPath
2. Data is sent to WebAPP API in the candidate batch
3. API saves the data to Supabase `candidates` table
4. UI displays the fields in candidate lists and detail views