from datetime import datetime, timedelta
import json
import urllib.parse
import urllib.request
import pandas as pd
import pytz
import streamlit as st

# 設定網頁標題與排版
st.set_page_config(page_title="阿凜的中職夢幻聯賽", page_icon="⚾", layout="wide")
st.title("⚾ 阿凜的中職夢幻聯賽")

ADMIN_USER = "謝正凜"
ADMIN_PIN = "0705"

# 取得 Google Sheet 網址與 Apps Script URL
try:
  SHEET_URL = st.secrets["spreadsheet"]
  SHEET_ID = SHEET_URL.split("/d/")[1].split("/")[0]
  SCRIPT_URL = st.secrets["script_url"]
except Exception as e:
  st.error("⚠️ 請確認 Streamlit Secrets 中有設定正確的 secrets！")
  SHEET_ID = ""
  SCRIPT_URL = ""


# 讀取 Google 試算表指定工作表為 DataFrame
def read_sheet(sheet_name):
  if not SHEET_ID:
    return pd.DataFrame()
  url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
  try:
    df = pd.read_csv(url)
    df.columns = [str(c).strip() for c in df.columns]
    return df
  except Exception as e:
    return pd.DataFrame()


# 寫入資料至 Google 試算表
def write_to_sheet(sheet_name, row_data):
  if not SCRIPT_URL:
    return False
  try:
    payload = json.dumps({"sheet": sheet_name, "row": row_data}).encode("utf-8")
    req = urllib.request.Request(
        SCRIPT_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as response:
      return True
  except Exception as e:
    st.error(f"寫入雲端失敗: {e}")
    return False


# 側邊欄：身分驗證
st.sidebar.title("👤 玩家身分驗證")
user_input = st.sidebar.text_input("請輸入您的姓名 / 暱稱", value="")

is_admin_verified = False

if user_input.strip() != "":
  st.session_state.user = user_input.strip()

  if st.session_state.user == ADMIN_USER:
    admin_pin = st.sidebar.text_input(
        "🔑 請輸入管理員驗證碼", type="password", key="admin_pin_input"
    )
    if admin_pin == ADMIN_PIN:
      st.sidebar.success(f"目前身分：**{st.session_state.user}** (管理員已驗證)")
      is_admin_verified = True
    else:
      st.sidebar.warning("🔒 身分為管理員，請輸入正確驗證碼以啟用權限！")
      is_admin_verified = False
  else:
    st.sidebar.success(f"目前身分：**{st.session_state.user}**")
    is_admin_verified = False
else:
  st.session_state.user = None
  is_admin_verified = False

st.session_state.is_admin = is_admin_verified


# 取得指定日期的截止時間
def get_cutoff_time_for_date(date_str):
  df_settings = read_sheet("settings")
  if not df_settings.empty and "date" in df_settings.columns:
    df_settings["date"] = df_settings["date"].astype(str)
    matched = df_settings[df_settings["date"] == date_str]
    if not matched.empty:
      time_str = str(matched.iloc[-1].get("cutoff_time", "18:35")).strip()
      try:
        h, m = map(int, time_str.split(":"))
        return h, m
      except:
        pass
  return 18, 35


tw_tz = pytz.timezone("Asia/Taipei")
now_tw = datetime.now(tw_tz)
today_str = now_tw.strftime("%Y-%m-%d")

today_h, today_m = get_cutoff_time_for_date(today_str)
cutoff_time_today = now_tw.replace(
    hour=today_h, minute=today_m, second=0, microsecond=0
)

if now_tw >= cutoff_time_today:
  default_game_date = (now_tw + timedelta(days=1)).date()
else:
  default_game_date = now_tw.date()


# 球員單日得分計算核心邏輯
def calculate_player_score(row):
  b1 = int(row.get("1B", 0))
  b2 = int(row.get("2B", 0))
  b3 = int(row.get("3B", 0))
  hr = int(row.get("HR", 0))
  rbi = int(row.get("RBI", 0))
  bb = int(row.get("BB", 0))
  sb = int(row.get("SB", 0))
  so = int(row.get("SO", 0))
  r = int(row.get("R", 0))
  gdp = int(row.get("GDP", 0))

  score = (
      (b1 * 3)
      + (b2 * 6)
      + (b3 * 10)
      + (hr * 15)
      + (bb * 2)
      + (rbi * 2)
      + (r * 2)
      + (sb * 3)
      - (so * 3)
      - (gdp * 5)
  )

  total_hits = b1 + b2 + b3 + hr

  if b1 >= 1 and b2 >= 1 and b3 >= 1 and hr >= 1:
    score += 50

  if total_hits >= 6:
    score += 30
  elif total_hits == 5:
    score += 20
  elif total_hits == 4:
    score += 12
  elif total_hits == 3:
    score += 7
  elif total_hits == 2:
    score += 4

  if hr >= 3:
    score += 40
  elif hr == 2:
    score += 24

  if sb >= 2:
    score += 8

  return score


def get_index(options, target_val):
  if target_val in options:
    return options.index(target_val)
  return 0


# 主頁面
if st.session_state.user is None:
  st.info("👈 請先於左側邊欄【輸入您的姓名 / 暱稱】，即可開始使用！")
else:
  tab1, tab2, tab3, tab4 = st.tabs(
      ["📋 安排今日陣容", "🏆 玩家積分排行榜", "📜 計分規則說明", "⚙️ 管理者數據匯入"]
  )

  # 載入球員名單
  try:
    df_players = pd.read_csv("players.csv")
    catchers = df_players[df_players["position"] == "捕手"]["name"].tolist()
    infielders = df_players[df_players["position"] == "內野手"][
        "name"
    ].tolist()
    outfielders = df_players[df_players["position"] == "外野手"][
        "name"
    ].tolist()
    all_batters = df_players["name"].tolist()
  except:
    df_players = pd.DataFrame()
    catchers, infielders, outfielders, all_batters = [], [], [], []

  # TAB 1: 安排陣容
  with tab1:
    game_date = st.date_input(
        "選擇比賽日期", value=default_game_date, key="lineup_date"
    ).strftime("%Y-%m-%d")

    c_h, c_m = get_cutoff_time_for_date(game_date)
    game_cutoff_dt = now_tw.replace(
        year=int(game_date.split("-")[0]),
        month=int(game_date.split("-")[1]),
        day=int(game_date.split("-")[2]),
        hour=c_h,
        minute=c_m,
        second=0,
        microsecond=0,
    )

    st.caption(
        f"🕒 {game_date} 比賽截止時間為：**{c_h:02d}:{c_m:02d}**（開打前陣容保密，截止後自動公開）"
    )

    st.subheader(
        f"【{st.session_state.user}】請安排 {game_date} 的守備陣容 (1捕 + 4內 +"
        " 3外 + 1DH)"
    )

    if df_players.empty:
      st.error("⚠️ 找不到 players.csv 或內容格式不正確，請檢查檔案！")
    else:
      df_cloud_lineups = read_sheet("lineups")

      has_history = False
      last_lineup = {}
      if not df_cloud_lineups.empty and "username" in df_cloud_lineups.columns:
        df_cloud_lineups["date"] = df_cloud_lineups["date"].astype(str)
        user_lineups = df_cloud_lineups[
            df_cloud_lineups["username"] == st.session_state.user
        ]
        if not user_lineups.empty:
          has_history = True
          if game_date in user_lineups["date"].values:
            last_lineup = user_lineups[
                user_lineups["date"] == game_date
            ].iloc[-1]
          else:
            last_lineup = user_lineups.iloc[-1]

      c_options = ["-- 請選擇 --"] + catchers
      if_options = ["-- 請選擇 --"] + infielders
      of_options = ["-- 請選擇 --"] + outfielders
      dh_options = ["-- 請選擇 --"] + all_batters

      idx_c = (
          get_index(c_options, last_lineup.get("catcher", ""))
          if has_history
          else 0
      )
      idx_if1 = (
          get_index(if_options, last_lineup.get("if1", "")) if has_history else 0
      )
      idx_if2 = (
          get_index(if_options, last_lineup.get("if2", "")) if has_history else 0
      )
      idx_if3 = (
          get_index(if_options, last_lineup.get("if3", "")) if has_history else 0
      )
      idx_if4 = (
          get_index(if_options, last_lineup.get("if4", "")) if has_history else 0
      )
      idx_of1 = (
          get_index(of_options, last_lineup.get("of1", "")) if has_history else 0
      )
      idx_of2 = (
          get_index(of_options, last_lineup.get("of2", "")) if has_history else 0
      )
      idx_of3 = (
          get_index(of_options, last_lineup.get("of3", "")) if has_history else 0
      )
      idx_dh = (
          get_index(dh_options, last_lineup.get("dh", "")) if has_history else 0
      )

      if has_history:
        st.caption(
            "💡 已為您自動帶入歷史提交陣容，可直接修改或點擊下方按鈕儲存。"
        )

      with st.form("position_lineup_form"):
        c_select = st.selectbox(
            "捕手 (1人)", options=c_options, index=idx_c, key="pos_c"
        )
        if1 = st.selectbox(
            "內野手 1", options=if_options, index=idx_if1, key="pos_if1"
        )
        if2 = st.selectbox(
            "內野手 2", options=if_options, index=idx_if2, key="pos_if2"
        )
        if3 = st.selectbox(
            "內野手 3", options=if_options, index=idx_if3, key="pos_if3"
        )
        if4 = st.selectbox(
            "內野手 4", options=if_options, index=idx_if4, key="pos_if4"
        )
        of1 = st.selectbox(
            "外野手 1", options=of_options, index=idx_of1, key="pos_of1"
        )
        of2 = st.selectbox(
            "外野手 2", options=of_options, index=idx_of2, key="pos_of2"
        )
        of3 = st.selectbox(
            "外野手 3", options=of_options, index=idx_of3, key="pos_of3"
        )
        dh_select = st.selectbox(
            "指定打擊 (DH)", options=dh_options, index=idx_dh, key="pos_dh"
        )

        submit = st.form_submit_button("儲存今日陣容")

        if submit:
          selected_all = [
              c_select,
              if1,
              if2,
              if3,
              if4,
              of1,
              of2,
              of3,
              dh_select,
          ]
          if "-- 請選擇 --" in selected_all:
            st.error("⚠️ 還有位置尚未選擇球員！")
          elif len(selected_all) != len(set(selected_all)):
            st.error("⚠️ 陣容中有重複選擇的球員，請重新檢查！")
          else:
            now_str = now_tw.strftime("%Y-%m-%d %H:%M:%S")

            row_data = [st.session_state.user, game_date, *selected_all, now_str]
            if write_to_sheet("lineups", row_data):
              st.success(
                  f"🎉 {game_date} 的守備陣容已成功上傳！（提交時間：{now_str}）"
              )
              st.rerun()

    st.divider()
    st.subheader(f"👀 {game_date} 所有玩家已提交陣容")

    if not df_cloud_lineups.empty and "date" in df_cloud_lineups.columns:
      df_cloud_lineups["date"] = df_cloud_lineups["date"].astype(str)
      df_display = df_cloud_lineups[df_cloud_lineups["date"] == game_date]

      if not df_display.empty and "username" in df_display.columns:
        df_display = df_display.drop_duplicates(
            subset=["username", "date"], keep="last"
        )

      is_locked = now_tw < game_cutoff_dt

      rename_dict = {
          "username": "玩家",
          "date": "比賽日期",
          "catcher": "捕手",
          "if1": "內野1",
          "if2": "內野2",
          "if3": "內野3",
          "if4": "內野4",
          "of1": "外野1",
          "of2": "外野2",
          "of3": "外野3",
          "dh": "指定打擊",
          "submit_time": "最後提交時間",
      }
      df_display = df_display.rename(columns=rename_dict)

      if is_locked and not df_display.empty:
        st.info(
            f"🔒 尚未到達截止時間（{c_h:02d}:{c_m:02d}），所有玩家選擇的球員保密中！僅顯示提交狀態。"
        )
        mask_cols = [
            "捕手",
            "內野1",
            "內野2",
            "內野3",
            "內野4",
            "外野1",
            "外野2",
            "外野3",
            "指定打擊",
        ]
        for col in mask_cols:
          if col in df_display.columns:
            df_display[col] = "🔒 保密中"
    else:
      df_display = pd.DataFrame()

    if df_display.empty:
      st.info(f"尚無玩家提交 {game_date} 的陣容。")
    else:
      st.dataframe(df_display, use_container_width=True, hide_index=True)

  # TAB 2: 排行榜 (新增：當日球員 MVP & 戰犯表現榜)
  with tab2:
    df_cloud_scores = read_sheet("daily_scores")
    df_player_stats = read_sheet("player_stats")

    # 1. 最上方：單日玩家得分榜 (切換選單)
    st.subheader("📅 單日玩家得分榜")
    selected_score_date = None

    if not df_cloud_scores.empty and "score" in df_cloud_scores.columns:
      df_s = df_cloud_scores.copy()
      df_s["score"] = pd.to_numeric(df_s["score"], errors="coerce")
      df_s["date"] = df_s["date"].astype(str)

      available_dates = sorted(df_s["date"].unique().tolist(), reverse=True)

      if available_dates:
        selected_score_date = st.selectbox(
            "選擇要查看的比賽日期",
            options=available_dates,
            key="select_score_date",
        )

        df_day_s = df_s[df_s["date"] == selected_score_date].copy()
        df_day_s = (
            df_day_s.drop_duplicates(subset=["username", "date"], keep="last")
            .sort_values(by="score", ascending=False)
            .reset_index(drop=True)
        )
        df_day_s.index = df_day_s.index + 1

        rename_daily = {
            "username": "玩家",
            "date": "比賽日期",
            "score": "當日得分",
        }
        df_s_display = df_day_s.rename(columns=rename_daily)

        st.dataframe(df_s_display, use_container_width=True)
      else:
        st.info("尚無單日結算紀錄。")
    else:
      st.info("尚無單日結算紀錄。")

    # 2. 中間第一區：🔥 選定日期之【球員表現榜】(Top 3 & Bottom 3)
    if (
        selected_score_date
        and not df_player_stats.empty
        and "score" in df_player_stats.columns
    ):
      st.divider()
      st.subheader(f"⚡ {selected_score_date} 球員表現榜")

      df_ps = df_player_stats.copy()
      df_ps["score"] = pd.to_numeric(df_ps["score"], errors="coerce")
      df_ps["date"] = df_ps["date"].astype(str)

      df_ps_day = df_ps[df_ps["date"] == selected_score_date].sort_values(
          by="score", ascending=False
      )

      if not df_ps_day.empty:
        p_col1, p_col2 = st.columns(2)

        # 最高分 Top 3 球員
        with p_col1:
          st.markdown("##### 🚀 當日最高得分球員 (Top 3)")
          top_3 = df_ps_day.head(3).reset_index(drop=True)
          top_3.index = top_3.index + 1
          top_3_display = top_3.rename(
              columns={"name": "球員姓名", "score": "貢獻分數"}
          )[["球員姓名", "貢獻分數"]]
          st.dataframe(top_3_display, use_container_width=True)

        # 最低分 Bottom 3 球員 (包含負分)
        with p_col2:
          st.markdown("##### 🧊 當日最低得分球員 (Bottom 3)")
          bot_3 = (
              df_ps_day.tail(3)
              .sort_values(by="score", ascending=True)
              .reset_index(drop=True)
          )
          bot_3.index = bot_3.index + 1
          bot_3_display = bot_3.rename(
              columns={"name": "球員姓名", "score": "貢獻分數"}
          )[["球員姓名", "貢獻分數"]]
          st.dataframe(bot_3_display, use_container_width=True)

    # 3. 中間第二區：賽季玩家累計總積分榜
    if not df_cloud_scores.empty and "score" in df_cloud_scores.columns:
      st.divider()
      st.subheader("🏆 賽季玩家累計總積分榜")
      df_total_base = df_s.drop_duplicates(
          subset=["username", "date"], keep="last"
      )
      df_total = (
          df_total_base.groupby("username")["score"]
          .sum()
          .reset_index()
          .sort_values(by="score", ascending=False)
          .reset_index(drop=True)
      )
      df_total.index = df_total.index + 1
      df_total.columns = ["玩家", "累計總積分"]

      st.dataframe(df_total, use_container_width=True)

    # 4. 最底下：🔥 夢幻聯賽大會紀錄 (Hall of Fame)
    st.divider()
    st.subheader("🔥 夢幻聯賽大會紀錄 (Hall of Fame)")

    rec_col1, rec_col2 = st.columns(2)

    if not df_cloud_scores.empty and "score" in df_cloud_scores.columns:
      df_s_rec = df_cloud_scores.copy()
      df_s_rec["score"] = pd.to_numeric(df_s_rec["score"], errors="coerce")
      max_user_row = df_s_rec.sort_values(by="score", ascending=False).iloc[0]

      u_top_score = int(max_user_row["score"])
      u_top_name = max_user_row["username"]
      u_top_date = max_user_row["date"]

      rec_col1.metric(
          label="👑 玩家單日史上最高分",
          value=f"{u_top_score} 分",
          delta=f"{u_top_name} ({u_top_date})",
      )
    else:
      rec_col1.metric(
          label="👑 玩家單日史上最高分", value="-- 分", delta="尚無紀錄"
      )

    if not df_player_stats.empty and "score" in df_player_stats.columns:
      df_p_rec = df_player_stats.copy()
      df_p_rec["score"] = pd.to_numeric(df_p_rec["score"], errors="coerce")
      max_p_row = df_p_rec.sort_values(by="score", ascending=False).iloc[0]

      p_top_score = int(max_p_row["score"])
      p_top_name = max_p_row["name"]
      p_top_date = max_p_row["date"]

      rec_col2.metric(
          label="⚾ 單一球員單場最高得分",
          value=f"{p_top_score} 分",
          delta=f"{p_top_name} ({p_top_date})",
      )
    else:
      rec_col2.metric(
          label="⚾ 單一球員單場最高得分", value="-- 分", delta="尚無紀錄"
      )

  # TAB 3: 計分規則
  with tab3:
    st.header("📜 阿凜的中職夢幻聯賽 - 計分規則總覽")

    col1, col2 = st.columns(2)

    with col1:
      st.subheader("⚾ 基本打擊得分")
      df_basic = pd.DataFrame({
          "打擊項目": [
              "一壘安打",
              "二壘安打",
              "三壘安打",
              "全壘打",
              "四死球",
              "打點",
              "得分",
              "盜壘",
          ],
          "代號": ["1B", "2B", "3B", "HR", "BB", "RBI", "R", "SB"],
          "得分計算法": [
              "+3 分",
              "+6 分",
              "+10 分",
              "+15 分",
              "+2 分",
              "+2 分",
              "+2 分",
              "+3 分",
          ],
      })
      st.dataframe(df_basic, use_container_width=True, hide_index=True)

      st.subheader("⚠️ 負分扣分項目")
      df_deduct = pd.DataFrame({
          "扣分項目": ["三振", "雙殺打"],
          "代號": ["SO", "GDP"],
          "扣分計算法": ["-3 分", "-5 分"],
      })
      st.dataframe(df_deduct, use_container_width=True, hide_index=True)

    with col2:
      st.subheader("🌟 特殊里程碑與成就加碼")
      df_bonus = pd.DataFrame({
          "成就類別": [
              "單場雙安",
              "猛打賞 (3H)",
              "鐵支 (4H)",
              "單場 5 安打",
              "單場 6 安打",
              "雙響砲 (2HR)",
              "三響砲 (3HR)",
              "單場雙盜壘 (2SB+)",
              "完全打擊",
          ],
          "額外加碼得分": [
              "+4 分",
              "+7 分",
              "+12 分",
              "+20 分",
              "+30 分",
              "+24 分",
              "+40 分",
              "+8 分",
              "+50 分",
          ],
      })
      st.dataframe(df_bonus, use_container_width=True, hide_index=True)

    st.info("💡 註：所有特殊里程碑加碼項目均採【階梯式不重複採計】。")

  # TAB 4: 管理者專區
  with tab4:
    st.header("⚙️ 管理者數據匯入與比賽設定")

    if not st.session_state.get("is_admin", False):
      st.error(
          f"🔒 權限不足：請於左側邊欄輸入正確的管理員驗證碼（密碼）以解鎖！"
      )
    else:
      st.subheader("⏰ 調整指定日期比賽截止時間 (如假日提前開打)")
      set_date = st.date_input(
          "選擇調整日期", value=now_tw.date(), key="cfg_date"
      ).strftime("%Y-%m-%d")

      curr_h, curr_m = get_cutoff_time_for_date(set_date)
      from datetime import time

      set_time = st.time_input(
          "設定比賽截止時間", value=time(curr_h, curr_m), key="cfg_time"
      )

      if st.button("💾 儲存截止時間設定"):
        time_str = set_time.strftime("%H:%M")
        if write_to_sheet("settings", [set_date, time_str]):
          st.success(f"🎉 已將 {set_date} 的比賽截止時間更新為：{time_str}！")
          st.rerun()
        else:
          st.error("❌ 儲存失敗，請確認 Google Apps Script 設定！")

      st.divider()

      st.subheader("📊 每日比賽數據匯入與分數結算")
      target_date = st.date_input(
          "選擇要結算的比賽日期", value=now_tw.date(), key="admin_date"
      ).strftime("%Y-%m-%d")

      default_csv_example = """name,1B,2B,3B,HR,RBI,BB,SB,SO,R,GDP
陳傑憲,2,1,0,0,1,1,1,0,2,0
張育成,0,0,0,1,2,0,0,1,1,0
吉力吉撈·鞏冠,1,1,1,1,4,0,0,0,2,0"""

      raw_data = st.text_area(
          "貼上數據區域", value=default_csv_example, height=200
      )

      if st.button("🚀 開始計算並結算此日得分"):
        try:
          from io import StringIO

          df_stats = pd.read_csv(StringIO(raw_data))
          df_stats["calculated_score"] = df_stats.apply(
              calculate_player_score, axis=1
          )
          player_score_dict = dict(
              zip(df_stats["name"], df_stats["calculated_score"])
          )

          for _, p_row in df_stats.iterrows():
            write_to_sheet("player_stats", [
                p_row["name"],
                target_date,
                int(p_row["calculated_score"]),
            ])

          df_cloud_lineups = read_sheet("lineups")
          if not df_cloud_lineups.empty and "date" in df_cloud_lineups.columns:
            df_cloud_lineups["date"] = df_cloud_lineups["date"].astype(str)
            df_target = df_cloud_lineups[
                df_cloud_lineups["date"] == target_date
            ]
            df_target = df_target.drop_duplicates(
                subset=["username", "date"], keep="last"
            )
          else:
            df_target = pd.DataFrame()

          if df_target.empty:
            st.warning(f"⚠️ {target_date} 沒有任何玩家提交陣容！")
          else:
            success_count = 0
            for _, row in df_target.iterrows():
              u_name = row["username"]
              players_selected = [
                  row["catcher"],
                  row["if1"],
                  row["if2"],
                  row["if3"],
                  row["if4"],
                  row["of1"],
                  row["of2"],
                  row["of3"],
                  row["dh"],
              ]
              total_team_score = sum(
                  [player_score_dict.get(p, 0) for p in players_selected]
              )

              score_row = [u_name, target_date, total_team_score]
              if write_to_sheet("daily_scores", score_row):
                success_count += 1

            st.success(
                f"🎉 {target_date} 數據結算完成！成功更新 {success_count} 位玩家與全體球員之雲端紀錄。"
            )
            st.rerun()

            st.write("### 當日球員得分明細：")
            st.dataframe(
                df_stats[["name", "calculated_score"]], use_container_width=True
            )

        except Exception as e:
          st.error(f"❌ 數據格式有誤！錯誤訊息: {e}")