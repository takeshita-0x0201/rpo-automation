import os
import google.generativeai as genai
from dotenv import load_dotenv

class GeminiClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    async def structure_requirement(self, text: str) -> dict:
        prompt = f"""あなたは採用要件をJSON形式で構造化する専門家です。以下の採用要件テキストを、指定されたJSONスキーマに従って構造化してください。
応答は必ずMarkdownのJSONコードブロック（```json ... ```）で囲み、JSON以外の余計なテキストは一切含めないでください。

採用要件テキスト:
{text}

JSONスキーマ:
{{"title": "string", "position": "string", "required_skills": ["string"], "preferred_skills": ["string"], "experience_years_min": "integer", "experience_years_max": "integer", "education_level": "string", "salary_min": "integer", "salary_max": "integer", "work_location": "string", "employment_type": "string"}}

構造化されたJSONコードブロック:
```json
"""
        response = self.model.generate_content(prompt)
        return response.text

