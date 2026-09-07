import os
import base64
import urllib.parse
import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. 画面の初期設定
st.set_page_config(page_title="AI食事アドバイザー", page_icon="🥗", layout="centered")
st.title("🥗 AI食事・健康アドバイザー (Amazonアフィリエイト対応)")
st.write("食事の写真を送ると、カロリー計算と健康に良いおすすめ食材を提案します。")

# 2. 利用者プロフィール（サイドバー）
st.sidebar.header("👤 利用者プロフィール")
age = st.sidebar.number_input("年齢", min_value=1, max_value=120, value=30)
gender = st.sidebar.selectbox("性別", ["男性", "女性", "その他"])
height = st.sidebar.number_input("身長 (cm)", min_value=50.0, max_value=250.0, value=170.0)
weight = st.sidebar.number_input("体重 (kg)", min_value=10.0, max_value=300.0, value=65.0)
purpose = st.sidebar.selectbox("目的", ["ダイエット", "現状維持", "バルクアップ（筋肥大）"])

# Gemini APIキーの入力欄
api_key = st.sidebar.text_input("Gemini API Keyを入力してください", type="password")

# 3. メイン画面：写真のアップロード
uploaded_file = st.file_uploader("食事の写真をアップロードしてください...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた食事", use_container_width=True)
    
    if st.button("エネルギー・栄養素を計算する"):
        if not api_key:
            st.error("APIキーが入力されていません。サイドバーから入力してください。")
        else:
            with st.spinner("AIが食事を分析中..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-3.6-flash')
                    
                    prompt = f"""
                    あなたはプロの管理栄養士です。提供された食事画像から以下の情報を解析してください。
                    利用者の健康データ：年齢 {age}歳、性別 {gender}、身長 {height}cm、体重 {weight}kg、目的 {purpose}
                    
                    以下の項目で親身にアドバイスを書いてください。
                    1. 📊 栄養・カロリー計算結果（メニュー名、総カロリー、PFCバランス）
                    2. 📝 あなたの健康状態に合わせたフィードバック
                    3. ⏰ 次に食べるべきおすすめの食材やメニュー（具体的に1つ）
                    """
                    
                    response = model.generate_content([prompt, image])
                    result_text = response.text
                    
                    st.success("分析が完了しました！")
                    st.markdown(result_text)
                    st.session_state["last_analysis"] = result_text
                    
                except Exception as e:
                    st.error(f"エラーが発生しました。APIキーまたは写真を確認してください: {e}")

# 4. 💰 Amazonアフィリエイト広告セクション（分析後に表示）
if "last_analysis" in st.session_state:
    st.markdown("---")
    st.header("🛒 不足栄養素をAmazonで補給する")
    st.write("AIのアドバイスを元に、健康維持に役立つ食材やサプリメントをAmazonで探せます。")
    
    search_keyword = st.text_input("購入・検索したい健康食材（例：プロテイン、サバ缶、特茶など）", value="プロテイン")
    
    # 【ここに取得したあなたのアソシエイトIDを入れてください】
    YOUR_ASSOCIATE_ID = "your_id-22" 
    
    encoded_keyword = urllib.parse.quote(search_keyword)
    amazon_url = f"https://amazon.co.jp{encoded_keyword}&tag={YOUR_ASSOCIATE_ID}"
    
    st.link_button(f"👉 Amazonで「{search_keyword}」をチェックする", amazon_url, use_container_width=True)

# 5. 📜 Amazon審査合格用：免責事項とプライバシーポリシーの自動表示
st.markdown("---")
with st.expander("📜 本アプリの規約・プライバシーポリシー（Amazonアソシエイト適応版）"):
    st.caption("""
    **【Amazonアソシエイト・プログラムについて】**
    当アプリ（AI食事・健康アドバイザー）は、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムである、Amazonアソシエイト・プログラムの参加者です。
    
    **【個人情報の取り扱い（プライバシーポリシー）】**
    ・当アプリは、ユーザーがアップロードした食事画像および入力されたプロフィール情報を、Gemini APIを利用したAI分析以外の目的で使用・保存することはありません。
    ・データの提供はユーザーの同意のもとで行われ、第三者に開示・譲渡されることはありません。
    """)
