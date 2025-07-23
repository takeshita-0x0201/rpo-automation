-- candidatesテーブルにgenderカラムを追加
ALTER TABLE public.candidates
ADD COLUMN IF NOT EXISTS gender VARCHAR(1);

-- genderカラムにインデックスを追加（検索性能向上のため）
CREATE INDEX IF NOT EXISTS idx_candidates_gender ON public.candidates(gender);

-- コメントを追加
COMMENT ON COLUMN public.candidates.gender IS '性別情報（M:男性, F:女性）';