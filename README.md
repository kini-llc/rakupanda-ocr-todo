# RAKUPANDA AI-OCR トード様向け

トードインターナショナル様の発注書PDF（付箋部分）から、PCシステム入力用CSVを抽出するStreamlit Webアプリ。

## 機能

- 複数PDFファイルのバッチ処理
- Dify ワークフロー連携（Gemini OCR）
- ファイルごとのタブ切替UI
- 表形式の編集（セルを直接修正）
- ファイルごとの確定CSVダウンロード

## アーキテクチャ

```
[Streamlit] フロントエンド
    ↕
[Dify API] OCR処理（Gemini）
    ↓
[CSV] PCシステム取り込み
```

## ローカル開発

### 1. 仮想環境の準備

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. APIキーの設定

`.streamlit/secrets.toml` を作成：

```toml
DIFY_API_KEY = "app-XXXXXXXXXXXXXXXXXXXXXXXX"
```

⚠️ このファイルは `.gitignore` でGit管理対象外。GitHubにはアップしない。

### 3. 起動

```bash
streamlit run app.py
```

ブラウザで http://localhost:8501 が開く。

## デプロイ（Streamlit Community Cloud）

1. GitHub にプッシュ
2. https://share.streamlit.io にサインアップ
3. このリポジトリを連携
4. アプリ設定の Secrets に `DIFY_API_KEY` を追加
5. 公開URLが発行される

## バージョン履歴

- v0.4 - クラウドデプロイ対応（環境変数化）
- v0.3 - 編集機能追加（st.data_editor）
- v0.2 - バッチ処理＆タブUI
- v0.1 - 最小機能版

## 開発

KINI合同会社  
https://kini.jp
