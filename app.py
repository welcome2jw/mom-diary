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
    h1 { font-size: 38px !important; font-weight: 800 !important; text-align: center; }
    .cycle-header { background-color: #007BFF; color: white; padding: 10px; border-radius: 10px; text-align: center; margin: 20px 0; }
    .record-card { border-radius: 15px; padding: 22px; margin-bottom: 15px; border: 1px solid #eee; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .weight-box { font-size: 24px; font-weight: 800; color: #007BFF; }
    </style>
    """, unsafe_allow_html=True)

# 연결 이름을 "gsheets_v2"로 변경하여 캐시를 강제로 초기화합니다.
conn = st.connection("gsheets_v2", type=GSheetsConnection)

def load_all_data():
    try:
        # 캐시 보존 시간을 0으로 설정하여 매번 새로 읽어옵니다.
        records = conn.read(worksheet="Records", ttl=0)
        cycles = conn.read(worksheet="Cycles", ttl=0)
        return records, cycles
    except Exception as e:
        return None, None

df, c_df = load_all_data()

st.title("오늘 하루 기록")

tab1, tab2, tab3 = st.tabs(["기록하기", "항암 차수", "요약보기"])

# --- [TAB 1] 기록하기 ---
with tab1:
    st.subheader("오늘의 상태 기록")
    curr_date = datetime.now().strftime("%Y-%m-%d")
    
    morning = st.radio("아침 기록", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
    evening = st.radio("저녁 기록", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
    
    last_w = 55.0
    if df is not None and not df.empty and "몸무게" in df.columns:
        try:
            v_w = pd.to_numeric(df['몸무게'], errors='coerce').dropna()
            if not v_w.empty: last_w = float(v_w.iloc[-1])
        except: pass

    weight = st.number_input("몸무게 (kg)", value=last_w, step=0.1)
    pain = st.select_slider("통증", options=list(range(1, 11)), value=1)
    notes = st.text_area("메모")

    if st.button("저장하기", use_container_width=True):
        new_data = pd.DataFrame([{
            "날짜": curr_date, "아침기록": morning, "저녁기록": evening,
            "몸무게": weight, "통증": pain, "메모": notes
        }])
        # 데이터가 없을 경우를 대비해 처리
        full_df = pd.concat([df, new_data], ignore_index=True) if df is not None else new_data
        conn.update(worksheet="Records", data=full_df)
        st.success("저장 완료!")
        st.rerun()

# --- [TAB 2] 항암 차수 ---
with tab2:
    st.subheader("차수 정보 입력")
    with st.form("cycle_f"):
        c_n = st.number_input("차수", min_value=1)
        c_d = st.date_input("시작일")
        if st.form_submit_button("저장"):
            new_c = pd.DataFrame([{"차수": int(c_n), "시작일": c_d.strftime('%Y-%m-%d')}])
            full_c = pd.concat([c_df, new_c], ignore_index=True) if c_df is not None else new_c
            conn.update(worksheet="Cycles", data=full_c)
            st.success("등록 완료!")
            st.rerun()

# --- [TAB 3] 요약보기 ---
with tab3:
    if df is not None and not df.empty and "날짜" in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        display_df = df.dropna(subset=['날짜']).sort_values('날짜', ascending=False)

        current_bar = None
        for i, row in display_df.iterrows():
            # 차수 매칭 로직
            label = "일반 기록"
            if c_df is not None and not c_df.empty:
                c_df['시작일'] = pd.to_datetime(c_df['시작일'], errors='coerce')
                match = c_df[c_df['시작일'] <= row['날짜']].sort_values('시작일', ascending=False)
                if not match.empty:
                    label = f"항암 {int(match.iloc[0]['차수'])}차 진행"

            if label != current_bar:
                st.markdown(f'<div class="cycle-header">{label}</div>', unsafe_allow_html=True)
                current_bar = label

            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between;">
                    <b>{row['날짜'].strftime('%m월 %d일')}</b>
                    <span class="weight-box">{row['몸무게']}kg</span>
                </div>
                <div style="margin-top:10px;">아침: {row['아침기록']} | 저녁: {row['저녁기록']}</div>
                <div style="font-size:14px; color:gray;">통증: {row['통증']} / 10</div>
                <div style="margin-top:10px;">{row['메모'] if str(row['메모']) != 'nan' else ''}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("시트에 데이터가 없거나 불러오는 중입니다. 잠시만 기다려주세요.")
        # 정말로 안나오면 에러 내용 출력
        if df is None:
            st.error("연결 에러: 시트의 'Records' 탭을 찾을 수 없습니다.")
