import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- [강력 저장된 UI 스타일] ---
st.markdown("""
    <style>
    :root { --primary-color: #007BFF !important; }
    h1 { font-size: 40px !important; font-weight: 800 !important; text-align: center; margin-bottom: 30px !important; }
    
    .cycle-header {
        background-color: #007BFF;
        color: white;
        padding: 8px 15px;
        border-radius: 10px;
        font-weight: bold;
        margin: 25px 0 15px 0;
        font-size: 18px;
        text-align: center;
        box-shadow: 0px 4px 10px rgba(0, 123, 255, 0.2);
    }

    div.stButton > button { background-color: #007BFF !important; color: white !important; border-radius: 8px !important; font-weight: bold !important; height: 3.5em !important; }
    div[data-baseweb="tab-highlight-spinner"] { background-color: #007BFF !important; }
    div[data-baseweb="tab"] div[aria-selected="true"] p { color: #007BFF !important; }
    .record-card { border-radius: 15px; padding: 22px; margin-bottom: 20px; border: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 0px 4px 12px rgba(0,0,0,0.05); }
    .weight-box { font-size: 26px; font-weight: 800; color: #007BFF !important; }
    </style>
    """, unsafe_allow_html=True)

# 시트 연결 (서비스 계정 인증 필수)
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 로드 함수 (에러 방지 강화)
def load_data():
    try:
        # worksheet 이름을 명시적으로 지정
        main_df = conn.read(worksheet="Records", ttl=0)
    except:
        main_df = pd.DataFrame(columns=["날짜", "아침기록", "저녁기록", "몸무게", "통증", "메모"])
    
    try:
        c_df = conn.read(worksheet="차수정보", ttl=0)
    except:
        c_df = pd.DataFrame(columns=["차수", "시작일"])
        
    return main_df, c_df

df, cycle_df = load_data()

st.title("오늘 하루 기록")
tab1, tab2, tab3 = st.tabs(["기록하기", "항암 차수", "요약보기"])

# --- [TAB 1] 기록하기 ---
with tab1:
    st.subheader("오늘의 상태 기록")
    curr_date_str = datetime.now().strftime("%Y년 %m월 %d일")
    st.markdown(f'<p style="font-size:25px; font-weight:bold;">{curr_date_str}</p>', unsafe_allow_html=True)
    
    options = ["약 복용", "주사 맞음", "복용 안함"]
    morning = st.radio("아침 기록", options, horizontal=True)
    evening = st.radio("저녁 기록", options, horizontal=True)
    
    # 마지막 몸무게 자동 로드
    last_w = 55.0
    if df is not None and not df.empty:
        try:
            v_w = pd.to_numeric(df['몸무게'], errors='coerce').dropna()
            if not v_w.empty: last_w = float(v_w.iloc[-1])
        except: pass

    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)
    pain = st.select_slider("통증 정도", options=list(range(1, 11)), value=1)
    notes = st.text_area("메모", placeholder="특이사항을 적어주세요.")

    if st.button("기록 저장하기", use_container_width=True):
        new_data = pd.DataFrame([{
            "날짜": datetime.now().strftime('%Y-%m-%d'), 
            "아침기록": morning, "저녁기록": evening, 
            "몸무게": weight, "통증": pain, "메모": notes
        }])
        updated_df = pd.concat([df, new_data], ignore_index=True) if df is not None else new_data
        # worksheet 명시 필수
        conn.update(worksheet="Records", data=updated_df)
        st.success("오늘의 기록이 저장되었습니다!")
        st.rerun()

# --- [TAB 2] 항암 차수 설정 ---
with tab2:
    st.subheader("새로운 항암 차수 등록")
    with st.form("cycle_form"):
        new_cycle = st.number_input("진행할 차수 (숫자만)", min_value=1, step=1)
        start_date = st.date_input("차수 시작 날짜")
        if st.form_submit_button("차수 시작 기록하기"):
            new_cycle_data = pd.DataFrame([{"차수": int(new_cycle), "시작일": start_date.strftime('%Y-%m-%d')}])
            updated_c_df = pd.concat([cycle_df, new_cycle_data], ignore_index=True) if cycle_df is not None else new_cycle_data
            conn.update(worksheet="차수정보", data=updated_c_df)
            st.success(f"{new_cycle}차 항암이 등록되었습니다!")
            st.rerun()

# --- [TAB 3] 요약보기 ---
with tab3:
    if df is not None and not df.empty:
        # 날짜 정렬 및 처리
        pdf = df.copy()
        pdf['날짜'] = pd.to_datetime(pdf['날짜'], errors='coerce')
        pdf = pdf.dropna(subset=['날짜']).sort_values('날짜', ascending=False)
        
        # 차수 데이터 처리
        cdf = cycle_df.copy() if cycle_df is not None and not cycle_df.empty else None
        if cdf is not None:
            cdf['시작일'] = pd.to_datetime(cdf['시작일'], errors='coerce')
            cdf = cdf.dropna(subset=['시작일']).sort_values('시작일', ascending=False)

        current_display_cycle = None
        for i, row in pdf.iterrows():
            applicable_cycle = "기록 외"
            if cdf is not None:
                match = cdf[cdf['시작일'] <= row['날짜']]
                if not match.empty:
                    applicable_cycle = f"항암 {int(match.iloc[0]['차수'])}차 진행 중"

            if applicable_cycle != current_display_cycle:
                st.markdown(f'<div class="cycle-header">{applicable_cycle}</div>', unsafe_allow_html=True)
                current_display_cycle = applicable_cycle

            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="font-size:19px; font-weight:bold;">{row['날짜'].strftime('%m월 %d일')}</span>
                    <span class="weight-box">{row['몸무게']} <small style="font-size:16px;">kg</small></span>
                </div>
                <div style="font-size:17px; margin-top:10px;">아침: {row['아침기록']} | 저녁: {row['저녁기록']}</div>
                <div style="font-size:15px; opacity:0.8; margin-top:5px;">통증: {row['통증']} / 10</div>
                <div style="margin-top:10px; font-size:16px;">{row['메모'] if str(row['메모']) != 'nan' and row['메모'] != '' else ''}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("아직 기록이 없습니다.")
