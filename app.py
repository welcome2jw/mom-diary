import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

# --- 구글 시트 직접 연결 함수 ---
def get_gspread_client():
    try:
        # Secrets에서 서비스 계정 정보를 가져옵니다.
        creds_dict = st.secrets["connections"]["gsheets"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"인증 설정 오류: {e}")
        return None

def load_data(worksheet_name):
    try:
        client = get_gspread_client()
        if client:
            sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            sh = client.open_by_url(sheet_url)
            ws = sh.worksheet(worksheet_name)
            data = ws.get_all_records()
            return pd.DataFrame(data), ws
        return pd.DataFrame(), None
    except Exception:
        # 탭이 없거나 데이터가 비어있을 경우 빈 프레임 반환
        return pd.DataFrame(), None

# 데이터 로드
df, ws_records = load_data("Records")
cycle_df, ws_cycles = load_data("차수정보")

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
    if not df.empty and "몸무게" in df.columns:
        try:
            # 유효한 마지막 몸무게 추출
            valid_weights = pd.to_numeric(df['몸무게'], errors='coerce').dropna()
            if not valid_weights.empty:
                last_w = float(valid_weights.iloc[-1])
        except: pass

    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)
    pain = st.select_slider("통증 정도", options=list(range(1, 11)), value=1)
    notes = st.text_area("메모", placeholder="특이사항을 적어주세요.")

    if st.button("기록 저장하기", use_container_width=True):
        if ws_records:
            new_row = [datetime.now().strftime('%Y-%m-%d'), morning, evening, weight, pain, notes]
            ws_records.append_row(new_row)
            st.success("오늘의 기록이 저장되었습니다!")
            st.rerun()
        else:
            st.error("기록 시트(Records)를 찾을 수 없습니다.")

# --- [TAB 2] 항암 차수 ---
with tab2:
    st.subheader("새로운 항암 차수 등록")
    with st.form("cycle_form"):
        new_cycle = st.number_input("진행할 차수 (숫자만)", min_value=1, step=1)
        start_date = st.date_input("차수 시작 날짜")
        if st.form_submit_button("차수 시작 기록하기"):
            if ws_cycles:
                ws_cycles.append_row([int(new_cycle), start_date.strftime('%Y-%m-%d')])
                st.success(f"{new_cycle}차 항암이 등록되었습니다!")
                st.rerun()
            else:
                st.error("차수정보 시트를 찾을 수 없습니다.")

# --- [TAB 3] 요약보기 ---
with tab3:
    if not df.empty and "날짜" in df.columns:
        pdf = df.copy()
        pdf['날짜'] = pd.to_datetime(pdf['날짜'], errors='coerce')
        pdf = pdf.dropna(subset=['날짜']).sort_values('날짜', ascending=False)
        
        cdf = cycle_df.copy() if not cycle_df.empty else None
        if cdf is not None and "시작일" in cdf.columns:
            cdf['시작일'] = pd.to_datetime(cdf['시작일'], errors='coerce')
            cdf = cdf.dropna(subset=['시작일']).sort_values('시작일', ascending=False)

        current_bar = None
        for i, row in pdf.iterrows():
            label = "기록 외"
            if cdf is not None:
                match = cdf[cdf['시작일'] <= row['날짜']]
                if not match.empty:
                    label = f"항암 {int(match.iloc[0]['차수'])}차 진행 중"

            if label != current_bar:
                st.markdown(f'<div class="cycle-header">{label}</div>', unsafe_allow_html=True)
                current_bar = label

            st.markdown(f"""
            <div class="record-card">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="font-size:19px; font-weight:bold;">{row['날짜'].strftime('%m월 %d일')}</span>
                    <span class="weight-box">{row['몸무게']} <small style="font-size:16px;">kg</small></span>
                </div>
                <div style="font-size:17px; margin-top:10px;">아침: {row['아침기록']} | 저녁: {row['저녁기록']}</div>
                <div style="font-size:15px; opacity:0.8; margin-top:5px;">통증: {row['통증']} / 10</div>
                <div style="margin-top:10px; font-size:16px;">{row['메모'] if str(row['메모']) != '' and str(row['메모']) != 'nan' else ''}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("데이터를 불러오는 중이거나 기록이 없습니다. Records 탭에 데이터가 있는지 확인해 주세요.")
