import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="어머니 건강 일기", layout="centered")

# --- UI 스타일링 (CSS) ---
st.markdown("""
    <style>
    /* 1. 배경 및 기본 텍스트 색상 (화이트 테마 강제) */
    .stApp { background-color: #FFFFFF; }
    
    /* 전체 글자색을 아주 진한 회색(#212121)으로 */
    p, span, label, .stMarkdown { 
        color: #212121 !important; 
        font-size: 17px !important;
        font-weight: 500;
    }
    
    /* 2. 포인트 컬러 (블루) 설정 */
    h1, h2, h3 { color: #0047AB !important; } /* 진한 블루 */
    
    /* 3. 입력창 및 체크박스 스타일 조정 */
    .stCheckbox [data-testid="stWidgetLabel"] p {
        font-size: 18px !important;
        color: #212121 !important;
    }
    
    /* 4. 요약 카드 디자인 개선 */
    .record-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid #E0E4E8;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
    }
    
    /* 카드 내 항목별 상태 라벨 (아침약, 저녁약 등) */
    .status-label {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
        margin-right: 5px;
        margin-bottom: 5px;
    }
    .status-on { background-color: #E3F2FD; color: #0047AB; border: 1px solid #BBDEFB; }
    .status-off { background-color: #F5F5 faces; color: #9E9E9E; border: 1px solid #E0E0E0; }
    
    /* 메모 섹션 스타일 */
    .memo-box {
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px dashed #E0E4E8;
        color: #424242;
        font-style: italic;
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

tab1, tab2 = st.tabs(["📝 기록하기", "📊 요약보기"])

with tab1:
    st.subheader(f"{datetime.now().strftime('%Y년 %m월 %d일')}")
    
    st.write("오늘 약 복용과 주사 여부를 체크해주세요.")
    
    # 체크박스를 조금 더 크게 보이게 배치
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
    
    st.write("오늘 통증 정도 (1:편안함 ~ 10:힘듦)")
    pain = st.select_slider("통증", options=list(range(1, 11)), value=1, label_visibility="collapsed")
    
    st.divider()
    
    notes = st.text_area("메모 (기분이나 증상)", placeholder="의사 선생님께 전할 말씀을 적어주세요.")

    # 버튼 색상을 블루로 변경 (type="primary"는 기본적으로 설정된 테마색을 따름)
    if st.button("기록 저장하기", use_container_width=True, type="primary"):
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
        st.success("저장되었습니다! 내일도 힘내세요.")
        st.balloons()

with tab2:
    st.subheader("최근 기록 요약")
    if not df.empty:
        recent_df = df.tail(10).iloc[::-1]
        
        for _, row in recent_df.iterrows():
            try:
                raw_date = pd.to_datetime(row['날짜'])
                formatted_date = raw_date.strftime('%m월 %d일')
            except:
                formatted_date = str(row['날짜'])
            
            # 약 복용 여부에 따른 스타일 클래스 결정
            m_cls = "status-on" if row['아침약'] == "O" else "status-off"
            e_cls = "status-on" if row['저녁약'] == "O" else "status-off"
            i_cls = "status-on" if row['주사'] == "O" else "status-off"

            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <span style="font-size: 20px; font-weight: bold; color: #0047AB;">{formatted_date}</span>
                    <span style="font-size: 16px; color: #212121; background: #F1F3F5; padding: 2px 8px; border-radius: 5px;">{row['몸무게']} kg</span>
                </div>
                <div style="margin-bottom: 10px;">
                    <span class="status-label {m_cls}">아침약 {row['아침약']}</span>
                    <span class="status-label {e_cls}">저녁약 {row['저녁약']}</span>
                    <span class="status-label {i_cls}">항암주사 {row['주사']}</span>
                </div>
                <div style="font-size: 15px; color: #495057;">
                    <b>통증 수준:</b> <span style="color:#0047AB; font-weight:bold;">{row['통증']}</span> / 10
                </div>
                <div class="memo-box">
                    {row['메모'] if row['메모'] else '기록된 메모가 없습니다.'}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("아직 기록이 없습니다.")
