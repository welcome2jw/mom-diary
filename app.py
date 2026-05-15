import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- UI 스타일 ---
st.markdown("""
    <style>
    :root { --primary-color: #007BFF; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 5px; }
    .record-card { border-radius: 12px; padding: 20px; margin-bottom: 15px; border: 1px solid #eee; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# 연결 식별자를 완전히 새롭게(v3) 변경하여 캐시 잔상을 지웁니다.
conn = st.connection("gsheets_v3", type=GSheetsConnection)

def load_data_securely():
    try:
        # 방법 1: 이름으로 시도
        df = conn.read(worksheet="Records", ttl=0)
        c_df = conn.read(worksheet="Cycles", ttl=0)
        return df, c_df
    except:
        try:
            # 방법 2: 이름으로 실패 시, 시트의 첫 번째/두 번째 탭을 순서대로 강제 로드
            df = conn.read(ttl=0) # 첫 번째 탭
            return df, None
        except Exception as e:
            st.error(f"데이터 연결 실패: {e}")
            return None, None

df, c_df = load_data_securely()

st.title("오늘 하루 기록")
tab1, tab2, tab3 = st.tabs(["📝 기록하기", "💉 항암 차수", "📊 요약보기"])

# --- 기록하기 ---
with tab1:
    st.subheader("오늘의 상태 기록")
    curr_date = datetime.now().strftime("%Y-%m-%d")
    
    m_val = st.radio("아침 기록", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
    e_val = st.radio("저녁 기록", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
    
    # 몸무게 초기값 설정
    last_w = 55.0
    if df is not None and not df.empty and "몸무게" in df.columns:
        try:
            last_w = float(pd.to_numeric(df['몸무게'], errors='coerce').dropna().iloc[-1])
        except: pass

    w_val = st.number_input("몸무게 (kg)", value=last_w, step=0.1)
    p_val = st.select_slider("통증", options=list(range(1, 11)), value=1)
    n_val = st.text_area("메모", value="")

    if st.button("저장하기", use_container_width=True):
        new_row = pd.DataFrame([{
            "날짜": curr_date, "아침기록": m_val, "저녁기록": e_val,
            "몸무게": w_val, "통증": p_val, "메모": n_val
        }])
        final_df = pd.concat([df, new_row], ignore_index=True) if df is not None else new_row
        # 업데이트 시에도 탭 이름을 명시하거나, 안 되면 첫 탭에 덮어씀
        try:
            conn.update(worksheet="Records", data=final_df)
        except:
            conn.update(data=final_df)
        st.success("데이터가 시트에 저장되었습니다!")
        st.rerun()

# --- 요약보기 ---
with tab3:
    if df is not None and not df.empty:
        # 컬럼 이름이 맞는지 확인 후 처리
        if "날짜" in df.columns:
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
            display_df = df.dropna(subset=['날짜']).sort_values('날짜', ascending=False)
            
            for _, row in display_df.iterrows():
                st.markdown(f"""
                <div class="record-card">
                    <div style="display:flex; justify-content:space-between;">
                        <b>{row['날짜'].strftime('%m월 %d일')}</b>
                        <span style="color:#007BFF; font-weight:bold;">{row['몸무게']}kg</span>
                    </div>
                    <div style="font-size:14px; color:#555; margin-top:8px;">
                        아침: {row['아침기록']} | 저녁: {row['저녁기록']} | 통증: {row['통증']}
                    </div>
                    <div style="margin-top:8px; font-size:15px;">{row['메모'] if str(row['메모']) != 'nan' else ''}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("시트의 헤더(1행)가 '날짜, 아침기록, 저녁기록...' 순서인지 확인해 주세요.")
            st.write("현재 시트 컬럼:", df.columns.tolist())
    else:
        st.info("데이터를 불러오는 중입니다. 시트에 데이터가 한 줄 이상 있는지 확인해 주세요.")
