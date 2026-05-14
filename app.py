import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 모바일 최적화 및 제목 설정
st.set_page_config(page_title="어머니 건강 일기", layout="centered")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0) 

st.title("☀️ 어머니의 하루 기록")

# 전날 몸무게 가져오기 (데이터가 없으면 55.0 기본값)
last_weight = 55.0
if not df.empty:
    last_weight = float(df.iloc[-1]['몸무게'])

tab1, tab2 = st.tabs(["📝 기록하기", "📊 요약보기"])

with tab1:
    st.subheader(f"날짜: {datetime.now().strftime('%Y년 %m월 %d일')}")
    
    # 1. 처치 구분
    mode = st.radio("오늘 복용/처치", ["약 복용", "항암 주사"], horizontal=True)
    
    m_pill, e_pill, injection = "X", "X", "X"
    if mode == "약 복용":
        col1, col2 = st.columns(2)
        with col1:
            if st.checkbox("아침 약"): m_pill = "O"
        with col2:
            if st.checkbox("저녁 약"): e_pill = "O"
    else:
        if st.checkbox("주사 맞음", value=True): injection = "O"

    st.divider()

    # 2. 몸무게 & 통증 (이모티콘 제거 및 심플화)
    weight = st.number_input("오늘 몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_weight, step=0.1)
    pain = st.select_slider("통증 정도 (1:편안함 ~ 10:힘듦)", options=list(range(1, 11)), value=1)
    notes = st.text_area("메모 (기분이나 증상)", placeholder="선생님께 하실 말씀을 적어주세요.")

    if st.button("기록 저장하기", use_container_width=True, type="primary"):
        new_data = pd.DataFrame([{
            "날짜": datetime.now().strftime('%Y-%m-%d'),
            "아침약": m_pill,
            "저녁약": e_pill,
            "주사": injection,
            "몸무게": weight,
            "통증": pain,
            "메모": notes
        }])
        updated_df = pd.concat([df, new_data], ignore_index=True)
        conn.update(data=updated_df)
        st.success("저장되었습니다!")

with tab2:
    st.subheader("최근 기록 요약")
    if not df.empty:
        st.table(df.tail(7)) # 최근 7일치만 깔끔하게 표시