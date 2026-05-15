import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- [강력 저장된 UI 스타일 고정] ---
st.markdown("""
    <style>
    :root { --primary-color: #007BFF !important; }
    h1 { font-size: 40px !important; font-weight: 800 !important; text-align: center; margin-bottom: 30px !important; }
    .cycle-header {
        background-color: #007BFF; color: white; padding: 8px 15px; border-radius: 10px;
        font-weight: bold; margin: 25px 0 15px 0; font-size: 18px; text-align: center;
        box-shadow: 0px 4px 10px rgba(0, 123, 255, 0.2);
    }
    .status-card {
        background-color: #f8f9fa; border-radius: 12px; padding: 20px; text-align: center;
        border: 2px solid #007BFF; margin-bottom: 20px;
    }
    div.stButton > button { background-color: #007BFF !important; color: white !important; border-radius: 8px !important; font-weight: bold !important; height: 3.5em !important; }
    .record-card { position: relative; border-radius: 15px; padding: 22px; margin-bottom: 20px; border: 1px solid rgba(128, 128, 128, 0.2); box-shadow: 0px 4px 12px rgba(0,0,0,0.05); }
    .weight-box { font-size: 26px; font-weight: 800; color: #007BFF !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 구글 시트 연결 함수 ---
def get_gspread_client():
    try:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        if "spreadsheet" in creds_dict: del creds_dict["spreadsheet"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"인증 오류: {e}")
        return None

def load_data(worksheet_name):
    try:
        client = get_gspread_client()
        sh = client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data), ws
    except:
        return pd.DataFrame(), None

df, ws_records = load_data("Records")
cycle_df, ws_cycles = load_data("차수정보")

st.title("오늘 하루 기록")
tab1, tab2, tab3 = st.tabs(["기록하기", "항암 차수", "기록보기"])

# --- [TAB 1] 기록하기 ---
with tab1:
    st.subheader("오늘의 상태 기록")
    st.markdown(f'<p style="font-size:25px; font-weight:bold;">{datetime.now().strftime("%Y년 %m월 %d일")}</p>', unsafe_allow_html=True)
    
    morning = st.radio("아침 기록", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
    evening = st.radio("저녁 기록", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
    
    last_w = 55.0
    if not df.empty and "몸무게" in df.columns:
        try: last_w = float(df['몸무게'].iloc[-1])
        except: pass

    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)
    
    # 통증 입력 (0부터 시작)
    pain = st.number_input("통증 정도 (0: 안 아픔 ~ 10: 매우 아픔)", min_value=0, max_value=10, value=0, step=1)
    
    notes = st.text_area("메모", placeholder="특이사항을 적어주세요.")

    if st.button("기록 저장하기", use_container_width=True):
        if ws_records:
            # 숫자로 명확히 저장
            ws_records.append_row([datetime.now().strftime('%Y-%m-%d'), morning, evening, weight, int(pain), notes])
            st.success("저장되었습니다!")
            st.rerun()

# --- [TAB 2] 항암 차수 ---
with tab2:
    st.subheader("항암 차수 관리")
    ongoing = cycle_df[cycle_df['종료일'] == ''] if not cycle_df.empty and '종료일' in cycle_df.columns else pd.DataFrame()
    
    if not ongoing.empty:
        curr_c = ongoing.iloc[-1]
        st.markdown(f'<div class="status-card"><h3 style="color:#007BFF; margin:0;">현재 {curr_c["차수"]}차 진행 중</h3><p style="margin:10px 0 0 0;">시작일: {curr_c["시작일"]}</p></div>', unsafe_allow_html=True)
        
        if st.button(f"{curr_c['차수']}차 종료하기", use_container_width=True):
            row_to_update = len(cycle_df) + 1
            ws_cycles.update_cell(row_to_update, 3, datetime.now().strftime('%Y-%m-%d'))
            st.success("차수가 종료되었습니다.")
            st.rerun()
    else:
        st.info("현재 진행 중인 차수가 없습니다.")
        with st.form("new_cycle_form"):
            new_c = st.number_input("진행할 차수", min_value=1, step=1, value=len(cycle_df)+1 if not cycle_df.empty else 1)
            s_date = st.date_input("차수 시작 날짜")
            if st.form_submit_button("새로운 차수 시작하기"):
                ws_cycles.append_row([int(new_c), s_date.strftime('%Y-%m-%d'), ""])
                st.rerun()

# --- [TAB 3] 기록보기 ---
with tab3:
    if not df.empty:
        pdf = df.copy()
        pdf['original_idx'] = pdf.index + 2
        pdf['날짜'] = pd.to_datetime(pdf['날짜'], errors='coerce')
        pdf = pdf.dropna(subset=['날짜']).sort_values('날짜', ascending=False)

        current_bar = None
        for _, row in pdf.iterrows():
            label = "휴식기 또는 기록 외"
            if not cycle_df.empty:
                for _, c in cycle_df.iterrows():
                    s_dt = pd.to_datetime(c['시작일'])
                    e_dt = pd.to_datetime(c['종료일']) if c['종료일'] != '' else pd.to_datetime('2099-12-31')
                    if s_dt <= row['날짜'] <= e_dt:
                        label = f"항암 {c['차수']}차 진행 중"
                        break

            if label != current_bar:
                st.markdown(f'<div class="cycle-header">{label}</div>', unsafe_allow_html=True)
                current_bar = label

            col1, col2 = st.columns([0.85, 0.15])
            with col2:
                # 삭제 버튼
                if st.button("X", key=f"del_{row['original_idx']}", help="기록 삭제"):
                    ws_records.delete_rows(int(row['original_idx']))
                    st.rerun()
            
            with col1:
                # 통증 표시 로직: 값이 존재하면 0이라도 표시, 아예 비었으면 생략
                pain_raw = str(row['통증']).strip()
                pain_display = f" | 통증: {pain_raw}/10" if pain_raw != "" and pain_raw != "nan" else ""
                
                st.markdown(f"""
                <div class="record-card">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <span style="font-size:19px; font-weight:bold;">{row['날짜'].strftime('%m월 %d일')}</span>
                        <span class="weight-box">{row['몸무게']} <small style="font-size:16px;">kg</small></span>
                    </div>
                    <div style="font-size:17px; margin-top:10px;">아침: {row['아침기록']} | 저녁: {row['저녁기록']}{pain_display}</div>
                    <div style="margin-top:10px; font-size:16px;">{row['메모'] if str(row['메모']) not in ['nan', ''] else ''}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("기록이 없습니다.")
