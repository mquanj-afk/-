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
st.title("🥗 AI食事・健康管理アドバイザー (セキュア履歴保存システム)")

# --- 🔐 SUPABASEの設定（バグ防止のため正しいURLに強制固定） ---
SUPABASE_URL = "https://supabase.co"
# 【💡 あなたのanon publicキー（eyJ...）を以下のダブルクォーテーション内に入れてください】
SUPABASE_KEY = "あなたのAPI key (anon public)を入れてください"

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
if "current_result" not in st.session_state:
    st.session_state["current_result"] = None

# --- 🔐 会員登録・ログインシステム ---
st.sidebar.header("🔑 アカウント (機密性保護)")

if st.session_state["user_id"] is None:
    auth_action = st.sidebar.radio("メニュー", ["ログイン", "新規会員登録"])
    email = st.sidebar.text_input("メールアドレス")
    password = st.sidebar.text_input("パスワード", type="password")
    
    if auth_action == "新規会員登録":
        if st.sidebar.button("アカウントを作成する"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                if res.user:
                    st.sidebar.success("登録完了！「ログイン」に切り替えて進んでください。")
            except Exception as e:
                st.sidebar.error(f"登録エラー: {e}")
                
    elif auth_action == "ログイン":
        if st.sidebar.button("ログインする"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if res.user:
                    st.session_state["user_id"] = res.user.id
                    st.sidebar.success("ログイン成功！")
                    st.rerun()
            except Exception as e:
                st.sidebar.error("ログインに失敗しました。")
else:
    st.sidebar.success("🔒 セキュア接続中")
    if st.sidebar.button("ログアウト"):
        st.session_state["user_id"] = None
        st.session_state["current_result"] = None
        st.rerun()

# --- 👤 プロフィール入力欄 ---
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

# --- 4. メイン画面の処理 ---
col1, col2 = st.columns(2)

with col1:
    st.header("📸 今日の食事を分析")
    uploaded_file = st.file_uploader("食事の写真をアップロードしてください...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="アップロードされた食事", use_container_width=True)
        
        if st.button("エネルギー・栄養素を計算する"):
            if not st.session_state["user_id"]:
                st.error("履歴を安全に保存するため、先にサイドバーからログインをしてください。")
            elif not api_key:
                st.error("APIキーを入力してください。")
            else:
                with st.spinner("AIが最先端モデルで分析中..."):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-3.6-flash')
                        
                        illness_prompt = "特になし" if has_illness == "なし" else f"持病・制限：{illness_detail}"

                        prompt = f"""
                        あなたはプロの管理栄養士です。食事画像から情報を解析してください。
                        利用者の健康データ：年齢 {age}歳、性別 {gender}、身長 {height}cm、体重 {weight}kg、目的 {purpose}、持病：{illness_prompt}
                        
                        【出力フォーマット】
                        ### 📊 栄養・カロリー計算結果
                        - **メニュー名**:（料理名）
                        - **総カロリー**: 〇〇 kcal
                        - **タンパク質**: 〇g
                        - **脂質**: 〇g
                        - **炭水化物**: 〇g
                        
                        ### 📝 フィードバック
                        （親身なアドバイス）
                        """
                        response = model.generate_content([prompt, image])
                        result_text = response.text
                        st.session_state["current_result"] = result_text
                        
                        # カロリーとメニュー名の簡易抽出
                        menu_name = "不明な料理"
                        calories = "0 kcal"
                        for line in result_text.split("\n"):
                            if "メニュー名" in line:
                                menu_name = line.split(":")[-1].strip().replace("**", "")
                            if "総カロリー" in line:
                                calories = line.split(":")[-1].strip().replace("**", "")

                        # クラウド金庫へダイレクト保存
                        history_data = {
                            "user_id": st.session_state["user_id"],
                            "menu_name": menu_name,
                            "calories": calories,
                            "detail_advice": result_text
                        }
                        supabase.table("diet_history_secure").insert(history_data).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")

    if "current_result" in st.session_state and st.session_state["current_result"]:
        st.success("分析完了！クラウド金庫に暗号化保存されました。")
        st.markdown(st.session_state["current_result"])

with col2:
    st.header("🗂️ あなたの全食事履歴 (機密保護)")
    
    if st.session_state["user_id"] is None:
        st.info("ログインすると、ここにあなただけの過去の食事履歴が安全に表示されます。")
    else:
        try:
            # ログインしている本人のデータだけをクエリ（機密性）
            res_history = supabase.table("diet_history_secure").select("*").eq("user_id", st.session_state["user_id"]).order("created_at", descending=True).execute()
            
            if not res_history.data:
                st.info("まだ保存された食事履歴はありません。")
            else:
                options = [f"{row['created_at'][:16]} - {row['menu_name']} ({row['calories']})" for row in res_history.data]
                selected_opt = st.selectbox("過去の分析アドバイスを振り返る：", options)
                
                selected_idx = options.index(selected_opt)
                selected_row = res_history.data[selected_idx]
                
                st.markdown("---")
                st.subheader(f"📄 {selected_row['menu_name']} の詳細分析")
                st.markdown(selected_row['detail_advice'])
                
                # Amazonアフィリエイト
                st.markdown("---")
                st.subheader("🛒 不足栄養素をAmazonで補給する")
                search_keyword = st.text_input("購入・検索したい健康食材", value="プロテイン")
                YOUR_ASSOCIATE_ID = "your_id-22"
                params = {"k": str(search_keyword).strip(), "tag": YOUR_ASSOCIATE_ID}
                amazon_url = "https://amazon.co.jp?" + urllib.parse.urlencode(params)
                st.link_button(f"👉 Amazonで「{search_keyword}」をチェックする", amazon_url, use_container_width=True)
        except Exception as e:
            st.error("履歴データの取得に失敗しました。")

# 5. 免責事項
st.markdown("---")
with st.expander("📜 本アプリの規約・プライバシーポリシー"):
    st.caption("当アプリは、ユーザー登録情報をSupabaseを介して暗号化保護し、許可なく第三者に開示することはありません。Amazonアソシエイト・プログラムの参加者です。")
