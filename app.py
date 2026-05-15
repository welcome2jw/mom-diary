import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- UI 스타일링 유지 ---
st.markdown("""
    <style>
    :root { --primary-color: #007BFF !important; }
    h1 { font-size: 40px !important; font-weight: 800 !important; text-align: center; }
    .cycle-header { background-color: #007BFF; color: white; padding: 10px; border-radius: 10px; text-align: center; margin: 20px 0; }
    .record-card { border-radius: 15px; padding: 20px; margin-bottom: 15px; border: 1px solid #eee; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- [강력한 데이터 로드 & 진단 로직] ---
def get_data():
    try:
        # 캐시를 완전히 무시하고 상태기록 시트를 가져옴
        df = conn.read(worksheet="상태기록", ttl=0)
        # 차수정보 시트 가져옴
        cdf = conn.read(worksheet="차수정보", ttl=0)
        return df, cdf
    except Exception as e:
        st.error(f"시트를 읽는 중 오류 발생: {e}")
        return None, None

df_raw, cdf_raw = get_data()

st.title("오늘 하루 기록")

tab1, tab2, tab3 = st.tabs(["기록하기", "항암 차수", "요약보기"])

# --- [TAB 1/2 생략 - 로직 동일] ---
# (기존 코드의 기록하기/항암차수 부분과 동일하므로 요약보기 해결에 집중하겠습니다)

with tab3:
    if df_raw is not None and not df_raw.empty:
        # 1. 데이터 복사 및 전처리
        df = df_raw.copy()
        
        # 날짜 컬럼을 강제로 datetime 객체로 변환
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        
        # 몸무게/통증 숫자 변환
        df['몸무게'] = pd.to_numeric(df['몸무게'], errors='coerce').fillna(0)
        df['통증'] = pd.to_numeric(df['통증'], errors='coerce').fillna(0)
        
        # 날짜가 유효한 데이터만 필터링 후 정렬
        display_df = df.dropna(subset=['날짜']).sort_values('날짜', ascending=False)

        # 2. 차수 정보 처리
        if cdf_raw is not None and not cdf_raw.empty:
            cdf = cdf_raw.copy()
            cdf['시작일'] = pd.to_datetime(cdf['시작일'], errors='coerce')
            cdf = cdf.dropna(subset=['시작일']).sort_values('시작일', ascending=False)
        else:
            cdf = pd.DataFrame()

        # 3. 화면 출력
        if not display_df.empty:
            current_bar = None
            for i, row in display_df.iterrows():
                this_cycle = "기록 외"
                if not cdf.empty:
                    match = cdf[cdf['시작일'] <= row['날짜']]
                    if not match.empty:
                        this_cycle = f"항암 {int(match.iloc[0]['차수'])}차 진행 중"

                if this_cycle != current_bar:
                    st.markdown(f'<div class="cycle-header">{this_cycle}</div>', unsafe_allow_html=True)
                    current_bar = this_cycle

                st.markdown(f"""
                <div class="record-card">
                    <b>{row['날짜'].strftime('%Y-%m-%d')}</b> | 몸무게: {row['몸무게']}kg | 통증: {row['통증']}<br>
                    아침: {row['아침기록']} | 저녁: {row['저녁기록']}<br>
                    메모: {row['메모']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("유효한 날짜 형식을 찾을 수 없습니다. 시트의 '날짜' 열을 확인해 주세요.")
            
    else:
        st.error("시트에서 데이터를 불러오지 못했습니다.")
        
    # --- [시스템 진단 정보] ---
    with st.expander("🛠️ 시스템 진단 정보 (문제가 계속될 때 확인)"):
        st.write("1. 읽어온 시트 컬럼명:", df_raw.columns.tolist() if df_raw is not None else "없음")
        st.write("2. 데이터 샘플 (첫 3행):")
        st.dataframe(df_raw.head(3) if df_raw is not None else "데이터 없음")
