"""
RAKUPANDA AI-OCR トード様向け Streamlit雛形 v0.4

新機能（v0.3から追加）:
- APIキーを Streamlit Secrets から読み込み
- Streamlit Community Cloud にデプロイ可能
- ローカル開発時は .streamlit/secrets.toml から読み込み
"""

import streamlit as st
import requests
import json
import os
import time
from io import StringIO
import pandas as pd

# ============================================
# 設定
# ============================================
# APIキーは Streamlit Secrets から取得（ローカル: .streamlit/secrets.toml、本番: Streamlit Cloud Secrets）
API_KEY = st.secrets.get("DIFY_API_KEY", "")
BASE_URL = "https://api.dify.ai/v1"

ESTIMATED_SECONDS_PER_FILE = 20

# ============================================
# ページ設定
# ============================================
st.set_page_config(
    page_title="RAKUPANDA AI-OCR トード様向け",
    page_icon="🐼",
    layout="wide"
)

# ============================================
# セッション状態の初期化
# ============================================
if 'files_data' not in st.session_state:
    st.session_state.files_data = {}

if 'processing_started' not in st.session_state:
    st.session_state.processing_started = False

if 'all_completed' not in st.session_state:
    st.session_state.all_completed = False


# ============================================
# Dify API 関数
# ============================================
def upload_file_to_dify(file_bytes, file_name, user="streamlit-user"):
    url = f"{BASE_URL}/files/upload"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    files = {'file': (file_name, file_bytes, 'application/pdf')}
    data = {'user': user}
    
    response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    
    if response.status_code == 201:
        return response.json().get('id'), None
    else:
        return None, f"アップロード失敗: {response.status_code} {response.text}"


def run_dify_workflow(file_id, user="streamlit-user"):
    url = f"{BASE_URL}/workflows/run"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "inputs": {
            "file_PDF": {
                "transfer_method": "local_file",
                "upload_file_id": file_id,
                "type": "document"
            }
        },
        "response_mode": "blocking",
        "user": user
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=180)
    
    if response.status_code == 200:
        result = response.json()
        data_section = result.get('data', {})
        outputs = data_section.get('outputs', {})
        csv_result = outputs.get('result', '')
        elapsed = data_section.get('elapsed_time', 0) or 0
        return csv_result, elapsed, None
    else:
        return None, 0, f"ワークフロー実行失敗: {response.status_code} {response.text}"


def process_single_file(file_name, file_bytes):
    file_id, error = upload_file_to_dify(file_bytes, file_name)
    if error:
        return None, 0, error
    
    csv_result, elapsed, error = run_dify_workflow(file_id)
    if error:
        return None, 0, error
    
    return csv_result, elapsed, None


# ============================================
# UI構築
# ============================================
st.title("🐼 RAKUPANDA AI-OCR トード様向け")
st.caption("付箋OCR → 編集 → CSV確定")

# APIキー未設定チェック
if not API_KEY:
    st.error("""
    ⚠️ APIキーが設定されていません。
    
    **ローカル開発の場合:**
    `.streamlit/secrets.toml` ファイルを作成し、以下を記述してください：
    ```
    DIFY_API_KEY = "app-XXXXXXXXXXXXXXXXXXXXXXXX"
    ```
    
    **Streamlit Cloud の場合:**
    アプリ設定の Secrets 欄に同じ内容を記述してください。
    """)
    st.stop()

# サイドバー
with st.sidebar:
    st.header("使い方")
    st.markdown("""
    1. PDFファイルを複数選択
    2. 「処理開始」ボタンをクリック
    3. 完了したタブで結果を確認
    4. **セルをダブルクリックして編集**
    5. 「確定」ボタンでCSV出力
    """)
    st.divider()
    st.caption("v0.4 - クラウドデプロイ対応")
    
    if st.button("🔄 リセット", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith('editor_') or key.startswith('confirmed_'):
                del st.session_state[key]
        st.session_state.files_data = {}
        st.session_state.processing_started = False
        st.session_state.all_completed = False
        st.rerun()


# ============================================
# ステップ 1: PDFアップロード
# ============================================
st.header("ステップ 1: PDFアップロード")

uploaded_files = st.file_uploader(
    "発注書PDFを選択してください（複数選択可）",
    type=['pdf'],
    accept_multiple_files=True,
    help="トード様の発注書PDFを複数選択できます",
    disabled=st.session_state.processing_started
)

if uploaded_files and not st.session_state.processing_started:
    st.success(f"✅ {len(uploaded_files)}件のファイルが選択されました")
    
    estimated_total = len(uploaded_files) * ESTIMATED_SECONDS_PER_FILE
    estimated_min = estimated_total // 60
    estimated_sec = estimated_total % 60
    st.info(f"⏱️ 想定処理時間: 約 {estimated_min}分{estimated_sec}秒")
    
    with st.expander("📋 ファイル一覧"):
        for i, f in enumerate(uploaded_files, 1):
            st.markdown(f"{i}. **{f.name}** ({f.size:,} バイト)")


# ============================================
# ステップ 2: 処理実行
# ============================================
if uploaded_files and not st.session_state.processing_started:
    st.divider()
    st.header("ステップ 2: 処理実行")
    
    if st.button("🚀 処理開始", type="primary", use_container_width=True):
        st.session_state.files_data = {
            f.name: {
                'status': 'waiting',
                'csv': None,
                'elapsed': 0,
                'error_msg': None,
                'bytes': f.getvalue(),
                'confirmed': False
            }
            for f in uploaded_files
        }
        st.session_state.processing_started = True
        st.session_state.all_completed = False
        st.rerun()


# ============================================
# 処理ロジック
# ============================================
if st.session_state.processing_started and not st.session_state.all_completed:
    st.divider()
    st.header("⚙️ 処理中...")
    
    progress_container = st.container()
    
    file_names = list(st.session_state.files_data.keys())
    total_files = len(file_names)
    
    next_file = None
    completed_count = 0
    for fname in file_names:
        data = st.session_state.files_data[fname]
        if data['status'] in ('completed', 'error'):
            completed_count += 1
        elif data['status'] == 'waiting':
            next_file = fname
            break
    
    with progress_container:
        progress = completed_count / total_files if total_files > 0 else 0
        st.progress(progress, text=f"進捗: {completed_count} / {total_files} ファイル完了")
        
        if next_file:
            remaining_files = total_files - completed_count
            estimated_remaining = remaining_files * ESTIMATED_SECONDS_PER_FILE
            remaining_min = estimated_remaining // 60
            remaining_sec = estimated_remaining % 60
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"🔄 処理中: **{next_file}**")
            with col2:
                st.info(f"⏱️ 推定残り時間: 約 {remaining_min}分{remaining_sec}秒")
    
    if next_file:
        st.session_state.files_data[next_file]['status'] = 'processing'
        
        file_bytes = st.session_state.files_data[next_file]['bytes']
        csv_result, elapsed, error = process_single_file(next_file, file_bytes)
        
        if error:
            st.session_state.files_data[next_file]['status'] = 'error'
            st.session_state.files_data[next_file]['error_msg'] = error
        else:
            st.session_state.files_data[next_file]['status'] = 'completed'
            st.session_state.files_data[next_file]['csv'] = csv_result
            st.session_state.files_data[next_file]['elapsed'] = elapsed
        
        st.session_state.files_data[next_file].pop('bytes', None)
        
        st.rerun()
    else:
        st.session_state.all_completed = True
        st.rerun()


# ============================================
# ステップ 3: 結果表示＆編集（タブ切替）
# ============================================
if st.session_state.files_data and (st.session_state.processing_started or st.session_state.all_completed):
    st.divider()
    
    if st.session_state.all_completed:
        st.header("✅ ステップ 3: 抽出結果（編集 → 確定）")
    else:
        st.header("📋 ステップ 3: 抽出結果（処理中・完了したものから表示）")
    
    file_names = list(st.session_state.files_data.keys())
    tab_labels = []
    for fname in file_names:
        data = st.session_state.files_data[fname]
        status = data['status']
        
        if status == 'completed':
            if data.get('confirmed'):
                icon = "💾"
            else:
                icon = "✅"
        elif status == 'processing':
            icon = "🔄"
        elif status == 'error':
            icon = "⚠️"
        else:
            icon = "⏳"
        
        display_name = fname if len(fname) <= 20 else fname[:17] + "..."
        tab_labels.append(f"{icon} {display_name}")
    
    tabs = st.tabs(tab_labels)
    
    for tab, fname in zip(tabs, file_names):
        with tab:
            data = st.session_state.files_data[fname]
            status = data['status']
            
            st.subheader(f"📄 {fname}")
            
            if status == 'waiting':
                st.info("⏳ 処理待ち...")
            
            elif status == 'processing':
                st.warning("🔄 処理中... しばらくお待ちください")
            
            elif status == 'error':
                st.error("❌ エラー発生")
                st.code(data['error_msg'])
            
            elif status == 'completed':
                csv_result = data['csv']
                elapsed = data['elapsed']
                
                try:
                    df = pd.read_csv(StringIO(csv_result))
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if data.get('confirmed'):
                            st.success(f"💾 確定済み（{len(df)}件の明細）処理時間: {elapsed:.1f}秒")
                        else:
                            st.info(f"📝 {len(df)}件の明細を抽出（編集可能） 処理時間: {elapsed:.1f}秒")
                    
                    with col2:
                        st.caption("💡 セルをダブルクリックで編集")
                    
                    editor_key = f"editor_{fname}"
                    
                    edited_df = st.data_editor(
                        df,
                        use_container_width=True,
                        num_rows="dynamic",
                        hide_index=True,
                        key=editor_key,
                        disabled=data.get('confirmed', False)
                    )
                    
                    st.divider()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if not data.get('confirmed'):
                            if st.button(
                                "✅ 確定してCSV出力",
                                type="primary",
                                use_container_width=True,
                                key=f"confirm_{fname}"
                            ):
                                edited_csv = edited_df.to_csv(index=False)
                                st.session_state.files_data[fname]['csv'] = edited_csv
                                st.session_state.files_data[fname]['confirmed'] = True
                                st.rerun()
                        else:
                            if st.button(
                                "🔓 編集に戻す",
                                use_container_width=True,
                                key=f"unconfirm_{fname}"
                            ):
                                st.session_state.files_data[fname]['confirmed'] = False
                                st.rerun()
                    
                    with col2:
                        if data.get('confirmed'):
                            st.download_button(
                                label="📥 確定CSVをダウンロード",
                                data=data['csv'],
                                file_name=f"{fname.replace('.pdf', '')}_confirmed.csv",
                                mime="text/csv",
                                type="primary",
                                use_container_width=True,
                                key=f"download_{fname}"
                            )
                        else:
                            st.button(
                                "📥 CSV確定後にダウンロード可能",
                                disabled=True,
                                use_container_width=True,
                                key=f"download_disabled_{fname}"
                            )
                    
                    with st.expander("🔍 現在のCSVデータを見る"):
                        if data.get('confirmed'):
                            st.code(data['csv'], language="csv")
                        else:
                            st.code(edited_df.to_csv(index=False), language="csv")
                
                except Exception as e:
                    st.warning(f"CSV形式の解析に失敗: {str(e)}")
                    st.code(csv_result)
    
    if st.session_state.all_completed:
        st.divider()
        st.header("📊 サマリー")
        
        total = len(file_names)
        completed = sum(1 for d in st.session_state.files_data.values() if d['status'] == 'completed')
        confirmed = sum(1 for d in st.session_state.files_data.values() if d.get('confirmed'))
        errors = sum(1 for d in st.session_state.files_data.values() if d['status'] == 'error')
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("総ファイル数", total)
        with col2:
            st.metric("抽出成功", completed)
        with col3:
            st.metric("確定済み", confirmed, delta=f"残り{completed - confirmed}件" if completed > confirmed else None)
        with col4:
            st.metric("エラー", errors)
        
        if confirmed == completed and completed > 0:
            st.success(f"🎉 全{confirmed}件の確定が完了しました！各タブからCSVをダウンロードしてください。")
