import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- [강력 고정: UI FINAL VER. 스타일 시트] ---
st.markdown("""
    <style>
    :root { --primary-color: #007BFF !important; }
    
    /* 1. 기본 폰트 및 제목 */
    h1 { font-size: 32px !important; font-weight: 800 !important; text-align: center; color: #333; margin-bottom: 20px !important; }
    
    /* 2. 탭 및 버튼 블루 테마 고정 */
    .stTabs [aria-selected="true"] { background-color: #007BFF !important; color: white !important; }
    div.stButton > button { 
        background-color: #007BFF !important; color: white !important; 
        border-radius: 8px !important; font-weight: bold !important; border: none !important;
    }

    /* 3. 항암 차수 헤더 & 상태 카드 */
    .cycle-header {
        background-color: #007BFF; color: white; padding: 8px 15px; border-radius: 10px;
        font-weight: bold; margin: 25px 0 15px 0; font-size: 16px; text-align: center;
        box-shadow: 0px 4px 10px rgba(0, 123, 255, 0.2);
    }
    .status-card {
        background-color: #f8f9fa; border-radius: 12px; padding: 15px; text-align: center;
        border: 2px solid #007BFF; margin-bottom: 20px;
    }

    /* 4. 기록 카드 레이아웃 (Final Ver.) */
    .record-card {
        border-radius: 15px; padding: 18px; margin-bottom: 10px; 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.03);
        background-color: white;
    }
    .weight-box { font-size: 22px; font-weight: 800; color: #007BFF !important; }
    .info-line { font-size: 16px; margin-top: 8px; line-height: 1.5; color: #333; } /* 약 기록 */
    .pain-line { font-size: 16px; font-weight: normal !important; color: #333; margin-top: 4px; } /* 통증 줄 (볼드해제) */
    .memo-line { margin-top: 10px; font-size: 15px; color: #555; border-top: 1px solid #eee; padding-top: 8px; }

    /* 5. 삭제 버튼 (X) 전용 스타일 */
    button[key^="del_"] {
        background-color: transparent !important; color: #ff4b4b !important;
        border: none !important; font-size: 20px !important; padding: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 구글 시트 연결 ---
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
        return pd.DataFrame(ws.get_all_records()), ws
    except:
        return pd.DataFrame(), None

df, ws_records = load_data("Records")
cycle_df, ws_cycles = load_data("차수정보")

st.title("오늘 하루 기록")
tab1, tab2, tab3 = st.tabs(["기록하기", "항암 차수", "기록보기"])

# --- [TAB 1] 기록하기 ---
with tab1:
    st.subheader("오늘의 상태 기록")
    st.markdown(f'<p style="font-size:22px; font-weight:bold;">{datetime.now().strftime("%Y년 %m월 %d일")}</p>', unsafe_allow_html=True)
    morning = st.radio("아침 기록", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
    evening = st.radio("저녁 기록", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
    
    last_w = 55.0
    if not df.empty and "몸무게" in df.columns:
        try: last_w = float(df['몸무게'].iloc[-1])
        except: pass

    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)
    pain = st.number_input("통증 정도 (0: 안 아픔 ~ 10: 매우 아픔)", min_value=0, max_value=10, value=0, step=1)
    notes = st.text_area("메모")

    if st.button("기록 저장하기", use_container_width=True):
        if ws_records:
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
            ws_cycles.update_cell(len(cycle_df) + 1, 3, datetime.now().strftime('%Y-%m-%d'))
            st.rerun()
    else:
        st.info("현재 진행 중인 차수가 없습니다.")
        with st.form("new_cycle"):
            new_c = st.number_input("진행할 차수", min_value=1, step=1, value=len(cycle_df)+1 if not cycle_df.empty else 1)
            s_date = st.date_input("차수 시작 날짜")
            if st.form_submit_button("새로운 차수 시작하기"):
                ws_cycles.append_row([int(new_c), s_date.strftime('%Y-%m-%d'), ""])
                st.rerun()

# --- [TAB 3] 기록보기 (Final Ver. 레이아웃 고정) ---
with tab3:
    if not df.empty:
        pdf = df.copy()
        pdf['idx'] = pdf.index + 2
        pdf['날짜'] = pd.to_datetime(pdf['날짜'], errors='coerce')
        pdf = pdf.dropna(subset=['날짜']).sort_values('날짜', ascending=False)

        current_bar = None
        for _, row in pdf.iterrows():
            # 차수 구분 바 표시
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

            # 레이아웃: 기록 카드와 X 버튼 나란히 배치
            col_card, col_del = st.columns([0.88, 0.12])
            with col_del:
                if st.button("✖", key=f"del_{row['idx']}"):
                    ws_records.delete_rows(int(row['idx']))
                    st.rerun()

            with col_card:
                # 통증 데이터 처리 (입력 안 되었을 시 "통증: "만 표시)
                p_val = str(row['통증']).strip()
                pain_text = f"통증: {p_val}/10" if p_val not in ["", "nan"] else "통증: "
                
                st.markdown(f"""
                <div class="record-card">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <span style="font-size:17px; font-weight:bold;">{row['날짜'].strftime('%m월 %d일')}</span>
                        <span class="weight-box">{row['몸무게']} <small style="font-size:14px;">kg</small></span>
                    </div>
                    <div class="info-line">아침: {row['아침기록']} | 저녁: {row['저녁기록']}</div>
                    <div class="pain-line">{pain_text}</div>
                    <div class="memo-line">{row['메모'] if str(row['메모']) not in ['nan', ''] else ''}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("기록이 없습니다.")
