-- テスト用のユーザーロールデータ
-- Supabase SQL Editorで実行してください

-- まず、auth.usersテーブルからユーザーIDを確認
SELECT id, email FROM auth.users;

-- profilesテーブルにロールを設定（IDを実際のユーザーIDに置き換えてください）
-- 例: adminユーザー
INSERT INTO profiles (id, role, full_name)
VALUES ('YOUR-ADMIN-USER-ID', 'admin', 'Admin User')
ON CONFLICT (id) 
DO UPDATE SET role = 'admin';

-- 例: 通常ユーザー
INSERT INTO profiles (id, role, full_name)
VALUES ('YOUR-USER-ID', 'user', 'Normal User')
ON CONFLICT (id) 
DO UPDATE SET role = 'user';

-- ロールが正しく設定されたか確認
SELECT p.id, p.role, p.full_name, u.email
FROM profiles p
JOIN auth.users u ON p.id = u.id;