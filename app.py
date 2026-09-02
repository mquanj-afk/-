import os
import base64
import pandas as pd
from io import BytesIO
from datetime import datetime
import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 画面の初期設定
st.set_page_config(page_title="AI食事・健康アドバイザー", page_icon="🥗", layout="wide")
st.title("🥗 AI食事・健康アドバイザー (チャット質問機能付き)")

# 履歴を保存するファイルの作成（アドバイス本文も保存するように拡張）
HISTORY_FILE = "diet_history.csv"
if not os.path.exists(HISTORY_FILE):
    df = pd.DataFrame(columns=["日時", "メニュー名", "カロリー", "詳細アドバイス"])
    df.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")

# 2. ユーザー情報の入力（サイドバー）
st.sidebar.header("👤 利用者プロフィール")
age = st.sidebar.number_input("年齢", min_value=1, max_value=120, value=30)
gender = st.sidebar.selectbox("性別", ["男性", "女性", "その他"])
height = st.sidebar.number_input("身長 (cm)", min_value=50.0, max_value=250.0, value=170.0, step=0.1)
weight = st.sidebar.number_input("体重 (kg)", min_value=10.0, max_value=300.0, value=65.0, step=0.1)

has_illness = st.sidebar.radio("持病・病気の有無", ["なし", "あり"])
illness_detail = ""
if has_illness == "あり":
    illness_detail = st.sidebar.text_input("具体的な病名や制限項目")

purpose = st.sidebar.selectbox("目的", ["ダイエット（減量）", "現状維持", "バルクアップ（筋肥大）"])

# Gemini APIキーの設定
api_key = st.sidebar.text_input("Gemini API Keyを入力してください", type="password")

# 3. 画面を2分割
col1, col2 = st.columns(2)

with col1:
    st.header("📸 今日の食事を分析")
    uploaded_file = st.file_uploader("食事の写真をアップロードしてください...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="アップロードされた食事", use_container_width=True)
        
        if st.button("エネルギー・栄養素を計算する"):
            if not api_key:
                st.error("APIキーが入力されていません。サイドバーから入力してください。")
            else:
                with st.spinner("Gemini AIが最新モデルで分析中..."):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-3.6-flash')
                        
                        illness_prompt = "特になし" if has_illness == "なし" else f"持病・制限：{illness_detail}。塩分や糖質など制限すべき栄養素があれば厳しくチェックしてください。"

                        prompt = f"""
                        あなたはプロの管理栄養士です。提供された食事画像と健康データを元に解析してください。
                        
                        【利用者の健康データ】
                        - 年齢: {age}歳 / 性別: {gender}
                        - 身長: {height} cm / 体重: {weight} kg
                        - 目的: {purpose}
                        - 持病・制限事項: {illness_prompt}
                        
                        【出力フォーマット】
                        ### 📊 栄養・カロリー計算結果
                        - **メニュー名**:（推測される料理名。必ず1つだけ簡潔に）
                        - **総カロリー**: 〇〇 kcal（※必ず「〇〇 kcal」の形式で）
                        - **タンパク質**: 〇g
                        - **脂質**: 〇g
                        - **炭水化物**: 〇g
                        
                        ### 📝 あなたの健康状態に合わせたフィードバック
                        （BMIや持病を考慮してコメント）
                        
                        ### ⏰ 次の食事の提案
                        - **食べるタイミング**:（〇時間後、または〇時頃）
                        - **おすすめのメニュー**:（次に食べるべき具体的なメニュー）
                        """
                        
                        response = model.generate_content([prompt, image])
                        result_text = response.text
                        
                        # 最新の分析結果を一時的にセッションに保存
                        st.session_state["current_result"] = result_text
                        
                        # データの抽出と保存（詳細アドバイスを丸ごとCSVに保存）
                        menu_name = "不明な料理"
                        calories = "0 kcal"
                        for line in result_text.split("\n"):
                            if "メニュー名" in line:
                                menu_name = line.split(":")[-1].strip().replace("**", "")
                            if "総カロリー" in line:
                                calories = line.split(":")[-1].strip().replace("**", "")

                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        new_data = pd.DataFrame([[now, menu_name, calories, result_text]], columns=["日時", "メニュー名", "カロリー", "詳細アドバイス"])
                        df_history = pd.read_csv(HISTORY_FILE, encoding="utf-8-sig")
                        df_history = pd.concat([new_data, df_history], ignore_index=True)
                        df_history.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")

    # 今日の分析結果の表示
    if "current_result" in st.session_state:
        st.success("分析完了！")
        st.markdown(st.session_state["current_result"])

# 4. 右側に履歴と質問機能を表示
with col2:
    st.header("🗂️ 過去の食事履歴")
    df_history = pd.read_csv(HISTORY_FILE, encoding="utf-8-sig")
    
    if df_history.empty:
        st.info("まだ履歴はありません。")
    else:
        # 画面をスッキリさせるため、詳細アドバイスを隠した表を表示
        df_display = df_history[["日時", "メニュー名", "カロリー"]]
        
        # ユーザーが選べるようにセレクトボックスを作成
        history_options = [f"{row['日時']} - {row['メニュー名']}" for idx, row in df_history.iterrows()]
        selected_index = st.selectbox("詳しく見たい過去の食事を選択してください：", range(len(history_options)), format_func=lambda x: history_options[x])
        
        # 選択された過去のアドバイスを取得
        selected_advice = df_history.iloc[selected_index]["詳細アドバイス"]
        selected_menu = df_history.iloc[selected_index]["メニュー名"]
        
        # 選択された過去のアドバイスを表示するエリア
        st.markdown("---")
        st.subheader(f"📄 {df_history.iloc[selected_index]['メニュー名']} のアドバイス詳細")
        st.markdown(selected_advice)
        
        # 💬 質問機能（チャット）の追加
        st.markdown("---")
        st.subheader("💬 この食事についてAIに質問する")
        user_question = st.text_input("例：もっと低カロリーにするための代替食材は？、他に足りない栄養素は？")
        
        if st.button("AIに質問を送信"):
            if not api_key:
                st.error("APIキーを入力してください。")
            elif not user_question:
                st.warning("質問内容を入力してください。")
            else:
                with st.spinner("AIが回答を考えています..."):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-3.6-flash')
                        
                        # 過去のアドバイス文脈を引き継いで質問するプロンプト
                        chat_prompt = f"""
                        あなたはプロの管理栄養士です。先ほど利用者へ行った以下の食事分析をベースにして、利用者の質問に親身に答えてください。
                        
                        【これまでの食事分析】
                        {selected_advice}
                        
                        【利用者からの追加の質問】
                        {user_question}
                        """
                        response = model.generate_content(chat_prompt)
                        
                        # 質問の回答を表示
                        st.info("💡 AIからの回答：")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")
        
        st.markdown("---")
        if st.button("履歴をすべて削除"):
            df_empty = pd.DataFrame(columns=["日時", "メニュー名", "カロリー", "詳細アドバイス"])
            df_empty.to_csv(HISTORY_FILE, index=False, encoding="utf-8-sig")
            if "current_result" in st.session_state:
                del st.session_state["current_result"]
            st.rerun()
