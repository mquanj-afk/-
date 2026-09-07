import os
import base64
import urllib.parse
from datetime import datetime
import streamlit as st
import google.generativeai as genai
from PIL import Image
from supabase import create_client, Client

# 1. 画面の初期設定
st.set_page_config(page_title="AI食事・健康管理アドバイザー", page_icon="🥗", layout="wide")
st.title("🥗 AI食事・健康管理アドバイザー (ログイン・自動入力機能付き)")

# --- 🔐 SUPABASEの設定（※あなたURLとKEYをここに貼り付けてください） ---
SUPABASE_URL = "https://teams.live.com/l/message/48:notes/1788756892679?context=%7B%22contextType%22%3A%22chat%22%2C%22oid%22%3A%228%3Alive%3Amquanj%22%7D"
SUPABASE_KEY = "sb_publishable_Xkz0kpAT_oyF_a1qNkA9PA_TuXsQy-s"

# Supabaseクライアントの初期化
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = get_supabase()
except Exception as e:
    st.error("Supabaseの初期設定エラーです。URLとKEYを確認してください。")

# セッション状態の初期化
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "profile" not in st.session_state:
    st.session_state["profile"] = {"age": 30, "gender": "男性", "height": 170.0, "weight": 65.0, "has_illness": "なし", "illness_detail": "", "purpose": "現状維持"}

# --- 🔐 ログイン・会員登録システム ---
st.sidebar.header("🔑 アカウント")

if st.session_state["user_id"] is None:
    auth_action = st.sidebar.radio("メニュー", ["ログイン", "新規会員登録"])
    email = st.sidebar.text_input("メールアドレス")
    password = st.sidebar.text_input("パスワード", type="password")
    
    if auth_action == "新規会員登録":
        if st.sidebar.button("アカウントを作成する"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                if res.user:
                    st.sidebar.success("登録完了！ログインメニューに切り替えてログインしてください。")
            except Exception as e:
                st.sidebar.error(f"登録エラー: {e}")
                
    elif auth_action == "ログイン":
        if st.sidebar.button("ログインする"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if res.user:
                    st.session_state["user_id"] = res.user.id
                    st.sidebar.success("ログイン成功！")
                    
                    # 金庫からプロフィールを自動読み込み
                    try:
                        profile_res = supabase.table("profiles").select("*").eq("id", res.user.id).execute()
                        if profile_res.data:
                            st.session_state["profile"] = profile_res.data[0]
                    except:
                        pass
                    st.rerun()
            except Exception as e:
                st.sidebar.error("ログインに失敗しました。アドレスかパスワードが違います。")
else:
    st.sidebar.success(f"ログイン中")
    if st.sidebar.button("ログアウト"):
        st.session_state["user_id"] = None
        st.session_state["profile"] = {"age": 30, "gender": "男性", "height": 170.0, "weight": 65.0, "has_illness": "なし", "illness_detail": "", "purpose": "現状維持"}
        st.rerun()

# --- 👤 プロフィール入力欄 ---
st.sidebar.header("👤 利用者プロフィール")
p = st.session_state["profile"]

age = st.sidebar.number_input("年齢", min_value=1, max_value=120, value=int(p.get("age", 30)))
gender = st.sidebar.selectbox("性別", ["男性", "女性", "その他"], index=["男性", "女性", "その他"].index(p.get("gender", "男性")))
height = st.sidebar.number_input("身長 (cm)", min_value=50.0, max_value=250.0, value=float(p.get("height", 170.0)), step=0.1)
weight = st.sidebar.number_input("体重 (kg)", min_value=10.0, max_value=300.0, value=float(p.get("weight", 65.0)), step=0.1)

has_illness = st.sidebar.radio("持病・病気の有無", ["なし", "あり"], index=["なし", "あり"].index(p.get("has_illness", "なし")))
illness_detail = p.get("illness_detail", "")
if has_illness == "あり":
    illness_detail = st.sidebar.text_input("具体的な病名や制限項目", value=p.get("illness_detail", ""))

purpose = st.sidebar.selectbox("目的", ["ダイエット（減量）", "現状維持", "バルクアップ（筋肥大）"], index=["ダイエット（減量）", "現状維持", "バルクアップ（筋肥大）"].index(p.get("purpose", "現状維持")))

# プロフィールの手動保存更新ボタン
if st.session_state["user_id"] is not None:
    if st.sidebar.button("💾 このプロフィールで金庫を更新"):
        updated_profile = {
            "id": st.session_state["user_id"], "age": age, "gender": gender, 
            "height": height, "weight": weight, "has_illness": has_illness, 
            "illness_detail": illness_detail, "purpose": purpose
        }
        try:
            supabase.table("profiles").upsert(updated_profile).execute()
            st.session_state["profile"] = updated_profile
            st.sidebar.success("金庫のデータを最新に更新しました！")
        except Exception as e:
            st.sidebar.error(f"保存失敗: {e}")

# Gemini APIキーの設定
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
                        # 【完全修正】ここを確実に2026年最新推奨モデルに書き換えました
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
                # 【完全修正】チャット質問用のモデルも最新に統一しました
                model = genai.GenerativeModel('gemini-3.6-flash')
                chat_prompt = f"分析：\n{st.session_state['current_result']}\n\n質問：\n{user_question}"
                response = model.generate_content(chat_prompt)
                st.info("💡 AIからの回答：")
                st.markdown(response.text)
                
        st.markdown("---")
        st.subheader("🛒 不足栄養素をAmazonで補給する")
        search_keyword = st.text_input("購入・検索したい健康食材", value="プロテイン")
        YOUR_ASSOCIATE_ID = "your_id-22" 
        encoded_keyword = urllib.parse.quote(search_keyword)
        amazon_url = f"https://amazon.co.jp{encoded_keyword}&tag={YOUR_ASSOCIATE_ID}"
        st.link_button(f"👉 Amazonで「{search_keyword}」をチェック", amazon_url, use_container_width=True)
    else:
        st.info("食事の分析を完了すると、ここに専用チャットとAmazonアフィリエイトリンクが出現します。")

# 5. 📜 Amazon審査合格用のプライバシーポリシー（画面一番下）
st.markdown("---")
with st.expander("📜 本アプリの規約・プライバシーポリシー（Amazonアソシエイト・個人情報保護適応版）"):
    st.caption("""
    **【Amazonアソシエイト・プログラムについて】**
    当アプリは、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムである、Amazonアソシエイト・プログラムの参加者です。
    
    **【個人情報の取り扱いとログイン情報について】**
    ・当アプリは、ユーザー登録時に入力されたメールアドレスおよび暗号化されたパスワード、健康プロフィール情報を、世界基準のセキュリティを誇るSupabase（米国ベンダ）を介して安全に保護・保存しています。
    ・ユーザーがアップロードした食事画像は、AI分析時のみ一時的に利用され、サーバー側や外部に無断で永続保存されることは一切ありません。
    """)
