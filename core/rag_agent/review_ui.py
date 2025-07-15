"""Streamlit UI for Recruitment RAG System"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
from typing import Dict, Optional

from .vector_db import RecruitmentVectorDB
from .agent import RAGRecruitmentAgent
from .feedback_loop import FeedbackLoop


# ページ設定
st.set_page_config(
    page_title="採用候補者AI評価システム",
    page_icon="🎯",
    layout="wide"
)


def init_session_state():
    """セッション状態の初期化"""
    if "vector_db" not in st.session_state:
        st.session_state.vector_db = RecruitmentVectorDB()
    
    if "agent" not in st.session_state:
        st.session_state.agent = RAGRecruitmentAgent(st.session_state.vector_db)
    
    if "feedback_loop" not in st.session_state:
        st.session_state.feedback_loop = FeedbackLoop(st.session_state.vector_db)
    
    if "ai_result" not in st.session_state:
        st.session_state.ai_result = None
    
    if "evaluation_history" not in st.session_state:
        st.session_state.evaluation_history = []


def main():
    """メインアプリケーション"""
    init_session_state()
    
    st.title("🎯 採用候補者AI評価システム")
    
    # タブ
    tab1, tab2, tab3 = st.tabs(["新規評価", "評価履歴", "学習統計"])
    
    with tab1:
        render_evaluation_tab()
    
    with tab2:
        render_history_tab()
    
    with tab3:
        render_statistics_tab()


def render_evaluation_tab():
    """新規評価タブ"""
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("入力情報")
        
        # 採用要件入力
        with st.expander("採用要件", expanded=True):
            job_company = st.text_input("企業名", placeholder="株式会社〇〇")
            job_title = st.text_input("職種名", placeholder="バックエンドエンジニア")
            required_skills = st.text_area(
                "必須スキル（改行区切り）",
                placeholder="Python\nDjango\nAWS"
            )
            preferred_skills = st.text_area(
                "歓迎スキル（改行区切り）",
                placeholder="Docker\nKubernetes"
            )
            experience_years = st.text_input("必要経験年数", placeholder="3年以上")
            team_size = st.text_input("チーム規模", placeholder="8名")
            salary_range = st.text_input("年収レンジ", placeholder="600-900万円")
            job_description = st.text_area("業務内容", placeholder="ECサイトのバックエンド開発...")
        
        # 候補者情報入力
        with st.expander("候補者情報", expanded=True):
            candidate_name = st.text_input("候補者名", placeholder="候補者A")
            candidate_experience = st.text_input("経験年数", placeholder="5年")
            current_position = st.text_input("現在の役職", placeholder="シニアエンジニア")
            candidate_skills = st.text_area(
                "保有スキル（改行区切り）",
                placeholder="Python\nDjango\nFastAPI\nAWS"
            )
            work_history = st.text_area(
                "職歴",
                placeholder="2020-現在: 株式会社〇〇でバックエンド開発..."
            )
            achievements = st.text_area(
                "主な実績",
                placeholder="マイクロサービス化プロジェクトをリード..."
            )
        
        # 評価実行ボタン
        if st.button("🤖 AI評価を実行", type="primary", use_container_width=True):
            if job_title and candidate_experience:
                with st.spinner("評価を実行中..."):
                    # 採用要件の構造化
                    job_requirement = {
                        "company": job_company,
                        "title": job_title,
                        "required_skills": [s.strip() for s in required_skills.split('\n') if s.strip()],
                        "preferred_skills": [s.strip() for s in preferred_skills.split('\n') if s.strip()],
                        "experience_years": experience_years,
                        "team_size": team_size,
                        "salary_range": salary_range,
                        "description": job_description
                    }
                    
                    # 候補者情報の構造化
                    candidate_resume = {
                        "name": candidate_name,
                        "experience": candidate_experience,
                        "current_position": current_position,
                        "skills": [s.strip() for s in candidate_skills.split('\n') if s.strip()],
                        "work_history": work_history,
                        "achievements": achievements
                    }
                    
                    # AI評価の実行
                    result = st.session_state.agent.evaluate_candidate(
                        job_requirement,
                        candidate_resume
                    )
                    
                    st.session_state.ai_result = {
                        "job_requirement": job_requirement,
                        "candidate_resume": candidate_resume,
                        "ai_evaluation": result,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    st.success("評価が完了しました！")
            else:
                st.error("必須項目を入力してください")
    
    with col2:
        st.header("評価結果")
        
        if st.session_state.ai_result:
            result = st.session_state.ai_result["ai_evaluation"]
            
            # メトリクス表示
            col_score, col_grade, col_rec = st.columns(3)
            with col_score:
                st.metric("スコア", f"{result.get('score', 0)}/100")
            with col_grade:
                grade = result.get('grade', 'C')
                grade_color = {
                    'A': '🟢', 'B': '🔵', 'C': '🟡', 'D': '🔴'
                }.get(grade, '⚪')
                st.metric("グレード", f"{grade_color} {grade}")
            with col_rec:
                rec = result.get('recommendation', 'medium')
                rec_text = {
                    'high': '強く推奨',
                    'medium': '推奨',
                    'low': '要検討'
                }.get(rec, rec)
                st.metric("推奨度", rec_text)
            
            # 詳細情報
            st.subheader("ポジティブな点")
            for i, reason in enumerate(result.get('positive_reasons', []), 1):
                st.write(f"{i}. ✅ {reason}")
            
            st.subheader("懸念事項")
            for i, concern in enumerate(result.get('concerns', []), 1):
                st.write(f"{i}. ⚠️ {concern}")
            
            if result.get('salary_estimate'):
                st.info(f"💰 推定年収: {result['salary_estimate']}")
            
            if result.get('additional_insights'):
                st.info(f"💡 追加の洞察: {result['additional_insights']}")
            
            # 人間による最終評価
            st.divider()
            st.subheader("👤 最終評価（人間）")
            
            col_human1, col_human2 = st.columns(2)
            with col_human1:
                final_score = st.slider(
                    "最終スコア",
                    0, 100,
                    value=result.get('score', 50)
                )
                final_grade = st.selectbox(
                    "最終グレード",
                    ["A", "B", "C", "D"],
                    index=["A", "B", "C", "D"].index(result.get('grade', 'C'))
                )
            
            with col_human2:
                reviewer_name = st.text_input("評価者名", placeholder="採用マネージャー")
                decision = st.selectbox(
                    "判定",
                    ["次選考へ進む", "保留", "不採用"]
                )
            
            comments = st.text_area("コメント", placeholder="評価の根拠や追加情報を記入...")
            
            if st.button("✅ 評価を確定して学習", type="secondary", use_container_width=True):
                if reviewer_name:
                    # 評価データの構築
                    evaluation_data = {
                        **st.session_state.ai_result,
                        "human_review": {
                            "final_score": final_score,
                            "final_grade": final_grade,
                            "reviewer": reviewer_name,
                            "comments": comments,
                            "decision": decision
                        }
                    }
                    
                    # フィードバックループに追加
                    doc_id = st.session_state.feedback_loop.add_human_reviewed_data(
                        evaluation_data
                    )
                    
                    # 履歴に追加
                    st.session_state.evaluation_history.append(evaluation_data)
                    
                    st.success(f"評価を確定しました！ (ID: {doc_id})")
                    st.balloons()
                    
                    # 結果をクリア
                    st.session_state.ai_result = None
                    st.experimental_rerun()
                else:
                    st.error("評価者名を入力してください")
        else:
            st.info("左側のフォームに情報を入力して、AI評価を実行してください")


def render_history_tab():
    """評価履歴タブ"""
    st.header("評価履歴")
    
    if st.session_state.evaluation_history:
        # データフレームに変換
        history_data = []
        for eval_data in st.session_state.evaluation_history:
            history_data.append({
                "評価日時": eval_data["timestamp"][:19],
                "企業": eval_data["job_requirement"]["company"],
                "職種": eval_data["job_requirement"]["title"],
                "候補者": eval_data["candidate_resume"]["name"],
                "AIスコア": eval_data["ai_evaluation"]["score"],
                "AIグレード": eval_data["ai_evaluation"]["grade"],
                "最終スコア": eval_data["human_review"]["final_score"],
                "最終グレード": eval_data["human_review"]["final_grade"],
                "判定": eval_data["human_review"]["decision"],
                "評価者": eval_data["human_review"]["reviewer"]
            })
        
        df = pd.DataFrame(history_data)
        st.dataframe(df, use_container_width=True)
        
        # CSVダウンロード
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv,
            file_name=f"evaluation_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("まだ評価履歴がありません")


def render_statistics_tab():
    """学習統計タブ"""
    st.header("学習統計")
    
    # 統計情報の取得
    stats = st.session_state.feedback_loop.get_learning_statistics()
    
    # ベクトルDB統計
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総評価数", stats["total_evaluations"])
    with col2:
        st.metric("最終更新", stats["last_updated"][:10])
    with col3:
        grade_dist = stats["grade_distribution"]
        st.metric("A評価率", f"{(grade_dist['A'] / max(stats['total_evaluations'], 1) * 100):.1f}%")
    
    # グレード分布
    st.subheader("グレード分布")
    if stats["total_evaluations"] > 0:
        grade_df = pd.DataFrame(
            list(stats["grade_distribution"].items()),
            columns=["グレード", "件数"]
        )
        st.bar_chart(grade_df.set_index("グレード"))
    
    # フィードバック統計
    if "feedback_metrics" in stats:
        st.divider()
        st.subheader("フィードバック分析")
        
        metrics = stats["feedback_metrics"]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("フィードバック数", metrics["total_feedbacks"])
        with col2:
            st.metric("平均スコア差", f"{metrics['avg_score_difference']}点")
        with col3:
            st.metric("グレード一致率", f"{metrics['grade_match_rate']}%")
        
        # 学習品質
        quality = metrics["learning_quality"]
        if quality == "良好":
            st.success(f"✅ 学習品質: {quality}")
        else:
            st.warning(f"⚠️ 学習品質: {quality}")
    
    # リセットボタン（開発用）
    if st.checkbox("開発者モード"):
        st.warning("⚠️ 以下の操作は元に戻せません")
        if st.button("🗑️ ベクトルDBをリセット", type="secondary"):
            st.session_state.vector_db.reset_database()
            st.success("ベクトルDBをリセットしました")
            st.experimental_rerun()


if __name__ == "__main__":
    # 環境変数チェック
    if not os.getenv("OPENAI_API_KEY"):
        st.error("❌ OPENAI_API_KEYが設定されていません")
        st.stop()
    
    main()