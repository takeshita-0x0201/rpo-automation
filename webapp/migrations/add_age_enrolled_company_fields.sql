-- Add age and enrolled_company_count fields to candidates table
ALTER TABLE candidates
ADD COLUMN IF NOT EXISTS age INTEGER,
ADD COLUMN IF NOT EXISTS enrolled_company_count INTEGER DEFAULT 0;

-- Add comments for documentation
COMMENT ON COLUMN candidates.age IS 'Candidate age extracted from profile';
COMMENT ON COLUMN candidates.enrolled_company_count IS 'Number of companies the candidate has worked at';