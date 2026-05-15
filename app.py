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

    h1 { font-size: 38px !important; font-weight: 800 !important; text-align: center; margin-bottom: 25px !important; }

    .cycle-header {

        background-color: #007BFF; color: white; padding: 10px 15px; border-radius: 10px;

        font-weight: bold; margin: 25px 0 15px 0; font-size: 18px; text-align: center;

    }

    div.stButton > button { background-color: #007BFF !important; color: white !important; border-radius: 8px !important; font-weight: bold !important; height: 3.5em !important; }

    .record-card { border-radius: 15px; padding: 22px; margin-bottom: 15px; border: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 0px 4px 12px rgba(0,0,0,0.05); }

    .weight-box { font-size: 24px; font-weight: 800; color: #007BFF !important; }

    </style>

    """, unsafe_allow_html=True)



conn = st.connection("gsheets", type=GSheetsConnection)



# --- 데이터 로드 (영문 시트 이름 사용) ---

def load_data():

    try:

        # 'Records' 시트에서 일일 기록 로드

        main_df = conn.read(worksheet="Records", ttl=0)

        # 'Cycles' 시트에서 차수 정보 로드

        cycle_df = conn.read(worksheet="Cycles", ttl=0)

        return main_df, cycle_df

    except Exception as e:

        # 시트 로드 실패 시 빈 데이터프레임 반환

        return None, None



df, c_df = load_data()



st.title("오늘 하루 기록")



tab1, tab2, tab3 = st.tabs(["기록하기", "항암 차수", "요약보기"])



# --- [TAB 1] 기록하기 ---

with tab1:

    st.subheader("오늘의 상태 기록")

    curr_date = datetime.now().strftime("%Y년 %m월 %d일")

    st.write(f"기록 날짜: {curr_date}")

    

    options = ["약 복용", "주사 맞음", "복용 안함"]

    morning = st.radio("아침 기록", options, horizontal=True)

    evening = st.radio("저녁 기록", options, horizontal=True)

    

    # 마지막 몸무게 찾기

    last_w = 55.0

    if df is not None and not df.empty:

        try:

            v_w = pd.to_numeric(df['몸무게'], errors='coerce').dropna()

            if not v_w.empty: last_w = float(v_w.iloc[-1])

        except: pass



    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)

    pain = st.select_slider("통증 정도 (1-10)", options=list(range(1, 11)), value=1)

    notes = st.text_area("메모", placeholder="특이사항을 입력하세요.")



    if st.button("기록 저장하기", use_container_width=True):

        new_row = pd.DataFrame([{

            "날짜": datetime.now().strftime('%Y-%m-%d'),

            "아침기록": morning, "저녁기록": evening,

            "몸무게": weight, "통증": pain, "메모": notes

        }])

        updated_df = pd.concat([df, new_row], ignore_index=True) if df is not None else new_row

        conn.update(worksheet="Records", data=updated_df)

        st.success("기록이 저장되었습니다.")

        st.rerun()



# --- [TAB 2] 항암 차수 ---

with tab2:

    st.subheader("항암 주기 등록")

    with st.form("cycle_form"):

        c_num = st.number_input("차수 (숫자만)", min_value=1, step=1)

        c_date = st.date_input("차수 시작일")

        if st.form_submit_button("차수 시작 저장"):

            new_c = pd.DataFrame([{"차수": int(c_num), "시작일": c_date.strftime('%Y-%m-%d')}])

            updated_c = pd.concat([c_df, new_c], ignore_index=True) if c_df is not None else new_c

            conn.update(worksheet="Cycles", data=updated_c)

            st.success(f"{c_num}차 항암이 등록되었습니다.")

            st.rerun()



# --- [TAB 3] 요약보기 ---

with tab3:

    if df is not None and not df.empty:

        # 데이터 정리

        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')

        display_df = df.dropna(subset=['날짜']).sort_values('날짜', ascending=False)

        

        # 차수 정보 정리

        if c_df is not None and not c_df.empty:

            c_df['시작일'] = pd.to_datetime(c_df['시작일'], errors='coerce')

            c_df = c_df.dropna(subset=['시작일']).sort_values('시작일', ascending=False)



        current_bar = None

        for i, row in display_df.iterrows():

            this_cycle = "이전 기록"

            if c_df is not None and not c_df.empty:

                match = c_df[c_df['시작일'] <= row['날짜']]

                if not match.empty:

                    this_cycle = f"항암 {int(match.iloc[0]['차수'])}차 진행 중"



            if this_cycle != current_bar:

                st.markdown(f'<div class="cycle-header">{this_cycle}</div>', unsafe_allow_html=True)

                current_bar = this_cycle



            st.markdown(f"""

            <div class="record-card">

                <div style="display: flex; justify-content: space-between;">

                    <span style="font-weight:bold;">{row['날짜'].strftime('%m월 %d일')}</span>

                    <span class="weight-box">{row['몸무게']}kg</span>

                </div>

                <div style="margin-top:8px;">아침: {row['아침기록']} | 저녁: {row['저녁기록']}</div>

                <div style="font-size:14px; color:gray;">통증: {row['통증']} / 10</div>

                <div style="margin-top:10px;">{row['메모'] if str(row['메모']) != 'nan' else ''}</div>

            </div>

            """, unsafe_allow_html=True)

    else:

        st.info("데이터가 없습니다. 구글 시트의 탭 이름이 'Records'인지 확인해 주세요.")

