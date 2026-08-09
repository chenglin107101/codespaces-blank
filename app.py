import pandas as pd
import streamlit as st
from st_gsheets_connection import GSheetsConnection

st.set_page_config(page_title="阿凜的中職夢幻聯賽", page_icon="⚾", layout="wide")
st.title("⚾ 阿凜的中職夢幻聯賽")

ADMIN_USER = "謝正凜"

# 建立 Google 試算表連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 側邊欄：簡單暱稱輸入
st.sidebar.title("👤 玩家身分驗證")
user_input = st.sidebar.text_input("請輸入您的姓名 / 暱稱", value="")

if user_input.strip() != "":
  st.session_state.user = user_input.strip()
  st.sidebar.success(f"目前身分：**{st.session_state.user}**")
  if st.session_state.user == ADMIN_USER:
    st.sidebar.info("🔑 管理員權限已啟用")
else:
  st.session_state.user = None


# 3. 球員單日得分計算核心邏輯
def calculate_player_score(row):
  b1 = int(row.get("1B", 0))
  b2 = int(row.get("2B", 0))
  b3 = int(row.get("3B", 0))
  hr = int(row.get("HR", 0))
  rbi = int(row.get("RBI", 0))
  bb = int(row.get("BB", 0))
  sb = int(row.get("SB", 0))
  so = int(row.get("SO", 0))

  score = (
      (b1 * 3)
      + (b2 * 6)
      + (b3 * 10)
      + (hr * 15)
      + (bb * 2)
      + (rbi * 2)
      + (sb * 3)
      - (so * 3)
  )
  total_hits = b1 + b2 + b3 + hr

  if b1 >= 1 and b2 >= 1 and b3 >= 1 and hr >= 1:
    score += 30
  if total_hits >= 6:
    score += 20
  elif total_hits == 5:
    score += 12
  elif total_hits == 4:
    score += 7
  elif total_hits == 3:
    score += 4

  return score


# 4. 主頁面內容
if st.session_state.user is None:
  st.info("👈 請先於左側邊欄【輸入您的姓名 / 暱稱】，即可開始使用！")
else:
  tab1, tab2, tab3, tab4 = st.tabs(
      ["📋 安排今日陣容", "🏆 玩家積分排行榜", "📜 計分規則說明", "⚙️ 管理者數據匯入"]
  )

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
    game_date = st.date_input("選擇比賽日期", key="lineup_date").strftime(
        "%Y-%m-%d"
    )
    st.subheader(
        f"【{st.session_state.user}】請安排 {game_date} 的守備陣容 (1捕 + 4內 +"
        " 3外 + 1DH)"
    )

    if df_players.empty:
      st.error("⚠️ 找不到 players.csv 或內容格式不正確，請檢查檔案！")
    else:
      with st.form("position_lineup_form"):
        c_select = st.selectbox(
            "捕手 (1人)", options=["-- 請選擇 --"] + catchers, key="pos_c"
        )
        if1 = st.selectbox(
            "內野手 1", options=["-- 請選擇 --"] + infielders, key="pos_if1"
        )
        if2 = st.selectbox(
            "內野手 2", options=["-- 請選擇 --"] + infielders, key="pos_if2"
        )
        if3 = st.selectbox(
            "內野手 3", options=["-- 請選擇 --"] + infielders, key="pos_if3"
        )
        if4 = st.selectbox(
            "內野手 4", options=["-- 請選擇 --"] + infielders, key="pos_if4"
        )
        of1 = st.selectbox(
            "外野手 1", options=["-- 請選擇 --"] + outfielders, key="pos_of1"
        )
        of2 = st.selectbox(
            "外野手 2", options=["-- 請選擇 --"] + outfielders, key="pos_of2"
        )
        of3 = st.selectbox(
            "外野手 3", options=["-- 請選擇 --"] + outfielders, key="pos_of3"
        )
        dh_select = st.selectbox(
            "指定打擊 (DH)",
            options=["-- 請選擇 --"] + all_batters,
            key="pos_dh",
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
            # 寫入 Google 試算表
            df_existing = conn.read(worksheet="lineups", ttl="0")
            new_data = pd.DataFrame([{
                "username": st.session_state.user,
                "date": game_date,
                "catcher": c_select,
                "if1": if1,
                "if2": if2,
                "if3": if3,
                "if4": if4,
                "of1": of1,
                "of2": of2,
                "of3": of3,
                "dh": dh_select,
            }])

            # 覆蓋或新增
            if not df_existing.empty:
              df_existing = df_existing[
                  ~(
                      (df_existing["username"] == st.session_state.user)
                      & (df_existing["date"] == game_date)
                  )
              ]
              df_updated = pd.concat([df_existing, new_data], ignore_index=True)
            else:
              df_updated = new_data

            conn.update(worksheet="lineups", data=df_updated)
            st.success(f"🎉 {game_date} 的守備陣容已成功上傳！")

    st.divider()
    st.subheader(f"👀 {game_date} 所有玩家已提交陣容")
    try:
      df_all_lineups = conn.read(worksheet="lineups", ttl="0")
      if not df_all_lineups.empty:
        df_filtered = df_all_lineups[df_all_lineups["date"] == game_date]
        if df_filtered.empty:
          st.info(f"尚無玩家提交 {game_date} 的陣容。")
        else:
          st.dataframe(df_filtered, use_container_width=True)
      else:
        st.info(f"尚無玩家提交 {game_date} 的陣容。")
    except:
      st.info("尚未讀取到陣容資料。")

  # TAB 2: 排行榜
  with tab2:
    st.subheader("📅 單日玩家得分榜")
    try:
      df_scores = conn.read(worksheet="daily_scores", ttl="0")
      if df_scores.empty:
        st.info("尚無單日結算紀錄。")
      else:
        st.dataframe(
            df_scores.sort_values(
                by=["date", "score"], ascending=[False, False]
            ),
            use_container_width=True,
        )

        st.divider()
        st.subheader("🏆 賽季玩家累計總積分榜")
        df_total = (
            df_scores.groupby("username")["score"]
            .sum()
            .reset_index()
            .sort_values(by="score", ascending=False)
        )
        df_total.columns = ["玩家", "總積分"]
        st.dataframe(df_total, use_container_width=True)
    except:
      st.info("尚無結算成績。")

  # TAB 3: 計分規則
  with tab3:
    st.header("📜 阿凜的中職夢幻聯賽 - 計分規則總覽")
    st.markdown("""
        * **一壘安打 ($1B$)**：`+3 分` | **二壘安打 ($2B$)**：`+6 分` | **三壘安打 ($3B$)**：`+10 分` | **全壘打 ($HR$)**：`+15 分`
        * **四死球 ($BB$)**：`+2 分` | **打點 ($RBI$)**：`+2 分` | **盜壘 ($SB$)**：`+3 分` | **三振 ($SO$)**：`-3 分`
        * **猛打賞(3H)**：`+4` | **鐵支(4H)**：`+7` | **5H**：`+12` | **6H**：`+20` | **完全打擊**：`+30`
        """)

  # TAB 4: 管理者結算
  with tab4:
    st.header("⚙️ 每日比賽數據匯入與分數結算")

    if st.session_state.user != ADMIN_USER:
      st.error(f"🔒 權限不足：只有管理者【{ADMIN_USER}】可進行結算！")
    else:
      target_date = st.date_input("選擇要結算的比賽日期", key="admin_date").strftime(
          "%Y-%m-%d"
      )

      default_csv_example = """name,1B,2B,3B,HR,RBI,BB,SB,SO
陳傑憲,2,1,0,0,1,1,1,0
張育成,0,0,0,1,2,0,0,1
吉力吉撈·鞏冠,1,1,1,1,4,0,0,0"""

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

          df_lineups = conn.read(worksheet="lineups", ttl="0")
          df_target = df_lineups[df_lineups["date"] == target_date]

          if df_target.empty:
            st.warning(f"⚠️ {target_date} 沒有任何玩家提交陣容！")
          else:
            new_scores = []
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
              new_scores.append(
                  {"username": u_name, "date": target_date, "score": total_team_score}
              )

            df_new_scores = pd.DataFrame(new_scores)
            try:
              df_existing_scores = conn.read(worksheet="daily_scores", ttl="0")
              if not df_existing_scores.empty:
                df_existing_scores = df_existing_scores[
                    ~(df_existing_scores["date"] == target_date)
                ]
                df_score_updated = pd.concat(
                    [df_existing_scores, df_new_scores], ignore_index=True
                )
              else:
                df_score_updated = df_new_scores
            except:
              df_score_updated = df_new_scores

            conn.update(worksheet="daily_scores", data=df_score_updated)
            st.success(f"🎉 {target_date} 數據結算完成！排行榜已更新。")

            st.write("### 當日球員得分明細：")
            st.dataframe(
                df_stats[["name", "calculated_score"]], use_container_width=True
            )

        except Exception as e:
          st.error(f"❌ 數據格式有誤！錯誤訊息: {e}")