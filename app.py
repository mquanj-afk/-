import re
import urllib.parse
from datetime import datetime, timedelta

import pandas as pd
import altair as alt
import streamlit as st
import streamlit.components.v1 as components
import extra_streamlit_components as stx
import google.generativeai as genai
from PIL import Image
from supabase import create_client, Client

# =========================================================
# 0. 多言語テキスト (日本語 / ベトナム語)
# =========================================================
TEXTS = {
    "ja": {
        "app_caption": "AIが写真から栄養バランスを判定し、今日の食事に点数をつけます。",
        "disclaimer": (
            "⚠️ 本アプリはAIによる簡易的な栄養アドバイスを提供するもので、医療的な診断・治療の代わりにはなりません。"
            "持病がある方や体調に不安がある方は、必ず医師・管理栄養士にご相談のうえご利用ください。"
        ),
        "lang_label": "🌐 言語",
        "account_header": "🔑 アカウント",
        "menu_login": "ログイン",
        "menu_signup": "新規会員登録",
        "email_label": "メールアドレス",
        "password_label": "パスワード",
        "create_account_btn": "アカウントを作成する",
        "login_btn": "ログインする",
        "logged_in": "🔒 ログイン中",
        "logout_btn": "ログアウト",
        "signup_success": "登録完了！「ログイン」に切り替えてログインしてください。",
        "max_users_reached": "現在、招待制のクローズドベータ運用中のため、新規登録の受付を停止しています。",
        "signup_error": "登録エラー: {e}",
        "login_success": "ログイン成功！",
        "login_fail": "ログインに失敗しました。",
        "supabase_missing": "Supabaseの設定が未完了です。",
        "email_pw_required": "メールアドレスとパスワードを両方正しく入力してください。",
        "pw_too_short": "パスワードは8文字以上で、英字と数字の両方を含めてください。",
        "profile_header": "👤 利用者プロフィール",
        "profile_loaded": "✅ 保存済みプロフィールを読み込みました",
        "profile_hint": "⚠️ 目標カロリーを正しく計算するため、下の項目を必ず入力してください👇",
        "age_label": "年齢",
        "gender_label": "性別",
        "gender_options": ["男性", "女性", "その他"],
        "height_label": "身長 (cm)",
        "weight_label": "体重 (kg)",
        "activity_label": "活動レベル",
        "activity_options": ["低い(デスクワーク中心)", "普通(週2-3回運動)", "高い(毎日運動・肉体労働)"],
        "illness_label": "持病・病気の有無",
        "illness_options": ["なし", "あり"],
        "illness_detail_label": "具体的な病名や制限項目",
        "purpose_label": "目的",
        "purpose_options": ["ダイエット（減量）", "現状維持", "バルクアップ（筋肥大）"],
        "save_profile_btn": "💾 プロフィールを保存する(次回から自動入力)",
        "profile_saved": "プロフィールを保存しました。次回ログイン時から自動入力されます。",
        "target_calorie_label": "🎯 推定目標カロリー/日",
        "gemini_key_expander": "🔑 自分のGemini API Keyを使う(任意・無制限)",
        "gemini_key_caption": "何も入力しなければ、運営者の共有キーで1日{limit}回まで無料でお試しいただけます。もっと使いたい方だけ、ご自身のAPI Keyを入力してください。",
        "gemini_key_label": "Gemini API Key",
        "own_key_caption": "✅ ご自身のAPI Keyを使用します(無制限)",
        "shared_key_caption": "🆓 共有キーを使用中(本日の残り: {remaining}/{limit}回)",
        "tab_record": "📸 今日の記録",
        "tab_history": "🗂️ 履歴",
        "record_header": "食事を記録する",
        "meal_type_label": "食事の区分",
        "meal_types": ["朝食", "昼食", "夕食", "間食"],
        "upload_label": "食事の写真をアップロードしてください...",
        "analyze_btn": "エネルギー・栄養素を計算する",
        "login_required": "履歴を保存するため、先にサイドバーからログインをしてください。",
        "quota_exceeded": "本日の無料利用回数(共有キー)を使い切りました。明日また利用いただくか、サイドバーからご自身のAPI Keyを入力してください。",
        "own_key_required": "サイドバーの「自分のGemini API Keyを使う」欄にAPI Keyを入力してください。",
        "analyzing": "AIが分析中...",
        "quota_error": "⚠️ 現在、AI分析の無料利用回数の上限に達しています。しばらく時間をおいてから再度お試しいただくか、ご自身のGemini API Keyの利用状況・プランをご確認ください。",
        "api_key_error": "⚠️ Gemini API Keyが正しくないか、無効になっている可能性があります。入力内容をご確認ください。",
        "generic_error": "エラーが発生しました: {e}",
        "record_success": "✅ {menu} を記録しました",
        "login_prompt_record": "ログインすると、今日の記録とスコアがここに表示されます。",
        "today_calorie_header": "🔥 今日のカロリー",
        "col_target": "目標カロリー",
        "col_consumed": "摂取済み",
        "col_remaining": "残り",
        "pfc_header": "⚖️ 今日のPFCバランス",
        "col_gram": "グラム",
        "col_kcal": "カロリー",
        "col_percent": "割合",
        "protein": "タンパク質",
        "fat": "脂質",
        "carbs": "炭水化物",
        "micro_header": "🧪 食物繊維・塩分・ビタミンなど",
        "micro_chart_y": "% (目安を100%として)",
        "col_today_total": "今日の合計",
        "col_guideline": "一般的な目安/日",
        "fiber": "食物繊維",
        "sodium": "塩分相当量",
        "vitamin_c": "ビタミンC",
        "vitamin_d": "ビタミンD",
        "calcium": "カルシウム",
        "iron": "鉄分",
        "micro_caption": "※ AIによる画像からの概算値です。正確な栄養成分表示ではありません。",
        "meal_score_header": "🍽️ 今日の食事とスコア",
        "col_meal_type": "区分",
        "col_menu": "メニュー",
        "col_score": "スコア",
        "final_score_label": "🏆 本日の最終スコア",
        "current_score_label": "📊 現在のスコア(途中経過)",
        "score_high_msg": "🎉 素晴らしい一日でした！このバランスを続けましょう。",
        "score_mid_msg": "👍 まずまずのバランスでした。明日はもう少し野菜や食物繊維を意識してみましょう。",
        "score_low_msg": "💪 明日はタンパク質・食物繊維・塩分のバランスを見直してみましょう。",
        "score_caption": "夕食を記録すると、その日の最終スコアが確定します。",
        "no_record_caption": "まだ今日の記録がありません。上のフォームから食事を記録してみましょう。",
        "advice_label": "💬 アドバイス",
        "translate_label": "🌐 この記録を表示する言語",
        "translate_btn": "翻訳する",
        "translating": "翻訳中...",
        "history_header": "🗂️ 食事履歴の一覧",
        "history_login_prompt": "ログインすると、あなたの過去の食事履歴が表示されます。",
        "no_history": "まだ保存された食事履歴はありません。",
        "select_history_label": "過去の分析アドバイスを振り返る：",
        "detail_header": "📄 {menu} の詳細分析",
        "delete_btn": "🗑️ この記録を削除する",
        "delete_success": "削除しました。",
        "download_btn": "⬇️ 全履歴をCSVでダウンロード",
        "history_error": "履歴データの取得に失敗しました: {e}",
        "shopping_header": "🛒 不足栄養素を購入する",
        "shopping_label": "購入・検索したい健康食材",
        "amazon_btn": "👉 Amazonで「{kw}」を見る",
        "rakuten_btn": "👉 楽天市場で「{kw}」を見る",
        "policy_expander": "📜 本アプリの規約・プライバシーポリシー",
        "policy_text": (
            "当アプリは、ユーザー登録情報をSupabaseを介して保護し、許可なく第三者に開示することはありません。"
            "Amazonアソシエイト・プログラム、楽天アフィリエイトの参加者です。"
        ),
        "status_low": "不足",
        "status_ok": "適正",
        "status_high": "過剰",
        "ai_output_lang_instruction": "回答はすべて日本語で出力してください。",
    },
    "vi": {
        "app_caption": "AI phân tích ảnh bữa ăn và chấm điểm cân bằng dinh dưỡng cho bạn mỗi ngày.",
        "disclaimer": (
            "⚠️ Ứng dụng này cung cấp lời khuyên dinh dưỡng đơn giản từ AI, không thay thế cho chẩn đoán "
            "hoặc điều trị y tế. Nếu bạn có bệnh nền hoặc lo lắng về sức khỏe, vui lòng tham khảo ý kiến "
            "bác sĩ hoặc chuyên gia dinh dưỡng trước khi sử dụng."
        ),
        "lang_label": "🌐 Ngôn ngữ",
        "account_header": "🔑 Tài khoản",
        "menu_login": "Đăng nhập",
        "menu_signup": "Đăng ký mới",
        "email_label": "Email",
        "password_label": "Mật khẩu",
        "create_account_btn": "Tạo tài khoản",
        "login_btn": "Đăng nhập",
        "logged_in": "🔒 Đã đăng nhập",
        "logout_btn": "Đăng xuất",
        "signup_success": "Đăng ký thành công! Vui lòng chuyển sang mục “Đăng nhập” để tiếp tục.",
        "max_users_reached": "Hiện đang trong giai đoạn thử nghiệm giới hạn số lượng người dùng, tạm thời không nhận đăng ký mới.",
        "signup_error": "Lỗi đăng ký: {e}",
        "login_success": "Đăng nhập thành công!",
        "login_fail": "Đăng nhập thất bại.",
        "supabase_missing": "Chưa thiết lập xong Supabase.",
        "email_pw_required": "Vui lòng nhập đầy đủ và chính xác email và mật khẩu.",
        "pw_too_short": "Mật khẩu phải có ít nhất 8 ký tự và bao gồm cả chữ cái và số.",
        "profile_header": "👤 Hồ sơ cá nhân",
        "profile_loaded": "✅ Đã tải hồ sơ đã lưu",
        "profile_hint": "⚠️ Vui lòng nhập đầy đủ thông tin bên dưới để tính calo mục tiêu chính xác👇",
        "age_label": "Tuổi",
        "gender_label": "Giới tính",
        "gender_options": ["Nam", "Nữ", "Khác"],
        "height_label": "Chiều cao (cm)",
        "weight_label": "Cân nặng (kg)",
        "activity_label": "Mức độ vận động",
        "activity_options": ["Thấp (làm việc bàn giấy)", "Bình thường (2-3 lần/tuần)", "Cao (vận động/lao động mỗi ngày)"],
        "illness_label": "Có bệnh nền không?",
        "illness_options": ["Không", "Có"],
        "illness_detail_label": "Tên bệnh hoặc hạn chế cụ thể",
        "purpose_label": "Mục tiêu",
        "purpose_options": ["Giảm cân", "Duy trì hiện tại", "Tăng cơ"],
        "save_profile_btn": "💾 Lưu hồ sơ (tự động điền lần sau)",
        "profile_saved": "Đã lưu hồ sơ. Lần đăng nhập sau sẽ tự động điền.",
        "target_calorie_label": "🎯 Calo mục tiêu ước tính/ngày",
        "gemini_key_expander": "🔑 Dùng API Key Gemini của riêng bạn (tùy chọn · không giới hạn)",
        "gemini_key_caption": "Nếu để trống, bạn có thể dùng miễn phí {limit} lần/ngày bằng key dùng chung của quản trị viên. Nếu muốn dùng nhiều hơn, hãy nhập API Key của riêng bạn.",
        "gemini_key_label": "Gemini API Key",
        "own_key_caption": "✅ Đang dùng API Key riêng của bạn (không giới hạn)",
        "shared_key_caption": "🆓 Đang dùng key dùng chung (còn lại hôm nay: {remaining}/{limit} lần)",
        "tab_record": "📸 Ghi lại hôm nay",
        "tab_history": "🗂️ Lịch sử",
        "record_header": "Ghi lại bữa ăn",
        "meal_type_label": "Loại bữa ăn",
        "meal_types": ["Bữa sáng", "Bữa trưa", "Bữa tối", "Ăn vặt"],
        "upload_label": "Vui lòng tải ảnh bữa ăn lên...",
        "analyze_btn": "Tính năng lượng & dinh dưỡng",
        "login_required": "Vui lòng đăng nhập ở thanh bên trước để lưu lịch sử.",
        "quota_exceeded": "Bạn đã dùng hết số lần miễn phí hôm nay (key dùng chung). Vui lòng thử lại vào ngày mai, hoặc nhập API Key riêng của bạn ở thanh bên.",
        "own_key_required": "Vui lòng nhập API Key vào mục “Dùng API Key Gemini của riêng bạn” ở thanh bên.",
        "analyzing": "AI đang phân tích...",
        "quota_error": "⚠️ Đã đạt giới hạn số lần phân tích miễn phí hôm nay. Vui lòng thử lại sau, hoặc kiểm tra gói/API Key Gemini của bạn.",
        "api_key_error": "⚠️ API Key Gemini không đúng hoặc không hợp lệ. Vui lòng kiểm tra lại.",
        "generic_error": "Đã xảy ra lỗi: {e}",
        "record_success": "✅ Đã ghi lại: {menu}",
        "login_prompt_record": "Đăng nhập để xem ghi chép và điểm số hôm nay tại đây.",
        "today_calorie_header": "🔥 Calo hôm nay",
        "col_target": "Mục tiêu",
        "col_consumed": "Đã nạp",
        "col_remaining": "Còn lại",
        "pfc_header": "⚖️ Cân bằng PFC hôm nay",
        "col_gram": "Gram",
        "col_kcal": "Calo",
        "col_percent": "Tỷ lệ",
        "protein": "Chất đạm",
        "fat": "Chất béo",
        "carbs": "Tinh bột/đường",
        "micro_header": "🧪 Chất xơ · Muối · Vitamin",
        "micro_chart_y": "% (so với khuyến nghị = 100%)",
        "col_today_total": "Tổng hôm nay",
        "col_guideline": "Khuyến nghị/ngày",
        "fiber": "Chất xơ",
        "sodium": "Muối (quy đổi)",
        "vitamin_c": "Vitamin C",
        "vitamin_d": "Vitamin D",
        "calcium": "Canxi",
        "iron": "Sắt",
        "micro_caption": "※ Đây là số liệu ước tính từ AI dựa trên hình ảnh, không phải thông tin dinh dưỡng chính xác.",
        "meal_score_header": "🍽️ Bữa ăn & điểm số hôm nay",
        "col_meal_type": "Loại",
        "col_menu": "Món ăn",
        "col_score": "Điểm",
        "final_score_label": "🏆 Điểm cuối cùng hôm nay",
        "current_score_label": "📊 Điểm hiện tại (đang cập nhật)",
        "score_high_msg": "🎉 Hôm nay bạn ăn rất cân bằng! Hãy duy trì nhé.",
        "score_mid_msg": "👍 Khá ổn. Ngày mai hãy ăn thêm rau và chất xơ nhé.",
        "score_low_msg": "💪 Ngày mai hãy chú ý cân bằng đạm, chất xơ và lượng muối nhé.",
        "score_caption": "Điểm cuối cùng sẽ được chốt sau khi bạn ghi lại bữa tối.",
        "no_record_caption": "Chưa có ghi chép nào hôm nay. Hãy bắt đầu ghi lại bữa ăn ở trên nhé.",
        "advice_label": "💬 Lời khuyên",
        "translate_label": "🌐 Xem bản ghi này bằng ngôn ngữ",
        "translate_btn": "Dịch",
        "translating": "Đang dịch...",
        "history_header": "🗂️ Lịch sử bữa ăn",
        "history_login_prompt": "Đăng nhập để xem lịch sử bữa ăn trước đây của bạn.",
        "no_history": "Chưa có lịch sử nào được lưu.",
        "select_history_label": "Xem lại phân tích trước đây:",
        "detail_header": "📄 Phân tích chi tiết: {menu}",
        "delete_btn": "🗑️ Xóa ghi chép này",
        "delete_success": "Đã xóa.",
        "download_btn": "⬇️ Tải toàn bộ lịch sử (CSV)",
        "history_error": "Không thể tải dữ liệu lịch sử: {e}",
        "shopping_header": "🛒 Mua thêm dưỡng chất còn thiếu",
        "shopping_label": "Từ khóa thực phẩm chức năng muốn tìm",
        "amazon_btn": "👉 Xem trên Amazon: “{kw}”",
        "rakuten_btn": "👉 Xem trên Rakuten: “{kw}”",
        "policy_expander": "📜 Điều khoản & Chính sách bảo mật",
        "policy_text": (
            "Ứng dụng này bảo vệ thông tin đăng ký của người dùng thông qua Supabase và không tiết lộ "
            "cho bên thứ ba khi chưa được phép. Ứng dụng tham gia chương trình Amazon Associates và "
            "Rakuten Affiliate."
        ),
        "status_low": "Thiếu",
        "status_ok": "Đủ",
        "status_high": "Dư",
        "ai_output_lang_instruction": "Hãy trả lời toàn bộ bằng tiếng Việt.",
    },
    "en": {
        "app_caption": "AI analyzes your meal photos and scores your nutritional balance every day.",
        "disclaimer": (
            "⚠️ This app provides simple AI-generated nutrition advice and is not a substitute for medical "
            "diagnosis or treatment. If you have a pre-existing condition or health concerns, please consult "
            "a doctor or registered dietitian before using this app."
        ),
        "lang_label": "🌐 Language",
        "account_header": "🔑 Account",
        "menu_login": "Log in",
        "menu_signup": "Sign up",
        "email_label": "Email",
        "password_label": "Password",
        "create_account_btn": "Create account",
        "login_btn": "Log in",
        "logged_in": "🔒 Logged in",
        "logout_btn": "Log out",
        "signup_success": "Account created! Please switch to “Log in” to continue.",
        "max_users_reached": "This app is currently running a limited, invite-only beta. New sign-ups are closed for now.",
        "signup_error": "Sign-up error: {e}",
        "login_success": "Logged in successfully!",
        "login_fail": "Login failed.",
        "supabase_missing": "Supabase is not set up yet.",
        "email_pw_required": "Please enter a valid email and password.",
        "pw_too_short": "Password must be at least 8 characters and include both letters and numbers.",
        "profile_header": "👤 Your Profile",
        "profile_loaded": "✅ Loaded your saved profile",
        "profile_hint": "⚠️ Please fill in the fields below so your target calories can be calculated accurately👇",
        "age_label": "Age",
        "gender_label": "Gender",
        "gender_options": ["Male", "Female", "Other"],
        "height_label": "Height (cm)",
        "weight_label": "Weight (kg)",
        "activity_label": "Activity level",
        "activity_options": ["Low (mostly desk work)", "Moderate (exercise 2-3x/week)", "High (exercise/labor daily)"],
        "illness_label": "Do you have any pre-existing conditions?",
        "illness_options": ["None", "Yes"],
        "illness_detail_label": "Condition or dietary restriction",
        "purpose_label": "Goal",
        "purpose_options": ["Weight loss", "Maintain current weight", "Bulk up (muscle gain)"],
        "save_profile_btn": "💾 Save profile (auto-fill next time)",
        "profile_saved": "Profile saved. It will be filled in automatically next time you log in.",
        "target_calorie_label": "🎯 Estimated target calories/day",
        "gemini_key_expander": "🔑 Use your own Gemini API Key (optional · unlimited)",
        "gemini_key_caption": "If left blank, you can try {limit} free analyses/day using the shared key. If you'd like more, enter your own API Key.",
        "gemini_key_label": "Gemini API Key",
        "own_key_caption": "✅ Using your own API Key (unlimited)",
        "shared_key_caption": "🆓 Using the shared key (remaining today: {remaining}/{limit})",
        "tab_record": "📸 Today's Log",
        "tab_history": "🗂️ History",
        "record_header": "Log a meal",
        "meal_type_label": "Meal type",
        "meal_types": ["Breakfast", "Lunch", "Dinner", "Snack"],
        "upload_label": "Upload a photo of your meal...",
        "analyze_btn": "Analyze energy & nutrients",
        "login_required": "Please log in from the sidebar first so your history can be saved.",
        "quota_exceeded": "You've used up today's free analyses (shared key). Please try again tomorrow, or enter your own API Key in the sidebar.",
        "own_key_required": "Please enter an API Key in the “Use your own Gemini API Key” section in the sidebar.",
        "analyzing": "AI is analyzing...",
        "quota_error": "⚠️ The free daily analysis limit has been reached. Please try again later, or check your own Gemini API Key's plan/usage.",
        "api_key_error": "⚠️ The Gemini API Key appears to be invalid. Please check it and try again.",
        "generic_error": "An error occurred: {e}",
        "record_success": "✅ Logged: {menu}",
        "login_prompt_record": "Log in to see today's log and score here.",
        "today_calorie_header": "🔥 Today's Calories",
        "col_target": "Target",
        "col_consumed": "Consumed",
        "col_remaining": "Remaining",
        "pfc_header": "⚖️ Today's PFC Balance",
        "col_gram": "Grams",
        "col_kcal": "Calories",
        "col_percent": "Ratio",
        "protein": "Protein",
        "fat": "Fat",
        "carbs": "Carbs",
        "micro_header": "🧪 Fiber, Sodium & Vitamins",
        "col_today_total": "Today's total",
        "col_guideline": "General daily guideline",
        "fiber": "Fiber",
        "sodium": "Sodium (salt equiv.)",
        "vitamin_c": "Vitamin C",
        "vitamin_d": "Vitamin D",
        "calcium": "Calcium",
        "iron": "Iron",
        "micro_caption": "※ These are AI estimates from the photo, not precise nutrition facts.",
        "micro_chart_y": "% (guideline = 100%)",
        "meal_score_header": "🍽️ Today's Meals & Scores",
        "col_meal_type": "Type",
        "col_menu": "Meal",
        "col_score": "Score",
        "final_score_label": "🏆 Today's Final Score",
        "current_score_label": "📊 Current Score (in progress)",
        "score_high_msg": "🎉 Great balance today! Keep it up.",
        "score_mid_msg": "👍 Pretty good. Tomorrow, try adding a bit more vegetables and fiber.",
        "score_low_msg": "💪 Tomorrow, try to balance protein, fiber, and sodium a bit more.",
        "score_caption": "Your final score for the day is set once you log dinner.",
        "no_record_caption": "No meals logged today yet. Try logging one using the form above.",
        "advice_label": "💬 Advice",
        "translate_label": "🌐 View this record in",
        "translate_btn": "Translate",
        "translating": "Translating...",
        "history_header": "🗂️ Meal History",
        "history_login_prompt": "Log in to see your past meal history.",
        "no_history": "No meal history saved yet.",
        "select_history_label": "Review a past analysis:",
        "detail_header": "📄 Detailed analysis: {menu}",
        "delete_btn": "🗑️ Delete this record",
        "delete_success": "Deleted.",
        "download_btn": "⬇️ Download all history (CSV)",
        "history_error": "Failed to load history data: {e}",
        "shopping_header": "🛒 Shop for what you're missing",
        "shopping_label": "Supplement keyword to search for",
        "amazon_btn": "👉 View “{kw}” on Amazon",
        "rakuten_btn": "👉 View “{kw}” on Rakuten",
        "policy_expander": "📜 Terms & Privacy Policy",
        "policy_text": (
            "This app protects registered user information via Supabase and does not disclose it to third "
            "parties without permission. This app participates in the Amazon Associates and Rakuten "
            "Affiliate programs."
        ),
        "status_low": "Low",
        "status_ok": "OK",
        "status_high": "High",
        "ai_output_lang_instruction": "Please respond entirely in English.",
    },
}

# =========================================================
# 1. 画面の初期設定
# =========================================================
st.set_page_config(page_title="FitCompanion", page_icon="🍁", layout="wide")

# Streamlit標準の「Deploy」ボタン・GitHubアイコンは .streamlit/config.toml (toolbarMode="minimal")
# で非表示にしている。ここではフッターの「Made with Streamlit」表記も非表示にする。
st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# スマホ画面向けの最適化: 余白を詰めてボタン・タブをタップしやすい大きさにする
st.markdown(
    """
    <style>
    @media (max-width: 640px) {
        .block-container {
            padding-top: 1.2rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }
        .stButton > button, .stLinkButton > a, .stDownloadButton > button {
            font-size: 1.02em;
            padding-top: 0.6em;
            padding-bottom: 0.6em;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 1.0em;
            padding: 10px 8px;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.4rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# サイドバーを開くための矢印(スマホでは閉じた状態がデフォルトで見落とされやすい)を、
# テーマカラーの丸いボタンにして目立たせる
st.markdown(
    """
    <style>
    [data-testid*="CollapsedControl"] {
        background-color: #D9455F !important;
        border-radius: 50% !important;
        padding: 6px !important;
        box-shadow: 0 2px 8px rgba(217, 69, 95, 0.5) !important;
    }
    [data-testid*="CollapsedControl"] svg {
        fill: white !important;
        color: white !important;
        width: 26px !important;
        height: 26px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# アプリ全体をフレンドリーな印象にするための共通スタイル(角丸・やわらかい影)
st.markdown(
    """
    <style>
    .stButton > button, .stLinkButton > a, .stDownloadButton > button {
        border-radius: 999px !important;
        border: none !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .stButton > button:hover, .stLinkButton > a:hover, .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(217, 69, 95, 0.25);
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px 12px 0 0 !important;
    }
    img {
        border-radius: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 右下に表示される「Hosted with Streamlit」バッジを非表示にする。
# このバッジはStreamlit Cloud側がページの最上位フレームに直接挿入するため、
# 自分のアプリ内の要素をCSSで隠すだけでは消えない。components.htmlで発行した
# 同一オリジンのフレームからwindow.topを操作して、該当リンクを非表示にする。
components.html(
    """
    <script>
    function hideStreamlitBadge() {
        try {
            window.top.document.querySelectorAll('a[href*="streamlit.io"]').forEach(function (el) {
                el.style.display = "none";
            });
        } catch (e) {}
    }
    hideStreamlitBadge();
    setInterval(hideStreamlitBadge, 1000);
    </script>
    """,
    height=0,
)

if "lang" not in st.session_state:
    st.session_state["lang"] = "ja"

LANG_LABELS = ["日本語", "Tiếng Việt", "English"]
LANG_CODES = ["ja", "vi", "en"]

lang_choice = st.sidebar.radio(
    " / ".join(TEXTS[c]["lang_label"] for c in LANG_CODES),
    LANG_LABELS,
    index=LANG_CODES.index(st.session_state["lang"]) if st.session_state["lang"] in LANG_CODES else 0,
)
st.session_state["lang"] = LANG_CODES[LANG_LABELS.index(lang_choice)]
T = TEXTS[st.session_state["lang"]]

st.title("🍁 FitCompanion")
st.caption(T["app_caption"])
st.info(T["disclaimer"])

# --- 🔐 SUPABASEの設定 ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.sidebar.warning("⚠️ Secretsが未設定です。下に直接入力してください。")
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

for key, default in {
    "user_id": None,
    "current_result": None,
    "current_nutrition": None,
    "profile": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def load_profile(user_id: str) -> dict:
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
    if not supabase or not user_id:
        return False
    try:
        payload = {"user_id": user_id, **profile_data}
        supabase.table("user_profiles").upsert(payload, on_conflict="user_id").execute()
        return True
    except Exception as e:
        st.sidebar.error(f"プロフィール保存エラー: {e}")
        return False


AUTH_COOKIE_NAME = "fitcompanion_refresh_token"


@st.cache_resource(show_spinner=False)
def get_cookie_manager():
    return stx.CookieManager()


cookie_manager = get_cookie_manager()


def set_auth_cookie(refresh_token: str, widget_key: str):
    """ログイン状態を保持するため、ブラウザにrefresh_tokenを30日間のCookieとして保存する。"""
    try:
        cookie_manager.set(
            AUTH_COOKIE_NAME,
            refresh_token,
            expires_at=datetime.now() + timedelta(days=30),
            key=widget_key,
        )
    except Exception:
        pass


def clear_auth_cookie(widget_key: str):
    try:
        cookie_manager.delete(AUTH_COOKIE_NAME, key=widget_key)
    except Exception:
        pass


# ログイン状態の自動復元: ブラウザに保存されたrefresh_tokenがあれば、
# パスワード再入力なしでセッションを復元する。
if st.session_state["user_id"] is None and supabase:
    stored_refresh_token = cookie_manager.get(cookie=AUTH_COOKIE_NAME)
    if stored_refresh_token:
        try:
            restore_res = supabase.auth.refresh_session(stored_refresh_token)
            if restore_res and restore_res.user and restore_res.session:
                st.session_state["user_id"] = restore_res.user.id
                st.session_state["profile"] = load_profile(restore_res.user.id)
                # Supabaseのrefresh_tokenは使い捨て(ローテーション)のため、
                # 新しく発行されたtokenで必ずCookieを更新する
                set_auth_cookie(restore_res.session.refresh_token, widget_key="set_restore")
                st.rerun()
        except Exception:
            clear_auth_cookie(widget_key="delete_restore_fail")

# =========================================================
# 2. 🔐 会員登録・ログインシステム
# =========================================================
MAX_REGISTERED_USERS = 6


def is_valid_password(pw: str) -> bool:
    """8文字以上、かつ英字と数字を両方含むことを要求する。"""
    if len(pw) < 8:
        return False
    has_letter = re.search(r"[A-Za-z]", pw) is not None
    has_digit = re.search(r"[0-9]", pw) is not None
    return has_letter and has_digit


def get_registered_user_count() -> int:
    """user_profilesテーブルの行数を「登録済みユーザー数」の目安として数える。
    新規登録時に必ず1行作成するため、実質的な登録者数と一致する。"""
    if not supabase:
        return 0
    try:
        res = supabase.table("user_profiles").select("user_id", count="exact").execute()
        return res.count or 0
    except Exception:
        return 0


st.sidebar.header(T["account_header"])

if st.session_state["user_id"] is None:
    auth_action = st.sidebar.radio("メニュー", [T["menu_login"], T["menu_signup"]])
    email = st.sidebar.text_input(T["email_label"], autocomplete="email")
    password_autocomplete = "new-password" if auth_action == T["menu_signup"] else "current-password"
    password = st.sidebar.text_input(T["password_label"], type="password", autocomplete=password_autocomplete)

    if auth_action == T["menu_signup"]:
        if st.sidebar.button(T["create_account_btn"], use_container_width=True):
            if not supabase:
                st.sidebar.error(T["supabase_missing"])
            elif not email.strip() or not password.strip():
                st.sidebar.error(T["email_pw_required"])
            elif not is_valid_password(password.strip()):
                st.sidebar.error(T["pw_too_short"])
            elif get_registered_user_count() >= MAX_REGISTERED_USERS:
                st.sidebar.error(T["max_users_reached"])
            else:
                try:
                    res = supabase.auth.sign_up({"email": email.strip(), "password": password.strip()})
                    if res.user:
                        # 空レコードでも作成しておき、登録者数カウントの対象にする
                        save_profile(res.user.id, {})
                        st.sidebar.success(T["signup_success"])
                except Exception as e:
                    st.sidebar.error(T["signup_error"].format(e=e))

    elif auth_action == T["menu_login"]:
        if st.sidebar.button(T["login_btn"], type="primary", use_container_width=True):
            if not supabase:
                st.sidebar.error(T["supabase_missing"])
            elif not email.strip() or not password.strip():
                st.sidebar.error(T["email_pw_required"])
            else:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password.strip()})
                    if res.user:
                        st.session_state["user_id"] = res.user.id
                        st.session_state["profile"] = load_profile(res.user.id)
                        if res.session:
                            set_auth_cookie(res.session.refresh_token, widget_key="set_login")
                        st.sidebar.success(T["login_success"])
                        st.rerun()
                except Exception:
                    st.sidebar.error(T["login_fail"])
else:
    st.sidebar.success(T["logged_in"])
    if st.sidebar.button(T["logout_btn"], use_container_width=True):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        clear_auth_cookie(widget_key="delete_logout")
        st.session_state["user_id"] = None
        st.session_state["current_result"] = None
        st.session_state["current_nutrition"] = None
        st.session_state["profile"] = None
        st.rerun()

    if st.session_state["profile"] is None:
        st.session_state["profile"] = load_profile(st.session_state["user_id"])

# =========================================================
# 3. 👤 プロフィール入力欄 (強調表示・2回目以降は自動入力)
# =========================================================
saved_profile = st.session_state.get("profile") or {}

# プロフィール欄のコンテナに固定のCSSクラス(st-key-profile_highlight_box)を付与し、
# 目立つよう枠線をパルスさせるアニメーションを適用する
st.markdown(
    """
    <style>
    @keyframes fc-pulse-border {
        0%   { box-shadow: 0 0 0 0 rgba(217, 69, 95, 0.55); }
        70%  { box-shadow: 0 0 0 8px rgba(217, 69, 95, 0); }
        100% { box-shadow: 0 0 0 0 rgba(217, 69, 95, 0); }
    }
    .st-key-profile_highlight_box {
        animation: fc-pulse-border 2.2s infinite;
        border: 2px solid #D9455F !important;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

profile_box = st.sidebar.container(border=True, key="profile_highlight_box")
profile_box.markdown(
    f"""
    <div style="background-color:#D9455F;color:white;padding:10px 14px;
                border-radius:10px;font-weight:bold;font-size:1.1em;
                margin-bottom:6px;text-align:center;">
        📋 {T["profile_header"]}
    </div>
    """,
    unsafe_allow_html=True,
)
if saved_profile:
    profile_box.caption(T["profile_loaded"])
else:
    profile_box.warning(T["profile_hint"])

gender_options = T["gender_options"]
activity_options = T["activity_options"]
illness_options = T["illness_options"]
purpose_options = T["purpose_options"]


def _idx(options, value, fallback=0):
    return options.index(value) if value in options else fallback


age = profile_box.number_input(T["age_label"], min_value=1, max_value=120, value=int(saved_profile.get("age", 30)))
gender = profile_box.selectbox(T["gender_label"], gender_options, index=_idx(gender_options, saved_profile.get("gender")))
height = profile_box.number_input(
    T["height_label"], min_value=50.0, max_value=250.0, value=float(saved_profile.get("height", 170.0)), step=0.1
)
weight = profile_box.number_input(
    T["weight_label"], min_value=10.0, max_value=300.0, value=float(saved_profile.get("weight", 65.0)), step=0.1
)
activity_level = profile_box.selectbox(
    T["activity_label"], activity_options, index=_idx(activity_options, saved_profile.get("activity_level"), fallback=1)
)
has_illness = profile_box.radio(
    T["illness_label"], illness_options, index=_idx(illness_options, saved_profile.get("has_illness"))
)
illness_detail = ""
if has_illness == illness_options[1]:
    illness_detail = profile_box.text_input(T["illness_detail_label"], value=saved_profile.get("illness_detail", ""))
purpose = profile_box.selectbox(T["purpose_label"], purpose_options, index=_idx(purpose_options, saved_profile.get("purpose")))

if st.session_state["user_id"]:
    if profile_box.button(T["save_profile_btn"], type="primary", use_container_width=True):
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
            profile_box.success(T["profile_saved"])


# =========================================================
# 4. 目標カロリーの計算 (ミフリン・セントジョール式)
# =========================================================
def calc_target_calories(age, gender, height, weight, activity_level, purpose):
    if gender == gender_options[0]:  # 男性 / Nam
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    elif gender == gender_options[1]:  # 女性 / Nữ
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 78

    activity_factor_map = {activity_options[0]: 1.375, activity_options[1]: 1.55, activity_options[2]: 1.725}
    activity_factor = activity_factor_map.get(activity_level, 1.55)

    tdee = bmr * activity_factor
    if purpose == purpose_options[0]:  # ダイエット / Giảm cân
        return tdee - 500
    elif purpose == purpose_options[2]:  # バルクアップ / Tăng cơ
        return tdee + 300
    return tdee


target_calories = calc_target_calories(age, gender, height, weight, activity_level, purpose)
st.sidebar.metric(T["target_calorie_label"], f"{target_calories:.0f} kcal")


# =========================================================
# 5. AI利用: 運営者の共有キー(1日の無料回数あり) + 自分のキー(無制限)
# =========================================================
DAILY_FREE_LIMIT = 3
SHARED_GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""


def get_today_rows(user_id: str) -> list:
    if not supabase or not user_id:
        return []
    today_start = datetime.now().strftime("%Y-%m-%dT00:00:00")
    try:
        res = (
            supabase.table("diet_history_secure")
            .select("*")
            .eq("user_id", user_id)
            .gte("created_at", today_start)
            .order("created_at", desc=False)
            .execute()
        )
        rows = res.data or []
    except Exception:
        rows = []

    numeric_cols = [
        "calories_num", "protein_g", "fat_g", "carbs_g",
        "fiber_g", "sodium_g", "vitamin_c_mg", "vitamin_d_ug", "calcium_mg", "iron_mg",
    ]
    for row in rows:
        for col in numeric_cols:
            row[col] = row.get(col) or 0.0
        row["meal_type"] = row.get("meal_type") or "-"
    return rows


today_rows = get_today_rows(st.session_state["user_id"]) if st.session_state["user_id"] else []
today_usage = len(today_rows)
remaining_free = max(0, DAILY_FREE_LIMIT - today_usage)

with st.sidebar.expander(T["gemini_key_expander"], expanded=False):
    st.caption(T["gemini_key_caption"].format(limit=DAILY_FREE_LIMIT))
    user_api_key = st.text_input(T["gemini_key_label"], type="password", key="user_gemini_key")

if user_api_key:
    api_key = user_api_key
    st.sidebar.caption(T["own_key_caption"])
elif SHARED_GEMINI_KEY and st.session_state["user_id"]:
    api_key = SHARED_GEMINI_KEY
    st.sidebar.caption(T["shared_key_caption"].format(remaining=remaining_free, limit=DAILY_FREE_LIMIT))
else:
    api_key = ""


# =========================================================
# 6. AI応答の解析・スコア計算・購入リンクのヘルパー
# =========================================================
def extract_number(label: str, text: str) -> float:
    match = re.search(rf"{label}[^\d]*([\d]+(?:\.[\d]+)?)", text)
    return float(match.group(1)) if match else 0.0


def extract_menu_name(text: str) -> str:
    match = re.search(r"メニュー名\**[:：]\s*(.+)", text)
    return match.group(1).strip() if match else "-"


def extract_advice(text: str) -> str:
    match = re.search(r"###\s*📝[^\n]*\n(.+)", text, re.S)
    return match.group(1).strip() if match else text.strip()


def translate_text(text: str, target_lang_name: str) -> str:
    """過去の記録(Markdown形式)を指定言語に翻訳する。見出し・箇条書きの構造は保持する。
    翻訳に失敗した場合は元のテキストをそのまま返す。"""
    if not api_key or not text:
        return text
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3.5-flash-lite")
        prompt = (
            f"以下はMarkdown形式の栄養分析結果です。見出し(###)や箇条書き(-)の構造はそのまま保ち、"
            f"値(数字や単位)も変えずに、文章の内容だけを{target_lang_name}に翻訳してください。"
            f"翻訳後のテキストのみを出力し、前置きは不要です。\n\n{text}"
        )
        generation_config = genai.types.GenerationConfig(max_output_tokens=500)
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text
    except Exception:
        return text


def parse_nutrition(text: str) -> dict:
    return {
        "menu_name": extract_menu_name(text),
        "calories": extract_number("総カロリー", text),
        "protein": extract_number("タンパク質", text),
        "fat": extract_number("脂質", text),
        "carbs": extract_number("炭水化物", text),
        "fiber": extract_number("食物繊維", text),
        "sodium": extract_number("塩分", text),
        "vitamin_c": extract_number("ビタミンC", text),
        "vitamin_d": extract_number("ビタミンD", text),
        "calcium": extract_number("カルシウム", text),
        "iron": extract_number("鉄分", text),
        "advice": extract_advice(text),
    }


def calculate_meal_score(protein_g, fat_g, carbs_g, fiber_g, sodium_g) -> float:
    total_kcal = protein_g * 4 + fat_g * 9 + carbs_g * 4
    if total_kcal <= 0:
        return 50.0
    p_ratio = protein_g * 4 / total_kcal
    f_ratio = fat_g * 9 / total_kcal
    c_ratio = carbs_g * 4 / total_kcal
    ideal = {"p": 0.18, "f": 0.25, "c": 0.57}
    deviation = abs(p_ratio - ideal["p"]) + abs(f_ratio - ideal["f"]) + abs(c_ratio - ideal["c"])
    score = 100 - deviation * 150
    if fiber_g >= 3:
        score += 5
    if sodium_g > 3:
        score -= (sodium_g - 3) * 10
    return max(0, min(100, score))


def suggest_shopping_keyword(totals: dict) -> str:
    """totals は {protein, fat, carbs, fiber, sodium, vitamin_c, vitamin_d, calcium, iron} の
    グラム/mg/µg合計値を受け取り、最も対応が必要な栄養素に応じた商品キーワードを返す。
    どれも適正なら、日替わりで一般的な健康食品をローテーション提案する。"""
    protein_g = totals.get("protein", 0)
    fat_g = totals.get("fat", 0)
    carbs_g = totals.get("carbs", 0)
    fiber_g = totals.get("fiber", 0)
    sodium_g = totals.get("sodium", 0)
    vc = totals.get("vitamin_c", 0)
    vd = totals.get("vitamin_d", 0)
    ca = totals.get("calcium", 0)
    fe = totals.get("iron", 0)

    total_kcal = protein_g * 4 + fat_g * 9 + carbs_g * 4
    protein_ratio = (protein_g * 4 / total_kcal) if total_kcal else 0
    fat_ratio = (fat_g * 9 / total_kcal) if total_kcal else 0

    lang = st.session_state["lang"]
    KEYWORDS = {
        "ja": {
            "protein": "プロテイン",
            "fat": "オメガ3 DHA EPA サプリ",
            "fiber": "食物繊維 サプリ",
            "sodium": "減塩 調味料",
            "vitamin_c": "ビタミンC サプリ",
            "vitamin_d": "ビタミンD サプリ",
            "calcium": "カルシウム サプリ",
            "iron": "鉄分 サプリ",
            "fallback": ["青汁", "スポーツドリンク", "プロテインバー", "素焼きミックスナッツ", "無糖ヨーグルト"],
        },
        "vi": {
            "protein": "Whey protein",
            "fat": "Omega 3 DHA EPA",
            "fiber": "Chất xơ bổ sung",
            "sodium": "Gia vị giảm muối",
            "vitamin_c": "Vitamin C bổ sung",
            "vitamin_d": "Vitamin D bổ sung",
            "calcium": "Canxi bổ sung",
            "iron": "Sắt bổ sung",
            "fallback": ["Bột rau xanh", "Nước uống thể thao", "Thanh protein", "Hạt hỗn hợp rang mộc", "Sữa chua không đường"],
        },
        "en": {
            "protein": "whey protein powder",
            "fat": "omega 3 DHA EPA supplement",
            "fiber": "fiber supplement",
            "sodium": "low sodium seasoning",
            "vitamin_c": "vitamin C supplement",
            "vitamin_d": "vitamin D supplement",
            "calcium": "calcium supplement",
            "iron": "iron supplement",
            "fallback": ["green superfood powder", "sports drink", "protein bar", "roasted mixed nuts", "plain yogurt"],
        },
    }[lang]

    # 優先順位: 不足しているものから順にチェック
    if protein_ratio < 0.13:
        return KEYWORDS["protein"]
    if fat_ratio < 0.15:
        return KEYWORDS["fat"]
    if fiber_g < 18:
        return KEYWORDS["fiber"]
    if vc < 75:
        return KEYWORDS["vitamin_c"]
    if vd < 5.5:
        return KEYWORDS["vitamin_d"]
    if ca < 600:
        return KEYWORDS["calcium"]
    if fe < 6:
        return KEYWORDS["iron"]
    if sodium_g > 7.5:
        return KEYWORDS["sodium"]

    # すべて適正な場合は、日替わりで一般的な健康食品をローテーション
    fallback_list = KEYWORDS["fallback"]
    return fallback_list[datetime.now().timetuple().tm_yday % len(fallback_list)]


def render_shopping_links(default_keyword: str, key_suffix: str):
    st.markdown("---")
    st.subheader(T["shopping_header"])
    search_keyword = st.text_input(T["shopping_label"], value=default_keyword, key=f"search_kw_{key_suffix}")

    amazon_tag = st.secrets.get("AMAZON_ASSOCIATE_ID", "your_id-22") if hasattr(st, "secrets") else "your_id-22"
    rakuten_id = st.secrets.get("RAKUTEN_AFFILIATE_ID", "") if hasattr(st, "secrets") else ""

    col_amazon, col_rakuten = st.columns(2)
    with col_amazon:
        amazon_params = {"k": str(search_keyword).strip(), "tag": amazon_tag}
        amazon_url = "https://www.amazon.co.jp/s?" + urllib.parse.urlencode(amazon_params)
        st.link_button(T["amazon_btn"].format(kw=search_keyword), amazon_url, use_container_width=True, key=f"amazon_btn_{key_suffix}")
    with col_rakuten:
        rakuten_search_url = f"https://search.rakuten.co.jp/search/mall/{urllib.parse.quote(str(search_keyword).strip())}/"
        if rakuten_id:
            encoded_target = urllib.parse.quote(rakuten_search_url, safe="")
            rakuten_url = f"https://hb.afl.rakuten.co.jp/hgc/{rakuten_id}/?pc={encoded_target}&m={encoded_target}"
        else:
            rakuten_url = rakuten_search_url
        st.link_button(T["rakuten_btn"].format(kw=search_keyword), rakuten_url, use_container_width=True, key=f"rakuten_btn_{key_suffix}")


# もみじテーマに合わせた状態カラー(不足=オレンジ, 適正=緑, 過剰=濃いピンク赤)
STATUS_COLORS = {"low": "#F2A65A", "ok": "#6FAE8C", "high": "#D9455F"}


def classify_status(value: float, low: float, high: float) -> str:
    """value が low未満なら'low'(不足)、high超なら'high'(過剰)、それ以外は'ok'(適正)。"""
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "ok"


def render_status_bar_chart(df: pd.DataFrame, y_title: str):
    """df は列 [nutrient, value, status_code, status_label] を持つ前提。
    色分けされた棒グラフ+値ラベルを描画する。"""
    color_scale = alt.Scale(domain=["low", "ok", "high"], range=[STATUS_COLORS["low"], STATUS_COLORS["ok"], STATUS_COLORS["high"]])
    base = alt.Chart(df).encode(x=alt.X("nutrient:N", title=None, sort=None))
    bars = base.mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=45).encode(
        y=alt.Y("value:Q", title=y_title),
        color=alt.Color("status_code:N", scale=color_scale, legend=alt.Legend(title=None, labelExpr="datum.label")),
        tooltip=[alt.Tooltip("nutrient:N", title=""), alt.Tooltip("value:Q", title=y_title, format=".1f"), alt.Tooltip("status_label:N", title="")],
    )
    labels = base.mark_text(dy=-10, fontSize=12).encode(y="value:Q", text=alt.Text("value:Q", format=".0f"))
    st.altair_chart((bars + labels).properties(height=260), use_container_width=True)

    # 凡例代わりの状態一覧をテキストで補足(色覚に依存しないため)
    legend_line = "　".join(
        f"🟠{T['status_low']}" if code == "low" else (f"🟢{T['status_ok']}" if code == "ok" else f"🔴{T['status_high']}")
        for code in ["low", "ok", "high"]
    )
    st.caption(legend_line)


def render_today_tables(rows: list, target_calories: float):
    total_calories = sum(r["calories_num"] for r in rows)
    total_protein = sum(r["protein_g"] for r in rows)
    total_fat = sum(r["fat_g"] for r in rows)
    total_carbs = sum(r["carbs_g"] for r in rows)
    total_fiber = sum(r["fiber_g"] for r in rows)
    total_sodium = sum(r["sodium_g"] for r in rows)
    total_vc = sum(r["vitamin_c_mg"] for r in rows)
    total_vd = sum(r["vitamin_d_ug"] for r in rows)
    total_ca = sum(r["calcium_mg"] for r in rows)
    total_fe = sum(r["iron_mg"] for r in rows)

    st.subheader(T["today_calorie_header"])
    df_cal = pd.DataFrame(
        {
            T["col_target"]: [f"{target_calories:.0f} kcal"],
            T["col_consumed"]: [f"{total_calories:.0f} kcal"],
            T["col_remaining"]: [f"{target_calories - total_calories:+.0f} kcal"],
        }
    )
    st.table(df_cal.T.rename(columns={0: "-"}))

    st.subheader(T["pfc_header"])
    pfc_kcal = {T["protein"]: total_protein * 4, T["fat"]: total_fat * 9, T["carbs"]: total_carbs * 4}
    total_pfc_kcal = sum(pfc_kcal.values()) or 1
    # 一般的な推奨PFC比率(%): タンパク質13-20 / 脂質20-30 / 炭水化物50-65
    pfc_ranges = {T["protein"]: (13, 20), T["fat"]: (20, 30), T["carbs"]: (50, 65)}
    pfc_rows = []
    for name, kcal in pfc_kcal.items():
        pct = kcal / total_pfc_kcal * 100
        low, high = pfc_ranges[name]
        code = classify_status(pct, low, high)
        pfc_rows.append({"nutrient": name, "value": pct, "status_code": code, "status_label": T[f"status_{code}"]})
    render_status_bar_chart(pd.DataFrame(pfc_rows), y_title="%")

    st.subheader(T["micro_header"])
    # (名前, 値, 不足判定の下限, 過剰判定の上限, 目安値=グラフの100%基準)
    micro_specs = [
        (T["fiber"], total_fiber, 18, 40, 18),
        (T["sodium"], total_sodium, 0, 7.5, 7.5),
        (T["vitamin_c"], total_vc, 75, 2000, 100),
        (T["vitamin_d"], total_vd, 5.5, 100, 8.5),
        (T["calcium"], total_ca, 600, 2500, 700),
        (T["iron"], total_fe, 6, 40, 7.5),
    ]
    micro_rows = []
    for name, value, low, high, target in micro_specs:
        code = classify_status(value, low, high)
        pct = (value / target * 100) if target else 0
        micro_rows.append({"nutrient": name, "value": pct, "status_code": code, "status_label": T[f"status_{code}"]})
    render_status_bar_chart(pd.DataFrame(micro_rows), y_title=T["micro_chart_y"])

    df_micro = pd.DataFrame(
        {
            T["col_today_total"]: [
                f"{total_fiber:.1f} g", f"{total_sodium:.1f} g", f"{total_vc:.0f} mg",
                f"{total_vd:.1f} µg", f"{total_ca:.0f} mg", f"{total_fe:.1f} mg",
            ],
        },
        index=[T["fiber"], T["sodium"], T["vitamin_c"], T["vitamin_d"], T["calcium"], T["iron"]],
    )
    st.table(df_micro.T)
    st.caption(T["micro_caption"])

    if rows:
        st.subheader(T["meal_score_header"])
        scores = []
        for r in rows:
            score = calculate_meal_score(r["protein_g"], r["fat_g"], r["carbs_g"], r["fiber_g"], r["sodium_g"])
            scores.append(score)
            with st.container(border=True):
                col_info, col_score = st.columns([4, 1])
                col_info.markdown(f"**[{r['meal_type']}] {r.get('menu_name', '')}**　{r['calories_num']:.0f} kcal")
                col_score.metric(T["col_score"], f"{score:.0f}")
                advice_text = extract_advice(r.get("detail_advice") or "")
                if advice_text:
                    st.caption(f"{T['advice_label']}: {advice_text}")

        avg_score = sum(scores) / len(scores)
        has_dinner = any(r["meal_type"] == T["meal_types"][2] for r in rows)

        if has_dinner:
            if avg_score >= 80:
                message = T["score_high_msg"]
            elif avg_score >= 60:
                message = T["score_mid_msg"]
            else:
                message = T["score_low_msg"]
            st.metric(T["final_score_label"], f"{avg_score:.0f}")
            st.success(message)
        else:
            st.metric(T["current_score_label"], f"{avg_score:.0f}")
            st.caption(T["score_caption"])
    else:
        st.caption(T["no_record_caption"])


# =========================================================
# 7. メイン画面
# =========================================================
tab_record, tab_history = st.tabs([T["tab_record"], T["tab_history"]])

# ---------------------------------------------------------
# タブ1: 今日の記録
# ---------------------------------------------------------
with tab_record:
    st.header(T["record_header"])

    meal_type = st.selectbox(T["meal_type_label"], T["meal_types"])
    uploaded_file = st.file_uploader(T["upload_label"], type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, use_container_width=True)

        if st.button(T["analyze_btn"], type="primary", use_container_width=True):
            if not st.session_state["user_id"]:
                st.error(T["login_required"])
            elif not api_key:
                st.error(T["quota_exceeded"] if SHARED_GEMINI_KEY else T["own_key_required"])
            elif not user_api_key and today_usage >= DAILY_FREE_LIMIT:
                st.error(T["quota_exceeded"])
            elif not supabase:
                st.error(T["supabase_missing"])
            else:
                with st.spinner(T["analyzing"]):
                    try:
                        genai.configure(api_key=api_key)
                        # gemini-3.5-flash-liteは画像からの構造化抽出のような単純作業に強く、
                        # gemini-3.6-flashより高速・低コスト
                        model = genai.GenerativeModel("gemini-3.5-flash-lite")

                        # 画像を小さくするほどアップロード・解析が速くなる。
                        # 食事の判別には640pxもあれば十分。
                        image_resized = image.copy()
                        if image_resized.mode != "RGB":
                            image_resized = image_resized.convert("RGB")
                        image_resized.thumbnail((512, 512))

                        illness_prompt = (
                            "特になし" if has_illness == illness_options[0] else f"持病・制限：{illness_detail}"
                        )

                        prompt = f"""
                        あなたはプロの管理栄養士です。食事画像から情報を解析してください。
                        利用者の健康データ：年齢 {age}歳、性別 {gender}、身長 {height}cm、体重 {weight}kg、目的 {purpose}、持病：{illness_prompt}
                        この食事の区分：{meal_type}
                        {T["ai_output_lang_instruction"]}

                        【出力フォーマット】(この形式を厳守してください。ラベル名(メニュー名、総カロリー等)は必ず日本語のまま、値と文章のみ指定言語にしてください)
                        ### 📊 栄養・カロリー計算結果
                        - **メニュー名**:（料理名）
                        - **総カロリー**: 〇〇 kcal
                        - **タンパク質**: 〇g
                        - **脂質**: 〇g
                        - **炭水化物**: 〇g
                        - **食物繊維**: 〇g
                        - **塩分相当量**: 〇g
                        - **ビタミンC**: 〇mg
                        - **ビタミンD**: 〇μg
                        - **カルシウム**: 〇mg
                        - **鉄分**: 〇mg

                        ### 📝 アドバイス
                        (2〜3文で簡潔に。目標カロリー{target_calories:.0f}kcal/日との兼ね合いに軽く触れつつ、
                        今不足している栄養素を補うために「次の食事で食べると良い具体的な食品」を1〜2個、
                        必ず名前を挙げて提案してください。)
                        """
                        # 出力トークン数の上限を絞って生成時間を短縮する
                        generation_config = genai.types.GenerationConfig(max_output_tokens=400)
                        response = model.generate_content(
                            [prompt, image_resized], generation_config=generation_config
                        )
                        result_text = response.text
                        nutrition = parse_nutrition(result_text)

                        st.session_state["current_result"] = result_text
                        st.session_state["current_nutrition"] = nutrition

                        history_data = {
                            "user_id": st.session_state["user_id"],
                            "meal_type": meal_type,
                            "menu_name": nutrition["menu_name"],
                            "calories": f"{nutrition['calories']:.0f} kcal",
                            "calories_num": nutrition["calories"],
                            "protein_g": nutrition["protein"],
                            "fat_g": nutrition["fat"],
                            "carbs_g": nutrition["carbs"],
                            "fiber_g": nutrition["fiber"],
                            "sodium_g": nutrition["sodium"],
                            "vitamin_c_mg": nutrition["vitamin_c"],
                            "vitamin_d_ug": nutrition["vitamin_d"],
                            "calcium_mg": nutrition["calcium"],
                            "iron_mg": nutrition["iron"],
                            "detail_advice": result_text,
                        }
                        supabase.table("diet_history_secure").insert(history_data).execute()
                        st.rerun()
                    except Exception as e:
                        error_text = str(e)
                        if "429" in error_text or "quota" in error_text.lower():
                            st.error(T["quota_error"])
                        elif "api_key" in error_text.lower() or "api key" in error_text.lower():
                            st.error(T["api_key_error"])
                        else:
                            st.error(T["generic_error"].format(e=e))

    if st.session_state["current_result"]:
        nutrition = st.session_state.get("current_nutrition") or {}
        st.success(T["record_success"].format(menu=nutrition.get("menu_name", "")))
        st.info(nutrition.get("advice", ""))

    st.markdown("---")
    if not st.session_state["user_id"]:
        st.info(T["login_prompt_record"])
    else:
        render_today_tables(today_rows, target_calories)

        today_totals = {
            "protein": sum(r["protein_g"] for r in today_rows),
            "fat": sum(r["fat_g"] for r in today_rows),
            "carbs": sum(r["carbs_g"] for r in today_rows),
            "fiber": sum(r["fiber_g"] for r in today_rows),
            "sodium": sum(r["sodium_g"] for r in today_rows),
            "vitamin_c": sum(r["vitamin_c_mg"] for r in today_rows),
            "vitamin_d": sum(r["vitamin_d_ug"] for r in today_rows),
            "calcium": sum(r["calcium_mg"] for r in today_rows),
            "iron": sum(r["iron_mg"] for r in today_rows),
        }
        render_shopping_links(suggest_shopping_keyword(today_totals), key_suffix="record")

# ---------------------------------------------------------
# タブ2: 履歴
# ---------------------------------------------------------
with tab_history:
    st.header(T["history_header"])

    if not st.session_state["user_id"] or not supabase:
        st.info(T["history_login_prompt"])
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
                st.info(T["no_history"])
            else:
                options = [
                    f"{row['created_at'][:16]} - [{row.get('meal_type', '')}] {row['menu_name']} ({row.get('calories', '')})"
                    for row in rows
                ]
                selected_opt = st.selectbox(T["select_history_label"], options)
                selected_idx = options.index(selected_opt)
                selected_row = rows[selected_idx]

                st.markdown("---")
                st.subheader(T["detail_header"].format(menu=selected_row["menu_name"]))

                lang_display_names = {"ja": "日本語", "vi": "Tiếng Việt", "en": "English"}
                col_lang, col_btn = st.columns([3, 1])
                translate_choice = col_lang.selectbox(
                    T["translate_label"],
                    LANG_LABELS,
                    index=LANG_CODES.index(st.session_state["lang"]),
                    key=f"translate_lang_{selected_row['id']}",
                )
                target_code = LANG_CODES[LANG_LABELS.index(translate_choice)]
                cache_key = f"translated_{selected_row['id']}_{target_code}"

                col_btn.write("")
                col_btn.write("")
                if col_btn.button(T["translate_btn"], key=f"translate_btn_{selected_row['id']}"):
                    if not api_key:
                        st.warning(T["own_key_required"] if not SHARED_GEMINI_KEY else T["quota_exceeded"])
                    else:
                        with st.spinner(T["translating"]):
                            st.session_state[cache_key] = translate_text(
                                selected_row["detail_advice"], lang_display_names[target_code]
                            )

                display_text = st.session_state.get(cache_key, selected_row["detail_advice"])
                st.markdown(display_text)

                col_del, col_export = st.columns(2)
                with col_del:
                    if st.button(T["delete_btn"]):
                        supabase.table("diet_history_secure").delete().eq("id", selected_row["id"]).execute()
                        st.success(T["delete_success"])
                        st.rerun()
                with col_export:
                    df_export = pd.DataFrame(rows)
                    csv = df_export.to_csv(index=False).encode("utf-8-sig")
                    st.download_button(T["download_btn"], data=csv, file_name="diet_history.csv", mime="text/csv")

                today_str = datetime.now().date()
                today_hist_rows = [r for r in rows if pd.to_datetime(r["created_at"]).date() == today_str]
                today_hist_totals = {
                    "protein": sum(r.get("protein_g") or 0 for r in today_hist_rows),
                    "fat": sum(r.get("fat_g") or 0 for r in today_hist_rows),
                    "carbs": sum(r.get("carbs_g") or 0 for r in today_hist_rows),
                    "fiber": sum(r.get("fiber_g") or 0 for r in today_hist_rows),
                    "sodium": sum(r.get("sodium_g") or 0 for r in today_hist_rows),
                    "vitamin_c": sum(r.get("vitamin_c_mg") or 0 for r in today_hist_rows),
                    "vitamin_d": sum(r.get("vitamin_d_ug") or 0 for r in today_hist_rows),
                    "calcium": sum(r.get("calcium_mg") or 0 for r in today_hist_rows),
                    "iron": sum(r.get("iron_mg") or 0 for r in today_hist_rows),
                }
                render_shopping_links(suggest_shopping_keyword(today_hist_totals), key_suffix="history")
        except Exception as e:
            st.error(T["history_error"].format(e=e))

st.markdown("---")
with st.expander(T["policy_expander"]):
    st.caption(T["policy_text"])
