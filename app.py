import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- UI 스타일링 ---
st.markdown("""
    <style>
    h1 { 
        font-size: 40px !important; 
        font-weight: 800 !important;
        text-align: center;
        margin-bottom: 30px !important;
    }
    .input-date-text {
        font-size: 30px !important;
        font-weight: bold !important;
        margin-bottom: 25px !important;
    }
    div.stButton > button {
        background-color: #007BFF !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        height: 3.5em !important;
        font-weight: bold !important;
    }
    div[data-baseweb="tab-highlight-spinner"] {
        background-color: #007BFF !important;
    }
    div[data-baseweb="tab"] div[aria-selected="true"] {
        color: #007BFF !important;
    }
    div[data-testid="stRadio"] > div {
        gap: 10px;
    }
    div[data-testid="stRadio"] label {
        background-color: rgba(128, 128, 128, 0.05);
        padding: 10px 15px;
        border-radius: 8px;
        border: 1px solid rgba(128, 128, 128, 0.1);
        width: 100%;
    }
    .record-card {
        border-radius: 15px;
        padding: 22px;
        margin-bottom: 20px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
    }
    .card-date { font-size: 19px !important; font-weight: bold; }
    .weight-box { font-size: 26px; font-weight: 800; color: #007BFF !important; }
    .status-text { font-size: 17px; margin-top: 12px; font-weight: 500; }
    .pain-text {
        font-size: 16px; margin-top: 5px; padding-bottom: 10px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1); opacity: 0.8;
    }
    .memo-text { margin-top: 12px; font-size: 16px; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 로드 로직 개선
try:
    df = conn.read(ttl=0)
    # 데이터가 비어있지 않은지 확인
    if df is not None and not df.empty:
        df = df.fillna('X').replace(r'^\s*$', 'X', regex=True)
    else:
        df = pd.DataFrame(columns=["날짜", "아침기록", "저녁기록", "몸무게", "통증", "메모"])
except:
    df = pd.DataFrame(columns=["날짜", "아침기록", "저녁기록", "몸무게", "통증", "메모"])

st.title("오늘 하루 기록")

# 기본 몸무게 설정
last_weight = 55.0
if not df.empty and "몸무게" in df.columns:
    try:
        valid_weights = pd.to_numeric(df['몸무게'], errors='coerce').dropna()
        if not valid_weights.empty:
            last_weight = float(valid_weights.iloc[-1])
    except: pass

tab1, tab2 = st.tabs(["기록하기", "요약보기"])

with tab1:
    st.markdown(f'<p class="input-date-text">{datetime.now().strftime("%Y년 %m월 %d일")}</p>', unsafe_allow_html=True)
    
    options = ["약 복용", "주사 맞음", "기록 안함"]
    
    st.write("아침 기록")
    morning_status = st.radio("아침", options, label_visibility="collapsed", key="morning_radio", horizontal=True)
    
    st.write("저녁 기록")
    evening_status = st.radio("저녁", options, label_visibility="collapsed", key="evening_radio", horizontal=True)

    st.divider()
    st.write("오늘의 몸무게 (kg)")
    weight = st.number_input("몸무게", min_value=30.0, max_value=120.0, value=last_weight, step=0.1, label_visibility="collapsed")
    
    st.divider()
    st.write("오늘의 통증 정도 (1~10)")
    pain = st.select_slider("통증", options=list(range(1, 11)), value=1, label_visibility="collapsed")
    
    st.divider()
    notes = st.text_area("메모 (기분이나 증상)", placeholder="오늘 하루는 어떠셨나요?")

    if st.button("기록 저장하기", use_container_width=True):
        new_row = pd.DataFrame([{
            "날짜": datetime.now().strftime('%Y-%m-%d'),
            "아침기록": morning_status,
            "저녁기록": evening_status,
            "몸무게": weight,
            "통증": pain,
            "메모": notes
        }])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.success("기록이 저장되었습니다.")
        st.rerun() # 저장 후 화면 갱신

with tab2:
    if not df.empty:
        recent_df = df.copy()
        
        # [핵심 수정] 날짜 변환 시 에러 처리 강화
        recent_df['날짜'] = pd.to_datetime(recent_df['날짜'], errors='coerce')
        # 변환 실패한 행 제거
        recent_df = recent_df.dropna(subset=['날짜'])
        
        # 몸무게 숫자 변환
        recent_df['몸무게'] = pd.to_numeric(recent_df['몸무게'], errors='coerce').fillna(0)
        
        # 최신순 정렬 후 상위 10개
        display_df = recent_df.sort_values(by='날짜', ascending=False).head(10)
        
        for i, row in display_df.iterrows():
            formatted_date = row['날짜'].strftime('%m월 %d일')
            
            # 몸무게 증감 계산 (정렬 전 원본 인덱스 활용 시 주의)
            diff_text = ""
            current_idx = recent_df.index.get_loc(i)
            if current_idx + 1 < len(recent_df): # 시간순으로 정렬했을 때 이전 데이터가 있는지 확인
                # 실제 시간순 상의 이전 데이터는 정렬된 상태에서 다음 행임
                sorted_all = recent_df.sort_values(by='날짜', ascending=True)
                target_pos = sorted_all.index.get_loc(i)
                if target_pos > 0:
                    prev_w = sorted_all.iloc[target_pos-1]['몸무게']
                    diff = row['몸무게'] - prev_w
                    if diff != 0:
                        diff_text = f"<span style='font-size:15px; opacity:0.6;'>({'+' if diff>0 else ''}{diff:.1f}kg)</span>"

            # 기존 컬럼(아침약/저녁약)과 새 컬럼(아침기록/저녁기록) 호환성 유지
            m_val = row.get('아침기록', row.get('아침약', 'X'))
            e_val = row.get('저녁기록', row.get('저녁약', 'X'))

            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span class="card-date">{formatted_date}</span>
                    <span class="weight-box">{row['몸무게']} <small style="font-size:16px;">kg</small> {diff_text}</span>
                </div>
                <div class="status-text">
                    아침: {m_val} | 저녁: {e_val}
                </div>
                <div class="pain-text">
                    통증 수치: {row['통증']} / 10
                </div>
                <div class="memo-text">
                    {row['메모'] if row['메모'] != 'X' else '기록된 메모가 없습니다.'}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("아직 기록이 없습니다.")
