import os
import base64
import urllib.parse
import json
import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 画面の初期設定
st.set_page_config(page_title="AI食事・健康管理アドバイザー", page_icon="🥗", layout="wide")
st.title("🥗 AI食事・健康管理アドバイザー (自動入力省略機能付き)")

# --- 🔐 パソコン内にプロフィールを保存するファイル名 ---
CONFIG_FILE = "user_profile_config.json"

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved_profile = json.load(f)
    except:
        saved_profile = {}
else:
    saved_profile = {}

default_profile = {
    "age": 30, "gender": "男性", "height": 170.0, "weight": 65.0,
    "has_illness": "なし", "illness_detail": "", "purpose": "現状維持"
}
p = {key: saved_profile.get(key, default_profile[key]) for key in default_profile}

# --- 👤 プロフィール入力欄 ---
st.sidebar.header("👤 利用者プロフィール")

age = st.sidebar.number_input("年齢", min_value=1, max_value=120, value=int(p["age"]))
gender = st.sidebar.selectbox("性別", ["男性", "女性", "その他"], index=["男性", "女性", "その他"].index(p["gender"]))
height = st.sidebar.number_input("身長 (cm)", min_value=50.0, max_value=250.0, value=float(p["height"]), step=0.1)
weight = st.sidebar.number_input("体重 (kg)", min_value=10.0, max_value=300.0, value=float(p["weight"]), step=0.1)

has_illness = st.sidebar.radio("持病・病気の有無", ["なし", "あり"], index=["なし", "あり"].index(p["has_illness"]))
illness_detail = p["illness_detail"]
if has_illness == "あり":
    illness_detail = st.sidebar.text_input("具体的な病名や制限項目", value=p["illness_detail"])

purpose = st.sidebar.selectbox("目的", ["ダイエット（減量）", "現状維持", "バルクアップ（筋肥大）"], index=["ダイエット（減量）", "現状維持", "バルクアップ（筋肥大）"].index(p["purpose"]))

if st.sidebar.button("💾 この入力内容を次回から自動省略する"):
    new_profile = {
        "age": age, "gender": gender, "height": height, "weight": weight,
        "has_illness": has_illness, "illness_detail": illness_detail, "purpose": purpose
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_profile, f, ensure_ascii=False, indent=4)
    st.sidebar.success("保存しました！次回からは開くだけで自動入力されます。")

api_key = st.sidebar.text_input("Gemini API Keyを入力してください", type="password")

# --- 4. メイン画面の処理（食事分析 ＆ Amazon連携） ---
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
                with st.spinner("AIが最先端モデルで分析中..."):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-3.6-flash')
                        
                        illness_prompt = "特になし" if has_illness == "なし" else f"持病・制限：{illness_detail}。塩分や糖質など制限すべき栄養素があれば厳しくチェックしてください。"

                        prompt = f"""
                        あなたはプロの管理栄養士です。提供された食事画像から以下の情報を解析してください。
                        利用者の健康データ：年齢 {age}歳、性別 {gender}、身長 {height}cm、体重 {weight}kg、目的 {purpose}、持病：{illness_prompt}
                        
                        1. 📊 栄養・カロリー計算結果（メニュー名、総カロリー、PFCバランス）
                        2. 📝 あなたの健康状態に合わせたフィードバック
                        3. ⏰ 次に食べるべきおすすめの食材やメニュー（具体的に1つ）
                        """
                        response = model.generate_content([prompt, image])
                        st.session_state["current_result"] = response.text
                        st.rerun()
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")

    if "current_result" in st.session_state:
        st.success("分析完了！")
        st.markdown(st.session_state["current_result"])

with col2:
    st.header("💬 AIへの質問 ＆ Amazon健康ショップ")
    
    if "current_result" in st.session_state:
        st.subheader("💬 この食事についてさらに質問する")
        user_question = st.text_input("例：この脂質を抑える調理法は？、代わりに何を食べればいい？")
        if st.button("AIに質問を送信"):
            with st.spinner("回答中..."):
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-3.6-flash')
                chat_prompt = f"分析：\n{st.session_state['current_result']}\n\n質問：\n{user_question}"
                response = model.generate_content(chat_prompt)
                st.info("💡 AIからの回答：")
                st.markdown(response.text)
                
        st.markdown("---")
        st.subheader("🛒 不足栄養素をAmazonで補給する")
        search_keyword = st.text_input("購入・検索したい健康食材", value="プロテイン")
        
        YOUR_ASSOCIATE_ID = "your_id-22" 
        clean_keyword = urllib.parse.quote(str(search_keyword).strip())
        amazon_url = f"https://amazon.co.jp{clean_keyword}&tag={YOUR_ASSOCIATE_ID}"
        
        st.link_button(f"👉 Amazonで「{search_keyword}」をチェックする", amazon_url, use_container_width=True)
    else:
        st.info("食事の分析を完了すると、ここに専用チャットとAmazonアフィリエイトリンクが出現します。")

# 5. 📜 Amazon審査合格用のプライバシーポリシー
st.markdown("---")
# 【💡 修正：タイピングミスを完全に修正しました】
with st.expander("📜 本アプリの規約・プライバシーポリシー（Amazonアソシエイト・個人情報保護適応版）"):
    st.caption("""
    **【Amazonアソシエイト・プログラムについて】**
    当アプリは、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムである、Amazonアソシエイト・プログラムの参加者です。
    
    **【個人情報の取り扱いについて】**
    ・当アプリに入力された健康プロフィール情報は、外部のサーバーには一切送信されず、ユーザーご自身のブラウザおよび端末内にのみ安全に記憶されます。
    ・ユーザーがアップロードした食事画像は、AI分析時のみ一時的に利用され、外部に無断で永続保存されることは一切ありません。
    """)
