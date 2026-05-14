import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- UI 스타일링 (CSS) ---
st.markdown("""
    <style>
    /* 1. 배경 및 기본 설정 */
    .stApp { background-color: #FFFFFF; }
    
    /* 대제목 스타일: 폰트 크기를 더 키우고 가운데 정렬 */
    h1 { 
        color: #212121 !important; 
        font-size: 42px !important; /* 32px에서 42px로 확대 */
        font-weight: 800 !important;
        text-align: center;
        margin-bottom: 35px !important;
        white-space: nowrap;
    }
    
    /* 전체 글자색 및 기본 폰트 */
    p, span, label, .stMarkdown { 
        color: #212121 !important; 
        font-size: 18px !important;
    }

    /* 2. 포인트 컬러 변경 (Blue) */
    /* 버튼 색상 강제 변경 */
    div.stButton > button {
        background-color: #007BFF !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        height: 3em !important;
        font-weight: bold !important;
    }
    
    /* 탭 밑줄 색상 변경 */
    div[data-baseweb="tab-highlight-spinner"] {
        background-color: #007BFF !important;
    }
    
    /* 슬라이더(통증 정도) 핸들 색상 변경 */
    div[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
        background-color: #007BFF !important;
        border: 2px solid #007BFF !important;
    }

    /* 3. 요약 카드 디자인 */
    .record-card {
        background-color: #FFFFFF;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 20px;
        border: 1px solid #EEEEEE;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
    }
    
    /* 카드 날짜 폰트 확대 */
    .card-date {
        font-size: 24px !important; /* 19px에서 24px로 확대 */
        font-weight: bold;
        color: #333333;
    }
    
    /* 몸무게 강조 */
    .weight-box {
        font-size: 28px;
        font-weight: 800;
        color: #007BFF; /* 강조색 블루 */
        text-align: right;
    }
    .weight-diff {
        font-size: 15px;
        font-weight: normal;
        color: #888888;
        margin-left: 6px;
    }
    
    /* 항목 텍스트 스타일 */
    .status-text {
        font-size: 17px;
        color: #212121;
        margin-top: 12px;
        padding: 10px 0;
        border-bottom: 1px solid #F1F3F5;
    }
    
    /* 메모 섹션 */
    .memo-content {
        margin-top: 15px;
        font-size: 16px;
        color: #555555;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기 및 전처리
try:
    df = conn.read(ttl=0)
    df = df.fillna('X')
    df = df.replace(r'^\s*$', 'X', regex=True)
except:
    df = pd.DataFrame(columns=["날짜", "아침약", "저녁약", "주사", "몸무게", "통증", "메모"])

st.title("☀️ 오늘 하루 기록")

# 전날 몸무게 가져오기
if not df.empty and "몸무게" in df.columns:
    try:
        last_weight = float(df.iloc[-1]['몸무게'])
    except:
        last_weight = 55.0
else:
    last_weight = 55.0

tab1, tab2 = st.tabs(["기록하기", "요약보기"])

with tab1:
    st.subheader(f"{datetime.now().strftime('%Y년 %m월 %d일')}")
    
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
    weight = st.number_input("조정 버튼으로 맞춰주세요.", min_value=30.0, max_value=120.0, value=last_weight, step=0.1, label_visibility="collapsed")
    
    st.divider()
    
    st.write("오늘의 통증 정도 (1~10)")
    pain = st.select_slider("통증", options=list(range(1, 11)), value=1, label_visibility="collapsed")
    
    st.divider()
    
    notes = st.text_area("메모 (기분이나 증상)", placeholder="오늘 하루는 어떠셨나요?")

    if st.button("기록 저장하기", use_container_width=True):
        new_row = pd.DataFrame([{
            "날짜": datetime.now().strftime('%Y-%m-%d'),
            "아침약": m_pill,
            "저녁약": e_pill,
            "주사": injection,
            "몸무게": weight,
            "통증": pain,
            "메모": notes
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
                raw_date = pd.to_datetime(row['날짜'])
                formatted_date = raw_date.strftime('%m월 %d일')
            except:
                formatted_date = str(row['날짜'])
            
            # 몸무게 증감 계산
            prev_idx = i - 1
            diff_text = ""
            if prev_idx in recent_df.index:
                prev_w = recent_df.loc[prev_idx, '몸무게']
                curr_w = row['몸무게']
                diff = curr_w - prev_w
                if diff > 0:
                    diff_text = f"<span class='weight-diff'>(+{diff:.1f}kg)</span>"
                elif diff < 0:
                    diff_text = f"<span class='weight-diff'>({diff:.1f}kg)</span>"

            # 항암주사 조건부 표시
            injection_text = f" | 항암주사 {row['주사']}" if row['주사'] == "O" else ""

            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span class="card-date">{formatted_date}</span>
                    <span class="weight-box">{row['몸무게']} <small style="font-size:16px;">kg</small>{diff_text}</span>
                </div>
                <div class="status-text">
                    아침약 {row['아침약']} | 저녁약 {row['저녁약']}{injection_text} | 통증 {row['통증']}
                </div>
                <div class="memo-content">
                    {row['메모'] if row['메모'] != 'X' else '메모가 없습니다.'}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("아직 기록이 없습니다.")
