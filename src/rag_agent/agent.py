"""RAG-based Recruitment Evaluation Agent"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import aiohttp

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.callbacks.base import BaseCallbackHandler

from .vector_db import RecruitmentVectorDB


class SearchAPITool:
    """Web検索APIを使用するツール"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"
    
    async def search(self, query: str, num_results: int = 3) -> str:
        """Web検索を実行"""
        if not self.api_key:
            return "検索APIキーが設定されていません"
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": num_results,
            "hl": "ja",
            "gl": "jp"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url, 
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        for item in data.get("organic", [])[:num_results]:
                            results.append({
                                "title": item.get("title"),
                                "snippet": item.get("snippet"),
                                "link": item.get("link")
                            })
                        return json.dumps(results, ensure_ascii=False, indent=2)
                    else:
                        return f"検索エラー: {response.status}"
        except Exception as e:
            return f"検索実行エラー: {str(e)}"


class EvaluationCallbackHandler(BaseCallbackHandler):
    """評価プロセスの進行状況を追跡するコールバックハンドラ"""
    
    def __init__(self):
        self.iterations = 0
        self.tool_calls = []
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """ツールの実行開始時"""
        self.iterations += 1
        tool_name = serialized.get("name", "unknown")
        self.tool_calls.append({
            "iteration": self.iterations,
            "tool": tool_name,
            "input": input_str[:200],
            "timestamp": datetime.now().isoformat()
        })
        print(f"\n🔍 反復 {self.iterations}: {tool_name} を実行中...")


class RAGRecruitmentAgent:
    """採用評価を行うRAGエージェント"""
    
    def __init__(
        self,
        vector_db: RecruitmentVectorDB,
        openai_api_key: Optional[str] = None,
        serper_api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.2,
        max_iterations: int = 4
    ):
        self.vector_db = vector_db
        self.search_api = SearchAPITool(serper_api_key)
        self.callback_handler = EvaluationCallbackHandler()
        
        # LLMの初期化
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
        )
        
        # ツールの定義
        self.search_similar_tool = Tool(
            name="search_similar_cases",
            func=self._search_similar_evaluations,
            description="過去の類似した採用評価事例を検索する。求人要件と候補者情報を含むクエリを入力"
        )
        
        self.web_search_tool = Tool(
            name="web_search",
            func=lambda q: asyncio.run(self.search_api.search(q)),
            description="Webで追加情報を検索する。企業情報、技術トレンド、給与相場などを調査"
        )
        
        # エージェントのプロンプト
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """あなたは採用評価の専門家です。
過去の評価事例とWeb検索を活用しながら、候補者と採用要件のマッチング度を評価してください。

評価プロセス:
1. まず過去の類似事例を検索し、評価の参考にする
2. 不足情報があれば、Web検索で補完する（企業情報、技術詳細、市場相場など）
3. 必要に応じて追加の検索を行い、評価の精度を高める
4. 最大4回まで検索を繰り返し、十分な情報を収集する

評価の観点:
- 必須スキルの充足度（各スキルを個別に評価）
- 歓迎スキルの保有状況
- 経験年数とレベル感の適合性
- チーム規模やプロジェクト経験の適合性
- 企業文化とのフィット
- 成長ポテンシャル
- 給与期待値と予算の整合性

最終的に以下の形式で評価を出力してください:
```json
{
  "score": 0-100の数値,
  "grade": "A/B/C/D",
  "positive_reasons": ["理由1", "理由2", "理由3"],
  "concerns": ["懸念1", "懸念2"],
  "recommendation": "high/medium/low",
  "salary_estimate": "推定年収レンジ",
  "additional_insights": "Web検索で得た追加の洞察"
}
```"""),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # エージェントの初期化
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=[self.search_similar_tool, self.web_search_tool],
            prompt=self.prompt
        )
        
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=[self.search_similar_tool, self.web_search_tool],
            verbose=True,
            max_iterations=max_iterations,
            callbacks=[self.callback_handler]
        )
    
    def _search_similar_evaluations(self, query: str) -> str:
        """類似する過去の評価事例を検索"""
        results = self.vector_db.search_similar_cases(
            query=query,
            k=3,
            score_threshold=0.6
        )
        
        if not results:
            return "類似する評価事例が見つかりませんでした"
        
        similar_cases = []
        for doc, score in results:
            case = {
                "similarity_score": round(1 - score, 3),
                "job_title": doc.metadata.get("job_title"),
                "company": doc.metadata.get("company"),
                "grade": doc.metadata.get("final_grade"),
                "score": doc.metadata.get("final_score"),
                "positive": doc.metadata.get("positive_summary"),
                "concerns": doc.metadata.get("concern_summary"),
                "decision": doc.metadata.get("decision")
            }
            similar_cases.append(case)
        
        return json.dumps(similar_cases, ensure_ascii=False, indent=2)
    
    def evaluate_candidate(
        self, 
        job_requirement: Dict, 
        candidate_resume: Dict,
        context: Optional[Dict] = None
    ) -> Dict:
        """候補者を評価"""
        # 評価用のテキストを作成
        input_text = self._format_evaluation_input(
            job_requirement, 
            candidate_resume,
            context
        )
        
        # コールバックハンドラをリセット
        self.callback_handler.iterations = 0
        self.callback_handler.tool_calls = []
        
        # エージェントを実行
        try:
            result = self.agent_executor.invoke({
                "input": input_text
            })
            
            # 結果をパース
            evaluation = self._parse_evaluation_result(result["output"])
            
            # 実行統計を追加
            evaluation["execution_stats"] = {
                "total_iterations": self.callback_handler.iterations,
                "tool_calls": self.callback_handler.tool_calls,
                "model": self.llm.model_name,
                "timestamp": datetime.now().isoformat()
            }
            
            return evaluation
            
        except Exception as e:
            return {
                "error": True,
                "message": str(e),
                "score": 0,
                "grade": "D",
                "recommendation": "low"
            }
    
    def _format_evaluation_input(
        self,
        job_req: Dict,
        resume: Dict,
        context: Optional[Dict] = None
    ) -> str:
        """評価用の入力テキストをフォーマット"""
        input_text = f"""
以下の採用要件と候補者情報を評価してください。

【採用要件】
企業: {job_req.get('company', '不明')}
職種: {job_req.get('title')}
必須スキル: {', '.join(job_req.get('required_skills', []))}
歓迎スキル: {', '.join(job_req.get('preferred_skills', []))}
経験年数: {job_req.get('experience_years')}
チーム規模: {job_req.get('team_size')}
年収レンジ: {job_req.get('salary_range')}
業務内容: {job_req.get('description', '')}

【候補者情報】
名前: {resume.get('name', '候補者')}
経験年数: {resume.get('experience')}
現在の役職: {resume.get('current_position')}
スキル: {', '.join(resume.get('skills', []))}
職歴: {resume.get('work_history', '')}
実績: {resume.get('achievements', '')}
"""
        
        if context:
            input_text += f"\n【追加コンテキスト】\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        
        return input_text
    
    def _parse_evaluation_result(self, output: str) -> Dict:
        """評価結果をパース"""
        try:
            # JSON部分を抽出
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                # JSON形式でない場合は構造化
                result = {
                    "score": 50,
                    "grade": "C",
                    "positive_reasons": ["評価結果の解析に失敗しました"],
                    "concerns": [],
                    "recommendation": "medium",
                    "raw_output": output
                }
            
            # 必須フィールドの確認
            result.setdefault("score", 50)
            result.setdefault("grade", "C")
            result.setdefault("positive_reasons", [])
            result.setdefault("concerns", [])
            result.setdefault("recommendation", "medium")
            
            return result
            
        except Exception as e:
            return {
                "score": 0,
                "grade": "D",
                "positive_reasons": [],
                "concerns": [f"評価結果の解析エラー: {str(e)}"],
                "recommendation": "low",
                "raw_output": output
            }


# テスト実行
if __name__ == "__main__":
    # 環境変数の確認
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEYが設定されていません")
        exit(1)
    
    # ベクトルDBとエージェントの初期化
    db = RecruitmentVectorDB()
    agent = RAGRecruitmentAgent(db)
    
    # テスト評価
    test_job = {
        "title": "フロントエンドエンジニア",
        "company": "株式会社Webイノベーション",
        "required_skills": ["React", "TypeScript", "CSS"],
        "preferred_skills": ["Next.js", "テスト自動化"],
        "experience_years": "3年以上",
        "team_size": "5名",
        "salary_range": "500-700万円",
        "description": "自社プロダクトのフロントエンド開発"
    }
    
    test_candidate = {
        "name": "テスト候補者B",
        "experience": "4年",
        "current_position": "フロントエンドエンジニア",
        "skills": ["React", "JavaScript", "HTML/CSS", "Vue.js"],
        "work_history": "Web制作会社でフロントエンド開発に従事",
        "achievements": "大規模ECサイトのUI/UX改善プロジェクトをリード"
    }
    
    print("🤖 評価を開始します...\n")
    result = agent.evaluate_candidate(test_job, test_candidate)
    
    print("\n📊 評価結果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))