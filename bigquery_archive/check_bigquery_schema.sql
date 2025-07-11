-- candidatesテーブルのスキーマを確認
SELECT 
  column_name,
  data_type,
  is_nullable,
  is_partitioning_column,
  clustering_ordinal_position
FROM 
  `rpo-automation.recruitment_data.INFORMATION_SCHEMA.COLUMNS`
WHERE 
  table_name = 'candidates'
ORDER BY 
  ordinal_position;