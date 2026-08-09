import sqlite3
import pandas as pd
import streamlit as st

# 1. 初始化資料庫 (包含使用者、陣容、每日球員數據、玩家每日得分)
conn = sqlite3.connect("fantasy.db", check_same_thread=False)
c = conn.cursor()

c.execute(
    "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password"
    " TEXT)"
)
c.execute("""
    CREATE TABLE IF NOT EXISTS lineups (
        username TEXT,
        date TEXT,
        catcher TEXT,
        if1 TEXT, if2 TEXT, if3 TEXT, if4 TEXT,
        of1 TEXT, of2 TEXT, of3 TEXT,
        dh TEXT,
        PRIMARY KEY(username, date)
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS daily_scores (
        username TEXT,
        date TEXT,
        score REAL,
        PRIMARY KEY(username, date)
    )
""")
conn.commit()

st.set_page_config(page_title="CPBL 夢幻聯賽", page_icon="⚾", layout="wide")
st.title("⚾ CPBL 夢幻聯賽")

# 2. 帳號狀態與側邊欄
if "user" not in st.session_state:
  st.session_state.user = None

st.sidebar.title("👤 帳號系統")

if st.session_state.user is None:
  menu = st.sidebar.radio("選擇操作", ["登入帳號", "註冊新帳號"])
  username = st.sidebar.text_input("使用者名稱 / 暱稱")
  password = st.sidebar.text_input("密碼", type="password")

  if menu == "註冊新帳號":
    if st.sidebar.button("完成註冊"):
      if username and password:
        try:
          c.execute("INSERT INTO users VALUES (?, ?)", (username, password))
          conn.commit()
          st.sidebar.success("註冊成功！請切換至『登入帳號』進行登入。")
        except:
          st.sidebar.error("這個帳號名稱已被註冊過了！")
      else:
        st.sidebar.warning("請填寫帳號與密碼。")

  elif menu == "登入帳號":
    if st.sidebar.button("登入"):
      c.execute(
          "SELECT * FROM users WHERE username=? AND password=?",
          (username, password),
      )
      if c.fetchone():
        st.session_state.user = username
        st.rerun()
      else:
        st.sidebar.error("帳號或密碼錯誤！")
else:
  st.sidebar.write(f"目前登入：**{st.session_state.user}**")
  if st.sidebar.button("登出"):
    st.session_state.user = None
    st.rerun()


# 3. 球員單日得分計算核心邏輯
def calculate_player_score(row):
  # 基礎數據解析
  b1 = int(row.get("1B", 0))
  b2 = int(row.get("2B", 0))
  b3 = int(row.get("3B", 0))
  hr = int(row.get("HR", 0))
  rbi = int(row.get("RBI", 0))
  bb = int(row.get("BB", 0))
  sb = int(row.get("SB", 0))
  so = int(row.get("SO", 0))

  # 基礎得分計算
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

  # 特殊成就加碼
  total_hits = b1 + b2 + b3 + hr

  # 完全打擊 (1B, 2B, 3B, HR 各至少 1 支)
  if b1 >= 1 and b2 >= 1 and b3 >= 1 and hr >= 1:
    score += 30

  # 安打里程碑成就 (階梯式不重複採計)
  if total_hits >= 6:
    score += 20
  elif total_hits == 5:
    score += 12
  elif total_hits == 4:
    score += 7
  elif total_hits == 3:
    score += 4

  return score


# 4. 主頁面（分為四個頁籤）
if st.session_state.user is None:
  st.info("👈 請先於左側邊欄【登入】或【註冊帳號】，即可開始安排陣容！")
else:
  tab1, tab2, tab3, tab4 = st.tabs(
      ["📋 安排今日陣容", "🏆 玩家積分排行榜", "📜 計分規則說明", "⚙️ 管理者數據匯入"]
  )

  # 讀取 CSV 並依守備位置過濾
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
    st.subheader(f"請安排 {game_date} 的守備陣容 (1捕 + 4內 + 3外 + 1DH)")

    if df_players.empty:
      st.error("⚠️ 找不到 players.csv 或內容格式不正確，請檢查檔案！")
    else:
      with st.form("position_lineup_form"):
        st.markdown("### 🥊 捕手 (選 1 人)")
        c_select = st.selectbox(
            "捕手", options=["-- 請選擇 --"] + catchers, key="pos_c"
        )

        st.markdown("### ⚾ 內野手 (選 4 人)")
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

        st.markdown("### 🏃 外野手 (選 3 人)")
        of1 = st.selectbox(
            "外野手 1", options=["-- 請選擇 --"] + outfielders, key="pos_of1"
        )
        of2 = st.selectbox(
            "外野手 2", options=["-- 請選擇 --"] + outfielders, key="pos_of2"
        )
        of3 = st.selectbox(
            "外野手 3", options=["-- 請選擇 --"] + outfielders, key="pos_of3"
        )

        st.markdown("### 💥 指定打擊 / DH (全打者皆可選 1 人)")
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
            c.execute(
                """
                            INSERT OR REPLACE INTO lineups 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                (st.session_state.user, game_date, *selected_all),
            )
            conn.commit()
            st.success(f"🎉 {game_date} 的守備陣容已成功儲存！")

  # TAB 2: 排行榜
  with tab2:
    st.subheader("🏆 賽季玩家累計總積分榜")
    df_total = pd.read_sql_query(
        """
            SELECT username AS 玩家, SUM(score) AS 總積分 
            FROM daily_scores 
            GROUP BY username 
            ORDER BY 總積分 DESC
        """,
        conn,
    )
    if df_total.empty:
      st.info("尚無結算成績。")
    else:
      st.dataframe(df_total, use_container_width=True)

    st.divider()
    st.subheader("📅 單日玩家得分明細")
    df_daily = pd.read_sql_query(
        """
            SELECT date AS 日期, username AS 玩家, score AS 當日得分 
            FROM daily_scores 
            ORDER BY date DESC, score DESC
        """,
        conn,
    )
    if df_daily.empty:
      st.info("尚無單日結算紀錄。")
    else:
      st.dataframe(df_daily, use_container_width=True)

  # TAB 3: 計分規則
  with tab3:
    st.header("📜 CPBL 夢幻聯賽 - 計分規則總覽")

    col1, col2 = st.columns(2)
    with col1:
      st.subheader("⚾ 基礎打擊項目")
      st.markdown("""
            * **一壘安打 ($1B$)**：`+3 分`
            * **二壘安打 ($2B$)**：`+6 分`
            * **三壘安打 ($3B$)**：`+10 分`
            * **全壘打 ($HR$)**：`+15 分`
            * **四死球保送 ($BB$)**：`+2 分`
            * **打點 ($RBI$)**：`每 1 分打點 +2 分`
            * **盜壘成功 ($SB$)**：`+3 分`
            * **被三振 ($SO$)**：`-3 分`
            """)

    with col2:
      st.subheader("🔥 特殊成就額外加碼")
      st.markdown("""
            * **猛打賞 (單場 3 安打)**：額外 `+4 分`
            * **鐵支 (單場 4 安打)**：額外 `+7 分`
            * **五支安打 (單場 5 安打)**：額外 `+12 分`
            * **六支安打 (單場 6 安打)**：額外 `+20 分`
            * **完全打擊 (單場達成 1B+2B+3B+HR)**：額外 `+30 分`
            
            *(註：安打成就採最高階梯採計，不重複疊加)*
            """)

  # TAB 4: 管理者數據匯入
  with tab4:
    st.header("⚙️ 每日比賽數據匯入與分數結算")

    target_date = st.date_input("選擇要結算的比賽日期", key="admin_date").strftime(
        "%Y-%m-%d"
    )

    st.markdown("""
        **請在下方貼上當天的打擊數據 CSV 文字：**  
        格式需求：`name,1B,2B,3B,HR,RBI,BB,SB,SO`
        """)

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

        # 計算每位球員當天得分
        df_stats["calculated_score"] = df_stats.apply(
            calculate_player_score, axis=1
        )
        player_score_dict = dict(
            zip(df_stats["name"], df_stats["calculated_score"])
        )

        # 抓取該日期所有玩家的陣容
        c.execute(
            "SELECT username, catcher, if1, if2, if3, if4, of1, of2, of3, dh"
            " FROM lineups WHERE date=?",
            (target_date,),
        )
        user_lineups = c.fetchall()

        if not user_lineups:
          st.warning(f"⚠️ {target_date} 沒有任何玩家提交陣容！")
        else:
          # 計算每位玩家的隊伍總分
          for row in user_lineups:
            u_name = row[0]
            players_selected = row[1:]
            total_team_score = sum(
                [player_score_dict.get(p, 0) for p in players_selected]
            )

            # 寫入 daily_scores
            c.execute(
                "INSERT OR REPLACE INTO daily_scores VALUES (?, ?, ?)",
                (u_name, target_date, total_team_score),
            )

          conn.commit()
          st.success(f"🎉 {target_date} 數據結算完成！排行榜已更新。")

          st.write("### 當日球員得分明細：")
          st.dataframe(
              df_stats[["name", "calculated_score"]], use_container_width=True
          )

      except Exception as e:
        st.error(f"❌ 數據格式有誤，請檢查欄位！錯誤訊息: {e}")