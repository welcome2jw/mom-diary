import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- UI 스타일링 (블루 포인트 & 차수 구분 바 스타일) ---
st.markdown("""
    <style>
    :root { --primary-color: #007BFF !important; }
    h1 { font-size: 40px !important; font-weight: 800 !important; text-align: center; margin-bottom: 30px !important; }
    
    /* 차수 구분 바 스타일 */
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

    /* 기존 UI 유지 */
    div.stButton > button { background-color: #007BFF !important; color: white !important; border-radius: 8px !important; font-weight: bold !important; height: 3.5em !important; }
    div[data-baseweb="tab-highlight-spinner"] { background-color: #007BFF !important; }
    div[data-baseweb="tab"] div[aria-selected="true"] p { color: #007BFF !important; }
    .record-card { border-radius: 15px; padding: 22px; margin-bottom: 20px; border: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 0px 4px 12px rgba(0,0,0,0.05); }
    .weight-box { font-size: 26px; font-weight: 800; color: #007BFF !important; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 데이터 로드 (메인 기록 & 차수 정보)
try:
    df = conn.read(ttl=0) # 기본 시트 (일일 기록)
    cycle_df = conn.read(worksheet="차수정보", ttl=0) # '차수정보'라는 이름의 시트 필요
except:
    df = pd.DataFrame(columns=["날짜", "아침기록", "저녁기록", "몸무게", "통증", "메모"])
    cycle_df = pd.DataFrame(columns=["차수", "시작일"])

st.title("오늘 하루 기록")

# 탭 구성: 기록하기 | 항암 차수 | 요약보기
tab1, tab2, tab3 = st.tabs(["기록하기", "항암 차수", "요약보기"])

# --- [TAB 1] 기록하기 ---
with tab1:
    st.subheader("오늘의 상태 기록")
    curr_date = datetime.now().strftime("%Y년 %m월 %d일")
    st.markdown(f'<p style="font-size:25px; font-weight:bold;">{curr_date}</p>', unsafe_allow_html=True)
    
    options = ["약 복용", "주사 맞음", "복용 안함"]
    morning = st.radio("아침 기록", options, horizontal=True)
    evening = st.radio("저녁 기록", options, horizontal=True)
    
    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=55.0, step=0.1)
    pain = st.select_slider("통증 정도", options=list(range(1, 11)), value=1)
    notes = st.text_area("메모", placeholder="특이사항을 적어주세요.")

    if st.button("기록 저장하기", use_container_width=True):
        new_data = pd.DataFrame([{"날짜": datetime.now().strftime('%Y-%m-%d'), "아침기록": morning, "저녁기록": evening, "몸무게": weight, "통증": pain, "메모": notes}])
        updated_df = pd.concat([df, new_data], ignore_index=True)
        conn.update(data=updated_df)
        st.success("오늘의 기록이 저장되었습니다!")
        st.rerun()

# --- [TAB 2] 항암 차수 설정 ---
with tab2:
    st.subheader("새로운 항암 차수 등록")
    with st.form("cycle_form"):
        new_cycle = st.number_input("진행할 차수 (숫자만)", min_value=1, step=1)
        start_date = st.date_input("차수 시작 날짜", value=datetime.now())
        submit_cycle = st.form_submit_button("차수 시작 기록하기")
        
        if submit_cycle:
            new_cycle_data = pd.DataFrame([{"차수": int(new_cycle), "시작일": start_date.strftime('%Y-%m-%d')}])
            updated_cycle_df = pd.concat([cycle_df, new_cycle_data], ignore_index=True)
            conn.update(worksheet="차수정보", data=updated_cycle_df)
            st.success(f"{new_cycle}차 항암이 등록되었습니다!")
            st.rerun()

    if not cycle_df.empty:
        st.divider()
        st.write("진행 중인 차수 목록")
        st.dataframe(cycle_df.sort_values("차수", ascending=False), hide_index=True)

# --- [TAB 3] 요약보기 (차수별 그룹화) ---
with tab3:
    if not df.empty:
        # 데이터 전처리
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜']).sort_values('날짜', ascending=False)
        
        # 차수 정보 전처리
        if not cycle_df.empty:
            cycle_df['시작일'] = pd.to_datetime(cycle_df['시작일'])
            cycle_df = cycle_df.sort_values('시작일', ascending=False)

        # 기록 출력
        current_display_cycle = None
        
        for i, row in df.iterrows():
            # 이 기록이 어느 차수에 해당되는지 확인
            record_date = row['날짜']
            applicable_cycle = "기록 외"
            
            if not cycle_df.empty:
                # 기록 날짜보다 작거나 같은 시작일 중 가장 최근 차수 찾기
                match = cycle_df[cycle_df['시작일'] <= record_date]
                if not match.empty:
                    applicable_cycle = f"항암 {int(match.iloc[0]['차수'])}차 진행 중"

            # 차수가 바뀌면 구분 바(Bar) 출력
            if applicable_cycle != current_display_cycle:
                st.markdown(f'<div class="cycle-header">{applicable_cycle}</div>', unsafe_allow_html=True)
                current_display_cycle = applicable_cycle

            # 개별 기록 카드
            formatted_date = record_date.strftime('%m월 %d일')
            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="font-size:19px; font-weight:bold;">{formatted_date}</span>
                    <span class="weight-box">{row['몸무게']} <small style="font-size:16px;">kg</small></span>
                </div>
                <div style="font-size:17px; margin-top:10px;">아침: {row['아침기록']} | 저녁: {row['저녁기록']}</div>
                <div style="font-size:15px; opacity:0.8; margin-top:5px;">통증: {row['통증']} / 10</div>
                <div style="margin-top:10px; font-size:16px;">{row['메모'] if row['메모'] != 'X' else ''}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("아직 기록이 없습니다.")
