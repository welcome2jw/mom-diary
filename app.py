import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- UI 스타일링 ---
st.markdown("""
    <style>
    :root { --primary-color: #007BFF !important; }
    h1 { font-size: 40px !important; font-weight: 800 !important; text-align: center; margin-bottom: 30px !important; }
    .cycle-header {
        background-color: #007BFF; color: white; padding: 10px 15px; border-radius: 10px;
        font-weight: bold; margin: 25px 0 15px 0; font-size: 18px; text-align: center;
        box-shadow: 0px 4px 10px rgba(0, 123, 255, 0.1);
    }
    div.stButton > button { background-color: #007BFF !important; color: white !important; border-radius: 8px !important; font-weight: bold !important; height: 3.5em !important; }
    div[data-baseweb="tab-highlight-spinner"] { background-color: #007BFF !important; }
    div[data-baseweb="tab"] div[aria-selected="true"] p { color: #007BFF !important; }
    .record-card { border-radius: 15px; padding: 22px; margin-bottom: 20px; border: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 0px 4px 12px rgba(0,0,0,0.05); }
    .weight-box { font-size: 26px; font-weight: 800; color: #007BFF !important; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 데이터 로드 (상태기록 과 차수정보 명시) ---
try:
    # 메인 기록 시트 이름을 '상태기록'으로 지정
    df = conn.read(worksheet="상태기록", ttl=0) 
    # 차수 정보 시트 이름을 '차수정보'로 지정
    cycle_df = conn.read(worksheet="차수정보", ttl=0)
except Exception as e:
    df = pd.DataFrame(columns=["날짜", "아침기록", "저녁기록", "몸무게", "통증", "메모"])
    cycle_df = pd.DataFrame(columns=["차수", "시작일"])

st.title("오늘 하루 기록")

tab1, tab2, tab3 = st.tabs(["기록하기", "항암 차수", "요약보기"])

# --- [TAB 1] 기록하기 ---
with tab1:
    st.subheader("오늘의 상태 기록")
    curr_date = datetime.now().strftime("%Y년 %m월 %d일")
    st.markdown(f'<p style="font-size:25px; font-weight:bold;">{curr_date}</p>', unsafe_allow_html=True)
    
    options = ["약 복용", "주사 맞음", "복용 안함"]
    morning = st.radio("아침 기록", options, horizontal=True, key="m_radio")
    evening = st.radio("저녁 기록", options, horizontal=True, key="e_radio")
    
    # 마지막 몸무게 가져오기 로직
    last_w = 55.0
    if not df.empty:
        try:
            v_w = pd.to_numeric(df['몸무게'], errors='coerce').dropna()
            if not v_w.empty: last_w = float(v_w.iloc[-1])
        except: pass

    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)
    pain = st.select_slider("통증 정도", options=list(range(1, 11)), value=1)
    notes = st.text_area("메모", placeholder="특이사항을 적어주세요.")

    if st.button("기록 저장하기", use_container_width=True):
        new_row = pd.DataFrame([{
            "날짜": datetime.now().strftime('%Y-%m-%d'),
            "아침기록": morning, "저녁기록": evening,
            "몸무게": weight, "통증": pain, "메모": notes
        }])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        # 저장할 때도 '상태기록'에 저장하도록 명시
        conn.update(worksheet="상태기록", data=updated_df)
        st.success("기록이 안전하게 저장되었습니다!")
        st.rerun()

# --- [TAB 2] 항암 차수 설정 ---
with tab2:
    st.subheader("새로운 항암 차수 등록")
    with st.form("cycle_setting"):
        c_num = st.number_input("진행 차수 (숫자)", min_value=1, step=1)
        c_date = st.date_input("시작 날짜", value=datetime.now())
        if st.form_submit_button("차수 시작 기록"):
            new_c = pd.DataFrame([{"차수": int(c_num), "시작일": c_date.strftime('%Y-%m-%d')}])
            updated_c = pd.concat([cycle_df, new_c], ignore_index=True)
            conn.update(worksheet="차수정보", data=updated_c)
            st.success(f"{c_num}차 항암 주기가 등록되었습니다.")
            st.rerun()

# --- [TAB 3] 요약보기 ---
with tab3:
    if not df.empty:
        # 데이터 정리
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜']).sort_values('날짜', ascending=False)
        
        if not cycle_df.empty:
            cycle_df['시작일'] = pd.to_datetime(cycle_df['시작일'], errors='coerce')
            cycle_df = cycle_df.dropna(subset=['시작일']).sort_values('시작일', ascending=False)

        current_bar = None
        
        for i, row in df.iterrows():
            this_cycle = "이전 기록"
            if not cycle_df.empty:
                match = cycle_df[cycle_df['시작일'] <= row['날짜']]
                if not match.empty:
                    this_cycle = f"항암 {int(match.iloc[0]['차수'])}차 진행 중"

            if this_cycle != current_bar:
                st.markdown(f'<div class="cycle-header">{this_cycle}</div>', unsafe_allow_html=True)
                current_bar = this_cycle

            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="font-size:18px; font-weight:bold;">{row['날짜'].strftime('%m월 %d일')}</span>
                    <span class="weight-box">{row['몸무게']} <small style="font-size:15px;">kg</small></span>
                </div>
                <div style="margin-top:10px; font-size:16px;">아침: {row['아침기록']} | 저녁: {row['저녁기록']}</div>
                <div style="font-size:15px; color:#666; margin-top:5px;">통증: {row['통증']} / 10</div>
                <div style="margin-top:10px; font-size:15px; line-height:1.5;">{row['메모'] if row['메모'] != 'X' else ''}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("기록된 데이터가 없습니다. 구글 시트의 '상태기록' 탭을 확인해 주세요.")
