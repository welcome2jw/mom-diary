import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- [UI 스타일: 배경 없는 빨간 X 버튼 및 UI 복구] ---
st.markdown("""
    <style>
    :root { --primary-color: #007BFF !important; }
    h1 { font-size: 40px !important; font-weight: 800 !important; text-align: center; margin-bottom: 30px !important; }
    
    .cycle-header {
        background-color: #007BFF; color: white; padding: 8px 15px; border-radius: 10px;
        font-weight: bold; margin: 25px 0 15px 0; font-size: 18px; text-align: center;
    }
    .cycle-header.end { background-color: #6c757d !important; }

    /* 메인 버튼 스타일 */
    div.stButton > button { background-color: #007BFF; color: white; border-radius: 8px; font-weight: bold; height: 3.5em; width: 100%; }
    
    .status-card {
        background-color: #f8f9fa; border-radius: 12px; padding: 20px; text-align: center;
        border: 2px solid #007BFF; margin-bottom: 25px;
    }

    .record-card { 
        border-radius: 15px; padding: 22px; margin-bottom: 20px; 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        box-shadow: 0px 4px 12px rgba(0,0,0,0.05); 
        background-color: white;
    }
    .weight-box { font-size: 26px; font-weight: 800; color: #007BFF !important; }
    
    /* [수정] X 버튼: 파란 배경, 테두리, 그림자 완전 삭제 */
    div[data-testid="column"] button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #ff4b4b !important;
        font-size: 22px !important;
        padding: 0 !important;
        height: auto !important;
        min-height: 0 !important;
    }
    div[data-testid="column"] button:hover {
        background-color: transparent !important;
        color: #d32f2f !important;
    }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 데이터 로드 시 모든 nan 계열을 빈 문자열로 통합
        m_df = conn.read(ttl=0).fillna("")
        c_df = conn.read(worksheet="차수정보", ttl=0).fillna("")
        
        # .0 제거 로직
        for dobj in [m_df, c_df]:
            for col in dobj.columns:
                dobj[col] = dobj[col].astype(str).apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
                dobj[col] = dobj[col].replace(['nan', 'None', 'NaN', 'NaT'], '')
        
        if not m_df.empty:
            m_df['날짜_dt'] = pd.to_datetime(m_df['날짜'], errors='coerce')
            
        return m_df, c_df
    except:
        return pd.DataFrame(), pd.DataFrame(columns=["차수", "시작일", "종료일"])

df, cycle_df = load_data()

st.title("오늘 하루 기록")
tab1, tab2, tab3 = st.tabs(["기록하기", "항암 차수", "기록보기"])

# --- [TAB 1] 기록하기 ---
with tab1:
    st.subheader("오늘의 상태 기록")
    curr_date = datetime.now().strftime("%Y년 %m월 %d일")
    st.markdown(f'<p style="font-size:25px; font-weight:bold;">{curr_date}</p>', unsafe_allow_html=True)
    morning = st.radio("아침 기록", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
    evening = st.radio("저녁 기록", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
    
    last_w = 55.0
    if not df.empty:
        ws = pd.to_numeric(df['몸무게'], errors='coerce').dropna()
        if not ws.empty: last_w = float(ws.iloc[-1])
    
    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)
    pain = st.number_input("통증 정도 (0~10)", min_value=0, max_value=10, value=0, step=1)
    notes = st.text_area("메모", placeholder="여기에 오늘의 특이사항을 기록해 주세요.")

    if st.button("기록 저장하기"):
        new_row = pd.DataFrame([{"날짜": datetime.now().strftime('%Y-%m-%d'), "아침기록": morning, "저녁기록": evening, "몸무게": weight, "통증": int(pain), "메모": notes}])
        conn.update(data=pd.concat([df.drop(columns=['날짜_dt'], errors='ignore'), new_row], ignore_index=True))
        st.rerun()

# --- [TAB 2] 항암 차수 관리 ---
with tab2:
    st.subheader("항암 차수 관리")
    ongoing = cycle_df[cycle_df['종료일'] == ''] if not cycle_df.empty else pd.DataFrame()
    if not ongoing.empty:
        curr = ongoing.iloc[-1]
        st.markdown(f'<div class="status-card"><h3 style="color:#007BFF; margin:0;">현재 {curr["차수"]}차 진행 중</h3><p style="margin:10px 0 0 0;">시작일: {curr["시작일"]}</p></div>', unsafe_allow_html=True)
        if st.button(f"{curr['차수']}차 종료하기"):
            idx = cycle_df[cycle_df['종료일'] == ''].index[-1]
            cycle_df.at[idx, '종료일'] = datetime.now().strftime('%Y-%m-%d')
            conn.update(worksheet="차수정보", data=cycle_df)
            st.rerun()
    else:
        st.info("현재 진행 중인 차수가 없습니다.")
        with st.form("new_cycle"):
            c_num = st.number_input("진행할 차수", min_value=1, step=1, value=len(cycle_df)+1)
            s_date = st.date_input("시작 날짜")
            if st.form_submit_button("새로운 차수 시작"):
                new_c = pd.DataFrame([{"차수": str(int(c_num)), "시작일": s_date.strftime('%Y-%m-%d'), "종료일": ""}])
                conn.update(worksheet="차수정보", data=pd.concat([cycle_df, new_c], ignore_index=True))
                st.rerun()

# --- [TAB 3] 기록보기 ---
with tab3:
    if not df.empty:
        ongoing = cycle_df[cycle_df['종료일'] == '']
        if not ongoing.empty:
            st.markdown(f'<div class="status-card" style="background-color:#eef7ff;"><h3 style="color:#007BFF; margin:0;">항암 {ongoing.iloc[-1]["차수"]}차 진행 중</h3></div>', unsafe_allow_html=True)

        events = []
        for i, row in df.iterrows():
            if pd.notnull(row['날짜_dt']):
                events.append({'type': 'record', 'date': row['날짜_dt'], 'val': row, 'id': i})
        for _, c in cycle_df.iterrows():
            s_dt = pd.to_datetime(c['시작일'], errors='coerce')
            e_dt = pd.to_datetime(c['종료일'], errors='coerce')
            if pd.notnull(s_dt): events.append({'type': 's_bar', 'date': s_dt, 'num': c['차수'], 'd_str': c['시작일']})
            if pd.notnull(e_dt): events.append({'type': 'e_bar', 'date': e_dt, 'num': c['차수'], 'd_str': c['종료일']})
        
        # 정렬 순서: 종료바(2) -> 기록(1) -> 시작바(0) 후 역순 정렬
        sorted_events = sorted(events, key=lambda x: (x['date'], {'e_bar': 2, 'record': 1, 's_bar': 0}[x['type']]), reverse=True)

        for event in sorted_events:
            if event['type'] == 's_bar':
                st.markdown(f'<div class="cycle-header">항암 {event["num"]}차 시작 ({event["d_str"]})</div>', unsafe_allow_html=True)
            elif event['type'] == 'e_bar':
                st.markdown(f'<div class="cycle-header end">항암 {event["num"]}차 종료 ({event["d_str"]})</div>', unsafe_allow_html=True)
            elif event['type'] == 'record':
                row, rid = event['val'], event['id']
                col_card, col_del = st.columns([0.9, 0.1])
                with col_del:
                    # [수정] 배경 없는 ❌ 버튼
                    if st.button("❌", key=f"del_{rid}"):
                        conn.update(data=df.drop(rid).drop(columns=['날짜_dt'], errors='ignore'))
                        st.rerun()
                with col_card:
                    # [수정] 데이터 공백 처리 및 통증 에러 방지 로직
                    w_val = str(row.get('몸무게', '')).strip()
                    m_val = str(row.get('아침기록', '')).strip()
                    e_val = str(row.get('저녁기록', '')).strip()
                    p_val = str(row.get('통증', '')).strip()
                    memo_val = str(row.get('메모', '')).strip()

                    pain_html = f'<div style="font-size:16px; margin-top:5px;">통증: {p_val}/10</div>' if p_val and p_val != '0' else ""
                    
                    # [에러 해결] 메모 HTML 노출 에러 방지를 위해 변수 분리 후 출력
                    if memo_val:
                        memo_section = f'<div style="margin-top:10px; font-size:16px; border-top: 1px solid #eee; padding-top:8px;">{memo_val}</div>'
                    else:
                        memo_section = ""

                    st.markdown(f"""
                    <div class="record-card">
                        <div style="display: flex; justify-content: space-between; align-items: baseline;">
                            <span style="font-size:19px; font-weight:bold;">{event['date'].strftime('%m월 %d일')}</span>
                            <span class="weight-box">{w_val} <small style="font-size:16px;">kg</small></span>
                        </div>
                        <div style="font-size:17px; margin-top:10px;">아침: {m_val} | 저녁: {e_val}</div>
                        {pain_html}
                        {memo_section}
                    </div>
                    """, unsafe_allow_html=True)
