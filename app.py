import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 모바일 및 테마 설정
st.set_page_config(page_title="어머니 건강 일기", layout="centered")

# CSS를 이용한 스타일링: 화이트 배경 강제 및 테이블 가독성 향상
st.markdown("""
    <style>
    /* 전체 배경을 밝게 */
    .stApp { background-color: white; }
    
    /* 텍스트 색상 및 폰트 크기 조정 */
    p, b, label, .stMarkdown { color: #262730; font-size: 16px !important; }
    h1, h2, h3 { color: #1f77b4 !important; }
    
    /* 입력 칸 가독성 */
    .stCheckbox label { font-weight: bold; }
    
    /* 요약 보기 카드 스타일 */
    .record-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 5px solid #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기
try:
    df = conn.read(ttl=0)
except:
    df = pd.DataFrame(columns=["날짜", "아침약", "저녁약", "주사", "몸무게", "통증", "메모"])

st.title("☀️ 어머니의 하루 기록")

# 전날 몸무게 가져오기
if not df.empty and "몸무게" in df.columns:
    last_weight = float(df.iloc[-1]['몸무게'])
else:
    last_weight = 55.0

tab1, tab2 = st.tabs(["기록하기", "요약보기"])

with tab1:
    st.subheader(f"{datetime.now().strftime('%Y년 %m월 %d일')}")
    
    # 아침약/저녁약/주사 병행 가능하도록 체크박스로 통합
    st.write("오늘 복용하거나 맞으신 주사가 있다면 체크해주세요.")
    col1, col2, col3 = st.columns(3)
    
    m_pill, e_pill, injection = "X", "X", "X"
    with col1:
        if st.checkbox("아침 약"): m_pill = "O"
    with col2:
        if st.checkbox("저녁 약"): e_pill = "O"
    with col3:
        if st.checkbox("항암 주사"): injection = "O"

    st.divider()

    # 몸무게
    weight = st.number_input("오늘 몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_weight, step=0.1)
    
    st.divider()
    
    # 통증 스케일
    st.write("오늘 몸은 얼마나 불편하셨나요? (1:편안함 ~ 10:힘듦)")
    pain = st.select_slider("통증 정도", options=list(range(1, 11)), value=1, label_visibility="collapsed")
    
    st.divider()
    
    notes = st.text_area("메모 (기분이나 증상)", placeholder="선생님께 하실 말씀을 적어주세요.")

    if st.button("저장하기", use_container_width=True, type="primary"):
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
        st.success("저장되었습니다!")
        st.balloons()

with tab2:
    st.subheader("최근 기록 요약")
    if not df.empty:
        # 최근 기록 5개만 카드 형태로 표시 (모바일 가독성 최강)
        recent_df = df.tail(5).iloc[::-1] # 최신순
        
        for _, row in recent_df.iterrows():
            # 날짜 형식 예쁘게 변환 (2026-05-15 -> 05월 15일)
            date_obj = datetime.strptime(row['날짜'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m월 %d일')
            
            with st.container():
                st.markdown(f"""
                <div class="record-card">
                    <b style="font-size:18px;">📅 {formatted_date}</b><br>
                    💊 약: 아침({row['아침약']}) 저녁({row['저녁약']}) | 💉 주사: {row['주사']}<br>
                    ⚖️ 몸무게: {row['몸무게']}kg | 📉 통증: {row['통증']}/10<br>
                    📝 메모: {row['메모']}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("아직 기록이 없습니다.")
