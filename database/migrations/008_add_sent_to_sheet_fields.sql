-- Add sent_to_sheet fields to ai_evaluations table
-- These fields track whether candidates have been exported to spreadsheets

-- Add sent_to_sheet flag
ALTER TABLE ai_evaluations
ADD COLUMN IF NOT EXISTS sent_to_sheet BOOLEAN DEFAULT FALSE;

-- Add sent_to_sheet timestamp
ALTER TABLE ai_evaluations
ADD COLUMN IF NOT EXISTS sent_to_sheet_at TIMESTAMPTZ;

-- Create an index for faster queries on sent candidates
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_sent_to_sheet 
ON ai_evaluations(sent_to_sheet) 
WHERE sent_to_sheet = TRUE;

-- Create an index for sent_to_sheet_at for chronological queries
CREATE INDEX IF NOT EXISTS idx_ai_evaluations_sent_to_sheet_at 
ON ai_evaluations(sent_to_sheet_at DESC) 
WHERE sent_to_sheet_at IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN ai_evaluations.sent_to_sheet IS 'Flag indicating whether this candidate has been exported to a spreadsheet';
COMMENT ON COLUMN ai_evaluations.sent_to_sheet_at IS 'Timestamp when the candidate was exported to a spreadsheet';