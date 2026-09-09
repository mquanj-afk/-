import os
import re
import urllib.parse
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import google.generativeai as genai
from PIL import Image
from supabase import create_client, Client

# =========================================================
# 1. 画面の初期設定
# =========================================================
st.set_page_config(page_title="AI食事・健康管理アドバイザー", page_icon="🥗", layout="wide")
st.title("🥗 AI食事・健康管理アドバイザー (ダッシュボード搭載版)")
st.info(
    "⚠️ 本アプリはAIによる簡易的な栄養アドバイスを提供するもので、医療的な診断・治療の代わりにはなりません。"
    "持病がある方や体調に不安がある方は、必ず医師・管理栄養士にご相談のうえご利用ください。"
)

# --- 🔐 SUPABASEの設定 ---
# ⚠️ セキュリティ改善: コード直書きをやめ、Streamlit Secrets から読み込む方式に変更。
# .streamlit/secrets.toml (ローカル) または Streamlit Cloud の Secrets 管理画面に、
# 以下の形式で登録してください:
#
# SUPABASE_URL = "https://xxxx.supabase.co"
# SUPABASE_KEY = "sb_publishable_xxxx"
# GEMINI_API_KEY = "AIza..."   # 任意。未設定ならサイドバーで都度入力できます。
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.sidebar.warning("⚠️ Secretsが未設定です。下に直接入力してください(本番運用ではsecrets.tomlを使用推奨)。")
    SUPABASE_URL = st.sidebar.text_input("Supabase URL", value="")
    SUPABASE_KEY = st.sidebar.text_input("Supabase Key", value="", type="password")


@st.cache_resource
def get_supabase(url: str, key: str) -> Client:
    return create_client(url, key)


supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = get_supabase(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        st.error("Supabaseの初期設定エラーです。URLとKeyを確認してください。")

# セッション状態の初期化
for key, default in {
    "user_id": None,
    "current_result": None,
    "current_nutrition": None,
    "profile": None,  # ログイン中ユーザーのプロフィール(Supabaseから読み込んだキャッシュ)
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def load_profile(user_id: str) -> dict:
    """user_profiles テーブルから保存済みプロフィールを取得する。無ければ空dictを返す。"""
    if not supabase or not user_id:
        return {}
    try:
        res = supabase.table("user_profiles").select("*").eq("user_id", user_id).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return {}


def save_profile(user_id: str, profile_data: dict) -> bool:
    """user_profiles テーブルに upsert (無ければ作成、あれば更新)。"""
    if not supabase or not user_id:
        return False
    try:
        payload = {"user_id": user_id, **profile_data}
        supabase.table("user_profiles").upsert(payload, on_conflict="user_id").execute()
        return True
    except Exception as e:
        st.sidebar.error(f"プロフィール保存エラー: {e}")
        return False

# =========================================================
# 2. 🔐 会員登録・ログインシステム
# =========================================================
st.sidebar.header("🔑 アカウント")

if st.session_state["user_id"] is None:
    auth_action = st.sidebar.radio("メニュー", ["ログイン", "新規会員登録"])
    email = st.sidebar.text_input("メールアドレス")
    password = st.sidebar.text_input("パスワード", type="password")

    if auth_action == "新規会員登録":
        if st.sidebar.button("アカウントを作成する"):
            if not supabase:
                st.sidebar.error("Supabaseの設定が未完了です。")
            elif not email.strip() or not password.strip():
                st.sidebar.error("メールアドレスとパスワードを両方正しく入力してください。")
            elif len(password.strip()) < 6:
                st.sidebar.error("パスワードは6文字以上で入力してください。")
            else:
                try:
                    res = supabase.auth.sign_up({"email": email.strip(), "password": password.strip()})
                    if res.user:
                        st.sidebar.success("登録完了！「ログイン」に切り替えてログインしてください。")
                except Exception as e:
                    st.sidebar.error(f"登録エラー: {e}")

    elif auth_action == "ログイン":
        if st.sidebar.button("ログインする"):
            if not supabase:
                st.sidebar.error("Supabaseの設定が未完了です。")
            elif not email.strip() or not password.strip():
                st.sidebar.error("アドレスとパスワードを入力してください。")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password.strip()})
                    if res.user:
                        st.session_state["user_id"] = res.user.id
                        st.session_state["profile"] = load_profile(res.user.id)
                        st.sidebar.success("ログイン成功！")
                        st.rerun()
                except Exception:
                    st.sidebar.error("ログインに失敗しました。")
else:
    st.sidebar.success("🔒 ログイン中")
    if st.sidebar.button("ログアウト"):
        st.session_state["user_id"] = None
        st.session_state["current_result"] = None
        st.session_state["current_nutrition"] = None
        st.session_state["profile"] = None
        st.rerun()

    # ページ再読み込み等でプロフィールがまだキャッシュされていない場合の保険
    if st.session_state["profile"] is None:
        st.session_state["profile"] = load_profile(st.session_state["user_id"])

# =========================================================
# 3. 👤 プロフィール入力欄 (2回目以降は保存済みの内容を自動入力)
# =========================================================
st.sidebar.header("👤 利用者プロフィール")

saved_profile = st.session_state.get("profile") or {}
if saved_profile:
    st.sidebar.caption("✅ 保存済みプロフィールを読み込みました")

gender_options = ["男性", "女性", "その他"]
activity_options = ["低い(デスクワーク中心)", "普通(週2-3回運動)", "高い(毎日運動・肉体労働)"]
illness_options = ["なし", "あり"]
purpose_options = ["ダイエット（減量）", "現状維持", "バルクアップ（筋肥大）"]


def _idx(options, value, fallback=0):
    return options.index(value) if value in options else fallback


age = st.sidebar.number_input(
    "年齢", min_value=1, max_value=120, value=int(saved_profile.get("age", 30))
)
gender = st.sidebar.selectbox(
    "性別", gender_options, index=_idx(gender_options, saved_profile.get("gender"))
)
height = st.sidebar.number_input(
    "身長 (cm)", min_value=50.0, max_value=250.0, value=float(saved_profile.get("height", 170.0)), step=0.1
)
weight = st.sidebar.number_input(
    "体重 (kg)", min_value=10.0, max_value=300.0, value=float(saved_profile.get("weight", 65.0)), step=0.1
)
activity_level = st.sidebar.selectbox(
    "活動レベル",
    activity_options,
    index=_idx(activity_options, saved_profile.get("activity_level"), fallback=1),
)
has_illness = st.sidebar.radio(
    "持病・病気の有無", illness_options, index=_idx(illness_options, saved_profile.get("has_illness"))
)
illness_detail = ""
if has_illness == "あり":
    illness_detail = st.sidebar.text_input(
        "具体的な病名や制限項目", value=saved_profile.get("illness_detail", "")
    )
purpose = st.sidebar.selectbox(
    "目的", purpose_options, index=_idx(purpose_options, saved_profile.get("purpose"))
)

if st.session_state["user_id"]:
    if st.sidebar.button("💾 プロフィールを保存する(次回から自動入力)"):
        new_profile = {
            "age": age,
            "gender": gender,
            "height": height,
            "weight": weight,
            "activity_level": activity_level,
            "has_illness": has_illness,
            "illness_detail": illness_detail,
            "purpose": purpose,
        }
        if save_profile(st.session_state["user_id"], new_profile):
            st.session_state["profile"] = {**new_profile, "user_id": st.session_state["user_id"]}
            st.sidebar.success("プロフィールを保存しました。次回ログイン時から自動入力されます。")

# =========================================================
# 3.5 AI利用: 運営者の共有キー(1日の無料回数あり) + 自分のキー(無制限)
# =========================================================
DAILY_FREE_LIMIT = 5  # 共有キーで1日に無料利用できる回数

SHARED_GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""


def get_today_usage_count(user_id: str) -> int:
    """今日、その user_id が診断に使った回数を diet_history_secure から数える。"""
    if not supabase or not user_id:
        return 0
    today_start = datetime.now().strftime("%Y-%m-%dT00:00:00")
    try:
        res = (
            supabase.table("diet_history_secure")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", today_start)
            .execute()
        )
        return res.count or 0
    except Exception:
        return 0


today_usage = get_today_usage_count(st.session_state["user_id"]) if st.session_state["user_id"] else 0
remaining_free = max(0, DAILY_FREE_LIMIT - today_usage)

with st.sidebar.expander("🔑 自分のGemini API Keyを使う(任意・無制限)", expanded=False):
    st.caption(
        "何も入力しなければ、運営者の共有キーで1日"
        f"{DAILY_FREE_LIMIT}回まで無料でお試しいただけます。"
        "もっと使いたい方だけ、ご自身のAPI Keyを入力してください。"
    )
    user_api_key = st.text_input("Gemini API Key", type="password", key="user_gemini_key")

if user_api_key:
    api_key = user_api_key
    st.sidebar.caption("✅ ご自身のAPI Keyを使用します(無制限)")
elif SHARED_GEMINI_KEY and st.session_state["user_id"]:
    api_key = SHARED_GEMINI_KEY
    st.sidebar.caption(f"🆓 共有キーを使用中(本日の残り: {remaining_free}/{DAILY_FREE_LIMIT}回)")
else:
    api_key = ""


# =========================================================
# 4. 目標カロリーの計算 (ミフリン・セントジョール式)
# =========================================================
def calc_target_calories(age, gender, height, weight, activity_level, purpose):
    if gender == "男性":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    elif gender == "女性":
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 78  # 男女の中間値

    activity_factor = {
        "低い(デスクワーク中心)": 1.375,
        "普通(週2-3回運動)": 1.55,
        "高い(毎日運動・肉体労働)": 1.725,
    }[activity_level]

    tdee = bmr * activity_factor

    if purpose == "ダイエット（減量）":
        return tdee - 500
    elif purpose == "バルクアップ（筋肥大）":
        return tdee + 300
    return tdee


target_calories = calc_target_calories(age, gender, height, weight, activity_level, purpose)
st.sidebar.metric("🎯 推定目標カロリー/日", f"{target_calories:.0f} kcal")


# =========================================================
# 5. AI応答から数値を抽出するヘルパー
# =========================================================
def extract_number(label: str, text: str) -> float:
    match = re.search(rf"{label}[^\d]*([\d]+(?:\.[\d]+)?)", text)
    return float(match.group(1)) if match else 0.0


def extract_menu_name(text: str) -> str:
    match = re.search(r"メニュー名\**[:：]\s*(.+)", text)
    return match.group(1).strip() if match else "不明な料理"


def parse_nutrition(text: str) -> dict:
    return {
        "menu_name": extract_menu_name(text),
        "calories": extract_number("総カロリー", text),
        "protein": extract_number("タンパク質", text),
        "fat": extract_number("脂質", text),
        "carbs": extract_number("炭水化物", text),
    }


def suggest_shopping_keyword(protein_g: float, fat_g: float, carbs_g: float) -> str:
    """今日のPFCバランスから、不足していそうな栄養素にあわせた検索キーワードを提案する。"""
    total_kcal = protein_g * 4 + fat_g * 9 + carbs_g * 4
    if total_kcal <= 0:
        return "マルチビタミン"

    protein_ratio = (protein_g * 4) / total_kcal
    fat_ratio = (fat_g * 9) / total_kcal
    carbs_ratio = (carbs_g * 4) / total_kcal

    # 一般的な推奨PFCバランス(P:13-20% F:20-30% C:50-65%)を目安に判定
    if protein_ratio < 0.13:
        return "プロテイン"
    if fat_ratio < 0.15:
        return "オメガ3 DHA EPA サプリ"
    if carbs_ratio > 0.70:
        return "食物繊維 サプリ"
    return "マルチビタミン"


def render_shopping_links(default_keyword: str, key_suffix: str):
    """Amazon/楽天市場への検索リンクボタンを描画する(複数タブから呼び出せる共通部品)。"""
    st.markdown("---")
    st.subheader("🛒 不足栄養素を購入する")
    search_keyword = st.text_input(
        "購入・検索したい健康食材", value=default_keyword, key=f"search_kw_{key_suffix}"
    )

    amazon_tag = st.secrets.get("AMAZON_ASSOCIATE_ID", "your_id-22") if hasattr(st, "secrets") else "your_id-22"
    rakuten_id = st.secrets.get("RAKUTEN_AFFILIATE_ID", "") if hasattr(st, "secrets") else ""

    col_amazon, col_rakuten = st.columns(2)

    with col_amazon:
        amazon_params = {"k": str(search_keyword).strip(), "tag": amazon_tag}
        amazon_url = "https://www.amazon.co.jp/s?" + urllib.parse.urlencode(amazon_params)
        st.link_button(
            f"👉 Amazonで「{search_keyword}」を見る",
            amazon_url,
            use_container_width=True,
            key=f"amazon_btn_{key_suffix}",
        )

    with col_rakuten:
        rakuten_search_url = (
            f"https://search.rakuten.co.jp/search/mall/{urllib.parse.quote(str(search_keyword).strip())}/"
        )
        if rakuten_id:
            encoded_target = urllib.parse.quote(rakuten_search_url, safe="")
            rakuten_url = f"https://hb.afl.rakuten.co.jp/hgc/{rakuten_id}/?pc={encoded_target}&m={encoded_target}"
        else:
            # アフィリエイトIDが未設定の場合は通常の検索リンク(成果報酬は発生しません)
            rakuten_url = rakuten_search_url
        st.link_button(
            f"👉 楽天市場で「{search_keyword}」を見る",
            rakuten_url,
            use_container_width=True,
            key=f"rakuten_btn_{key_suffix}",
        )


# =========================================================
# 6. メインタブ
# =========================================================
tab_record, tab_dashboard, tab_history = st.tabs(["📸 食事記録", "📊 ダッシュボード", "🗂️ 履歴・詳細"])

# ---------------------------------------------------------
# タブ1: 食事記録
# ---------------------------------------------------------
with tab_record:
    st.header("今日の食事を分析")
    uploaded_file = st.file_uploader("食事の写真をアップロードしてください...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="アップロードされた食事", use_container_width=True)

        if st.button("エネルギー・栄養素を計算する"):
            if not st.session_state["user_id"]:
                st.error("履歴を保存するため、先にサイドバーからログインをしてください。")
            elif not api_key:
                if SHARED_GEMINI_KEY:
                    st.error("本日の無料利用回数(共有キー)を使い切りました。明日また利用いただくか、サイドバーからご自身のAPI Keyを入力してください。")
                else:
                    st.error("サイドバーの「自分のGemini API Keyを使う」欄にAPI Keyを入力してください。")
            elif not user_api_key and today_usage >= DAILY_FREE_LIMIT:
                st.error("本日の無料利用回数(共有キー)を使い切りました。明日また利用いただくか、サイドバーからご自身のAPI Keyを入力してください。")
            elif not supabase:
                st.error("Supabaseの設定が未完了です。")
            else:
                with st.spinner("AIが分析中..."):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel("gemini-3.6-flash")

                        image_resized = image.copy()
                        image_resized.thumbnail((800, 800))

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
                        （親身なアドバイス。目標カロリー{target_calories:.0f}kcal/日との兼ね合いにも触れること）
                        """
                        response = model.generate_content([prompt, image_resized])
                        result_text = response.text
                        nutrition = parse_nutrition(result_text)

                        st.session_state["current_result"] = result_text
                        st.session_state["current_nutrition"] = nutrition

                        history_data = {
                            "user_id": st.session_state["user_id"],
                            "menu_name": nutrition["menu_name"],
                            "calories": f"{nutrition['calories']:.0f} kcal",
                            "calories_num": nutrition["calories"],
                            "protein_g": nutrition["protein"],
                            "fat_g": nutrition["fat"],
                            "carbs_g": nutrition["carbs"],
                            "detail_advice": result_text,
                        }
                        supabase.table("diet_history_secure").insert(history_data).execute()
                        st.rerun()
                    except Exception as e:
                        error_text = str(e)
                        if "429" in error_text or "quota" in error_text.lower():
                            st.error(
                                "⚠️ 現在、AI分析の無料利用回数の上限に達しています。\n\n"
                                "Gemini APIの無料枠には1日あたりのリクエスト数に上限があります。"
                                "しばらく時間をおいてから再度お試しいただくか、"
                                "ご自身のGemini API Keyの利用状況・プランをご確認ください。\n\n"
                                "詳細: https://ai.google.dev/gemini-api/docs/rate-limits"
                            )
                        elif "api_key" in error_text.lower() or "api key" in error_text.lower():
                            st.error("⚠️ Gemini API Keyが正しくないか、無効になっている可能性があります。入力内容をご確認ください。")
                        else:
                            st.error(f"エラーが発生しました: {e}")

    if st.session_state["current_result"]:
        st.success("分析完了！保存されました。")
        st.markdown(st.session_state["current_result"])

        nutrition = st.session_state.get("current_nutrition") or {}
        suggested_keyword = suggest_shopping_keyword(
            nutrition.get("protein", 0), nutrition.get("fat", 0), nutrition.get("carbs", 0)
        )
        render_shopping_links(suggested_keyword, key_suffix="record")

# ---------------------------------------------------------
# タブ2: ダッシュボード
# ---------------------------------------------------------
with tab_dashboard:
    st.header("📊 栄養ダッシュボード")

    if not st.session_state["user_id"] or not supabase:
        st.info("ログインするとダッシュボードが表示されます。")
    else:
        try:
            res_history = (
                supabase.table("diet_history_secure")
                .select("*")
                .eq("user_id", st.session_state["user_id"])
                .order("created_at", desc=True)
                .execute()
            )
            data = res_history.data or []

            if not data:
                st.info("まだ食事記録がありません。まずは「📸 食事記録」タブから写真を分析してください。")
            else:
                df = pd.DataFrame(data)
                df["created_at"] = pd.to_datetime(df["created_at"])
                df["date"] = df["created_at"].dt.date

                # 数値カラムが無い/欠損している古いレコードにも対応
                for col in ["calories_num", "protein_g", "fat_g", "carbs_g"]:
                    if col not in df.columns:
                        df[col] = 0.0
                    df[col] = df[col].fillna(0.0)

                today = datetime.now().date()
                today_df = df[df["date"] == today]
                today_total = today_df["calories_num"].sum()

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("今日の摂取カロリー", f"{today_total:.0f} kcal")
                col_b.metric("目標カロリー", f"{target_calories:.0f} kcal")
                diff = today_total - target_calories
                col_c.metric("差分", f"{diff:+.0f} kcal", delta_color="inverse")

                st.subheader("📈 直近14日間のカロリー推移")
                daily = df.groupby("date")["calories_num"].sum().sort_index()
                last14 = daily.tail(14)
                st.line_chart(last14)

                st.subheader("🥗 直近7日間の平均PFCバランス")
                last7 = df[df["date"] >= today - timedelta(days=7)]
                if not last7.empty:
                    pfc_avg = pd.DataFrame(
                        {
                            "平均g/日": [
                                last7["protein_g"].sum() / 7,
                                last7["fat_g"].sum() / 7,
                                last7["carbs_g"].sum() / 7,
                            ]
                        },
                        index=["タンパク質", "脂質", "炭水化物"],
                    )
                    st.bar_chart(pfc_avg)
                else:
                    st.caption("直近7日間のデータがまだありません。")
        except Exception as e:
            st.error(f"ダッシュボードの取得に失敗しました: {e}")

# ---------------------------------------------------------
# タブ3: 履歴・詳細
# ---------------------------------------------------------
with tab_history:
    st.header("🗂️ 食事履歴の一覧")

    if not st.session_state["user_id"] or not supabase:
        st.info("ログインすると、あなたの過去の食事履歴が表示されます。")
    else:
        try:
            res_history = (
                supabase.table("diet_history_secure")
                .select("*")
                .eq("user_id", st.session_state["user_id"])
                .order("created_at", desc=True)
                .execute()
            )
            rows = res_history.data or []

            if not rows:
                st.info("まだ保存された食事履歴はありません。")
            else:
                options = [
                    f"{row['created_at'][:16]} - {row['menu_name']} ({row.get('calories', '')})" for row in rows
                ]
                selected_opt = st.selectbox("過去の分析アドバイスを振り返る：", options)
                selected_idx = options.index(selected_opt)
                selected_row = rows[selected_idx]

                st.markdown("---")
                st.subheader(f"📄 {selected_row['menu_name']} の詳細分析")
                st.markdown(selected_row["detail_advice"])

                col_del, col_export = st.columns(2)
                with col_del:
                    if st.button("🗑️ この記録を削除する"):
                        supabase.table("diet_history_secure").delete().eq("id", selected_row["id"]).execute()
                        st.success("削除しました。")
                        st.rerun()
                with col_export:
                    df_export = pd.DataFrame(rows)
                    csv = df_export.to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        "⬇️ 全履歴をCSVでダウンロード",
                        data=csv,
                        file_name="diet_history.csv",
                        mime="text/csv",
                    )

                # 不足栄養素の購入リンク (Amazon / 楽天) — 今日の栄養バランスから提案
                today_str = datetime.now().date()
                today_rows = [
                    r for r in rows if pd.to_datetime(r["created_at"]).date() == today_str
                ]
                suggested_keyword = suggest_shopping_keyword(
                    sum(r.get("protein_g") or 0 for r in today_rows),
                    sum(r.get("fat_g") or 0 for r in today_rows),
                    sum(r.get("carbs_g") or 0 for r in today_rows),
                )
                render_shopping_links(suggested_keyword, key_suffix="history")
        except Exception as e:
            st.error(f"履歴データの取得に失敗しました: {e}")

st.markdown("---")
with st.expander("📜 本アプリの規約・プライバシーポリシー"):
    st.caption(
        "当アプリは、ユーザー登録情報をSupabaseを介して保護し、許可なく第三者に開示することはありません。"
        "Amazonアソシエイト・プログラム、楽天アフィリエイトの参加者です。"
    )
