import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 모바일 및 테마 설정
st.set_page_config(page_title="어머니 건강 일기", layout="centered")

# CSS 스타일링 (화이트 배경 및 카드 디자인)
st.markdown("""
    <style>
    .stApp { background-color: white; }
    p, b, label, .stMarkdown { color: #262730; font-size: 16px !important; }
    h1, h2, h3 { color: #1f77b4 !important; }
    .record-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 5px solid #1f77b4;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
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
    try:
        last_weight = float(df.iloc[-1]['몸무게'])
    except:
        last_weight = 55.0
else:
    last_weight = 55.0

tab1, tab2 = st.tabs(["기록하기", "요약보기"])

with tab1:
    st.subheader(f"{datetime.now().strftime('%Y년 %m월 %d일')}")
    
    st.write("오늘 복용하거나 맞으신 주사를 체크해주세요.")
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
    
    st.write("오늘 몸은 얼마나 불편하셨나요? (1:편안함 ~ 10:힘듦)")
    pain = st.select_slider("통증 정도", options=list(range(1, 11)), value=1)
    
    st.divider()
    
    notes = st.text_area("메모 (기분이나 증상)", placeholder="하고 싶은 말씀을 적어주세요.")

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
    st.subheader("최근 기록")
    if not df.empty:
        # 최신 기록순으로 정렬
        recent_df = df.tail(10).iloc[::-1]
        
        for _, row in recent_df.iterrows():
            # 날짜 형식을 더 똑똑하게 읽어오도록 수정 (pd.to_datetime 사용)
            try:
                raw_date = pd.to_datetime(row['날짜'])
                formatted_date = raw_date.strftime('%m월 %d일')
            except:
                formatted_date = str(row['날짜']) # 변환 실패 시 원본 그대로 표시
            
            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <b style="font-size:18px; color:#1f77b4;">{formatted_date}</b>
                    <span style="font-size:14px; color:#666;">몸무게: {row['몸무게']}kg</span>
                </div>
                <div style="text-align: center; background: white; border-radius: 5px; padding: 5px; margin-bottom: 8px; border: 1px solid #eee;">
                    약: 아침({row['아침약']}) 저녁({row['저녁약']}) | 주사: {row['주사']} | 통증: {row['통증']}/10
                </div>
                <div style="font-size: 15px; color: #444;">
                    {row['메모'] if row['메모'] else '기록된 메모가 없습니다.'}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("아직 기록이 없습니다.")
