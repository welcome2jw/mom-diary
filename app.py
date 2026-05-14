import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- UI 스타일링 (시스템 테마 호환 + 블루 포인트) ---
st.markdown("""
    <style>
    /* 대제목: 가운데 정렬 및 폰트 확대 */
    h1 { 
        font-size: 45px !important; 
        font-weight: 800 !important;
        text-align: center;
        margin-bottom: 30px !important;
    }
    
    /* 기록하기 탭의 날짜 확대 및 간격 확보 */
    .input-date-text {
        font-size: 32px !important;
        font-weight: bold !important;
        margin-bottom: 25px !important;
    }

    /* --- 포인트 컬러 (Blue) 적용 --- */
    
    /* 1. 버튼: 파란 배경 + 흰색 글자 */
    div.stButton > button {
        background-color: #007BFF !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        height: 3.5em !important;
        font-weight: bold !important;
    }
    
    /* 2. 탭(Tabs) 선택 시 빨간색 라인 -> 파란색으로 변경 */
    div[data-baseweb="tab-highlight-spinner"] {
        background-color: #007BFF !important;
    }
    
    /* 탭 텍스트 선택 시 색상 */
    div[data-baseweb="tab"] div[aria-selected="true"] {
        color: #007BFF !important;
    }
    
    /* 3. 슬라이더(통증 수치) 핸들 및 트랙 */
    div[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
        background-color: #007BFF !important;
        border: 2px solid #007BFF !important;
    }
    div[data-testid="stSlider"] [data-baseweb="slider"] [aria-valuemax] {
        background: #007BFF !important;
    }

    /* 요약 카드 디자인 */
    .record-card {
        border-radius: 15px;
        padding: 22px;
        margin-bottom: 20px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
    }
    
    .card-date {
        font-size: 19px !important; 
        font-weight: bold;
    }
    
    .weight-box {
        font-size: 26px;
        font-weight: 800;
        color: #007BFF !important;
    }

    .status-text {
        font-size: 17px;
        margin-top: 12px;
    }
    
    .pain-text {
        font-size: 16px;
        margin-top: 5px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
        opacity: 0.8;
    }

    .memo-text {
        margin-top: 12px;
        font-size: 16px;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(ttl=0)
    df = df.fillna('X').replace(r'^\s*$', 'X', regex=True)
except:
    df = pd.DataFrame(columns=["날짜", "아침약", "저녁약", "주사", "몸무게", "통증", "메모"])

st.title("☀️ 오늘 하루 기록")

if not df.empty and "몸무게" in df.columns:
    try: last_weight = float(df.iloc[-1]['몸무게'])
    except: last_weight = 55.0
else:
    last_weight = 55.0

tab1, tab2 = st.tabs(["기록하기", "요약보기"])

with tab1:
    # 큰 날짜 및 간격
    st.markdown(f'<p class="input-date-text">{datetime.now().strftime("%Y년 %m월 %d일")}</p>', unsafe_allow_html=True)
    
    st.write("오늘의 복용 및 주사 여부")
    col1, col2, col3 = st.columns(3)
    m_pill, e_pill, injection = "X", "X", "X"
    with col1:
        if st.checkbox("아침 약"): m_pill = "O"
    with col2:
        if st.checkbox("저녁 약"): e_pill = "O"
    with col3:
        if st.checkbox("항암 주사"): injection = "O"

    st.divider()
    st.write("오늘의 몸무게 (kg)")
    weight = st.number_input("몸무게 조정", min_value=30.0, max_value=120.0, value=last_weight, step=0.1, label_visibility="collapsed")
    
    st.divider()
    st.write("오늘의 통증 정도 (1~10)")
    pain = st.select_slider("통증", options=list(range(1, 11)), value=1, label_visibility="collapsed")
    
    st.divider()
    notes = st.text_area("메모 (기분이나 증상)", placeholder="오늘 하루는 어떠셨나요?")

    if st.button("기록 저장하기", use_container_width=True):
        new_row = pd.DataFrame([{
            "날짜": datetime.now().strftime('%Y-%m-%d'),
            "아침약": m_pill, "저녁약": e_pill, "주사": injection,
            "몸무게": weight, "통증": pain, "메모": notes
        }])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.success("기록이 저장되었습니다.")
        st.balloons()

with tab2:
    if not df.empty:
        recent_df = df.copy()
        recent_df['몸무게'] = pd.to_numeric(recent_df['몸무게'], errors='coerce').fillna(0)
        display_df = recent_df.tail(10).iloc[::-1]
        
        for i, row in display_df.iterrows():
            try:
                formatted_date = pd.to_datetime(row['날짜']).strftime('%m월 %d일')
            except:
                formatted_date = str(row['날짜'])
            
            prev_idx = i - 1
            diff_text = ""
            if prev_idx in recent_df.index:
                diff = row['몸무게'] - recent_df.loc[prev_idx, '몸무게']
                if diff != 0:
                    diff_text = f"<span style='font-size:15px; opacity:0.6;'>({'+' if diff>0 else ''}{diff:.1f}kg)</span>"

            inj_text = f" | 항암주사 {row['주사']}" if row['주사'] == "O" else ""

            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span class="card-date">{formatted_date}</span>
                    <span class="weight-box">{row['몸무게']} <small style="font-size:16px;">kg</small> {diff_text}</span>
                </div>
                <div class="status-text">
                    아침약 {row['아침약']} | 저녁약 {row['저녁약']}{inj_text}
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
