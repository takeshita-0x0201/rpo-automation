#!/usr/bin/env python3
"""
overall_assessment問題の修正案
reporter.pyの改善案を提示
"""

def improved_parse_final_judgment(text: str) -> dict:
    """改善されたパース処理"""
    print(f"  判定パース開始（文字数: {len(text)}）")
    
    # デフォルト値
    judgment = {
        'recommendation': 'C',
        'reason': '',
        'strengths': [],
        'concerns': [],
        'overall_assessment': ''
    }
    
    lines = text.strip().split('\n')
    current_section = None
    overall_lines = []  # 総合評価の行を集める
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 推奨度
        if line.startswith('推奨度:') or '推奨度:' in line:
            parts = line.split(':', 1)
            if len(parts) > 1:
                rec = parts[1].strip()
                if 'A' in rec:
                    judgment['recommendation'] = 'A'
                elif 'B' in rec:
                    judgment['recommendation'] = 'B'
                elif 'C' in rec:
                    judgment['recommendation'] = 'C'
                elif 'D' in rec:
                    judgment['recommendation'] = 'D'
                print(f"    推奨度検出: {judgment['recommendation']}")
        
        # 判定理由
        elif line.startswith('判定理由:'):
            parts = line.split(':', 1)
            if len(parts) > 1:
                judgment['reason'] = parts[1].strip()
            # 次の行も理由の続きかもしれない
            if i + 1 < len(lines) and not lines[i + 1].strip().startswith(('強み', '懸念', '総合評価')):
                judgment['reason'] += ' ' + lines[i + 1].strip()
        
        # セクション開始
        elif '強み' in line and ':' in line:
            current_section = 'strengths'
        elif '懸念' in line and ':' in line:
            current_section = 'concerns'
        elif ('総合評価' in line) and (':' in line or '：' in line):
            parts = line.split(':', 1) if ':' in line else line.split('：', 1)
            if len(parts) > 1 and parts[1].strip():
                overall_lines.append(parts[1].strip())
            current_section = 'overall'
        
        # 項目収集
        elif line.startswith('-') or line.startswith('・'):
            item = line[1:].strip()
            if current_section == 'strengths' and len(judgment['strengths']) < 3:
                judgment['strengths'].append(item)
            elif current_section == 'concerns' and len(judgment['concerns']) < 3:
                judgment['concerns'].append(item)
        
        # 総合評価の続き（空行まで、または次のセクションまで）
        elif current_section == 'overall' and line and not line.startswith(('-', '・')):
            # 次のセクションの開始を検出
            if any(keyword in line for keyword in ['推奨度:', '判定理由:', '強み:', '懸念点:', '面接確認事項:']):
                current_section = None
            else:
                overall_lines.append(line)
    
    # 総合評価を結合
    if overall_lines:
        judgment['overall_assessment'] = ' '.join(overall_lines).strip()
        print(f"    総合評価検出: {len(judgment['overall_assessment'])}文字")
    
    # デフォルト値の設定（総合評価以外）
    if not judgment['strengths']:
        judgment['strengths'] = ['詳細な強みは評価中']
    if not judgment['concerns']:
        judgment['concerns'] = ['特筆すべき懸念なし']
    
    # 総合評価のデフォルト値を改善
    if not judgment['overall_assessment']:
        # recommendationとreasonから自動生成
        if judgment['reason']:
            assessment = f"候補者は{judgment['reason']} "
            
            if judgment['recommendation'] == 'A':
                assessment += "以上の経験・スキルから、本ポジションに非常に適した人材と判断します。"
            elif judgment['recommendation'] == 'B':
                assessment += "必要な要件を概ね満たしており、本ポジションでの活躍が期待できます。"
            elif judgment['recommendation'] == 'C':
                assessment += "一定の要件は満たしているものの、面接での詳細確認が必要です。"
            else:
                assessment += "現時点では必須要件との適合度が低いと判断します。"
            
            judgment['overall_assessment'] = assessment
            print(f"    総合評価を自動生成: {len(assessment)}文字")
        else:
            # 最終手段のデフォルト
            judgment['overall_assessment'] = '詳細な評価結果については、強みと懸念点をご確認ください。'
            print(f"    総合評価にデフォルト値を設定")
    
    print(f"    パース完了: 推奨度={judgment['recommendation']}, 強み={len(judgment['strengths'])}, 懸念={len(judgment['concerns'])}")
    
    return judgment


# 修正提案を表示
if __name__ == '__main__':
    print("=== overall_assessment問題の修正提案 ===\n")
    
    print("1. reporter.pyの_parse_final_judgment関数を改善:")
    print("   - 総合評価のパース処理を強化")
    print("   - 複数行にまたがる総合評価を適切に取得")
    print("   - LLMが総合評価を生成しなかった場合の自動生成ロジックを追加")
    print()
    
    print("2. プロンプトの改善案:")
    print("   - 「総合評価:」の後に必ず内容を記載するよう明示的に指示")
    print("   - フォーマットの例を追加してLLMの出力を安定化")
    print()
    
    print("3. デバッグログの追加:")
    print("   - LLMの生の応答を一時的にログ出力")
    print("   - パース処理の各ステップでデバッグ情報を出力")
    print()
    
    print("4. 既存データの修復:")
    print("   - プレースホルダーのみの評価を検出")
    print("   - reasonとrecommendationから総合評価を再生成")
    
    # テストケース
    print("\n=== テスト実行 ===")
    
    test_text = """推奨度: B

判定理由: Python/Django開発5年、AWS環境でのマイクロサービス構築経験3年
チームリーダーとして5名規模の開発チームをマネジメント

強み:
- 必要な技術スキルを全て保有
- チームマネジメント経験が豊富
- 決済システムの実装経験

懸念点:
- 金融業界での経験が不足
- 転職回数がやや多い

総合評価: 技術力とリーダーシップは申し分なく、即戦力として期待できます。
金融業界特有の規制については入社後のキャッチアップが必要ですが、
学習意欲が高いため問題ないと判断します。"""
    
    result = improved_parse_final_judgment(test_text)
    print(f"\nパース結果:")
    print(f"  recommendation: {result['recommendation']}")
    print(f"  overall_assessment: {result['overall_assessment'][:50]}...")
    
    # 総合評価が欠けているケース
    print("\n=== 総合評価が欠けているケースのテスト ===")
    
    test_text2 = """推奨度: A

判定理由: 経理財務20年、上場企業でのCFO経験5年、IPO実績2社
業務プロセス設計とシステム導入で業務効率を50%改善

強み:
- IPO実績と上場企業での経験
- 業務改善の具体的成果
- チーム構築力

懸念点:
- 現職での在籍期間が短い
- 希望年収が高め"""
    
    result2 = improved_parse_final_judgment(test_text2)
    print(f"\nパース結果（自動生成）:")
    print(f"  recommendation: {result2['recommendation']}")
    print(f"  overall_assessment: {result2['overall_assessment']}")