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

conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 데이터 로드 및 날짜 포맷 안전 처리
def load_and_fix_data():
    try:
        # worksheet 이름을 명시하지 않으면 첫 번째 탭을 읽습니다.
        main_df = conn.read(ttl=0) 
        # 차수 정보 시트 이름이 '차수정보'인지 확인 필요
        try:
            c_df = conn.read(worksheet="차수정보", ttl=0)
        except:
            c_df = pd.DataFrame(columns=["차수", "시작일"])
        
        # 날짜 포맷 강제 변환 (가장 중요한 부분)
        if not main_df.empty and "날짜" in main_df.columns:
            main_df['날짜'] = pd.to_datetime(main_df['날짜'], errors='coerce', infer_datetime_format=True)
        
        if not c_df.empty and "시작일" in c_df.columns:
            c_df['시작일'] = pd.to_datetime(c_df['시작일'], errors='coerce', infer_datetime_format=True)
            
        return main_df, c_df
    except:
        return pd.DataFrame(columns=["날짜", "아침기록", "저녁기록", "몸무게", "통증", "메모"]), pd.DataFrame(columns=["차수", "시작일"])

df, cycle_df = load_and_fix_data()

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
    if not df.empty:
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
        if st.form_submit_button("차수 시작 기록하기"):
            new_cycle_data = pd.DataFrame([{"차수": int(new_cycle), "시작일": start_date.strftime('%Y-%m-%d')}])
            updated_cycle_df = pd.concat([cycle_df, new_cycle_data], ignore_index=True)
            conn.update(worksheet="차수정보", data=updated_cycle_df)
            st.success(f"{new_cycle}차 항암이 등록되었습니다!")
            st.rerun()

    if not cycle_df.empty:
        st.divider()
        st.write("진행 중인 차수 목록")
        st.dataframe(cycle_df.sort_values("차수", ascending=False), hide_index=True)

# --- [TAB 3] 요약보기 ---
with tab3:
    # 에러 방지를 위해 날짜가 유효한 데이터만 필터링
    valid_df = df.dropna(subset=['날짜']).sort_values('날짜', ascending=False) if not df.empty else pd.DataFrame()
    
    if not valid_df.empty:
        current_display_cycle = None
        
        for i, row in valid_df.iterrows():
            record_date = row['날짜']
            applicable_cycle = "기록 외"
            
            if not cycle_df.empty:
                # 시작일이 유효한지 확인 후 비교
                temp_cycle = cycle_df.dropna(subset=['시작일']).sort_values('시작일', ascending=False)
                match = temp_cycle[temp_cycle['시작일'] <= record_date]
                if not match.empty:
                    applicable_cycle = f"항암 {int(match.iloc[0]['차수'])}차 진행 중"

            if applicable_cycle != current_display_cycle:
                st.markdown(f'<div class="cycle-header">{applicable_cycle}</div>', unsafe_allow_html=True)
                current_display_cycle = applicable_cycle

            formatted_date = record_date.strftime('%m월 %d일')
            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="font-size:19px; font-weight:bold;">{formatted_date}</span>
                    <span class="weight-box">{row['몸무게']} <small style="font-size:16px;">kg</small></span>
                </div>
                <div style="font-size:17px; margin-top:10px;">아침: {row['아침기록']} | 저녁: {row['저녁기록']}</div>
                <div style="font-size:15px; opacity:0.8; margin-top:5px;">통증: {row['통증']} / 10</div>
                <div style="margin-top:10px; font-size:16px;">{row['메모'] if str(row['메모']) != 'nan' and row['메모'] != '' else ''}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("아직 기록이 없거나 날짜 형식을 읽을 수 없습니다. 첫 번째 탭에서 기록을 저장해 보세요.")
