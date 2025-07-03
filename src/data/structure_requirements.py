
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_document_content(document_id):
    # サービスアカウントキーファイルのパスを環境変数から取得
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

    # 認証情報のロード
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=['https://www.googleapis.com/auth/documents.readonly']
    )

    # Google Docs APIクライアントの構築
    service = build('docs', 'v1', credentials=credentials)

    # ドキュメントの内容を取得
    document = service.documents().get(documentId=document_id).execute()
    content = ""
    for element in document.get('body').get('content'):
        if 'paragraph' in element:
            for run in element.get('paragraph').get('elements'):
                if 'textRun' in run:
                    content += run.get('textRun').get('content')
    return content

def structure_requirements(document_id):
    # ここにGemini APIを呼び出して構造化するロジックを実装します
    # 現時点では、ドキュメントの内容をそのまま返すダミー実装です
    doc_content = get_document_content(document_id)
    print(f"Document Content: {doc_content}")
    # 実際にはGemini APIを呼び出し、構造化されたJSONを返します
    return {"raw_content": doc_content, "structured_data": {}}

if __name__ == '__main__':
    import argparse
    from dotenv import load_dotenv

    # .envファイルをロード
    load_dotenv()

    parser = argparse.ArgumentParser(description='Structure job requirements from Google Docs.')
    parser.add_argument('--doc-id', type=str, required=True, help='Google Docs Document ID.')
    args = parser.parse_args()

    try:
        structured_data = structure_requirements(args.doc_id)
        print("Successfully processed document.")
        print(structured_data)
    except Exception as e:
        print(f"An error occurred: {e}")
