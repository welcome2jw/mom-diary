import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- [UI 스타일: 파란 배경 없는 X 버튼 및 전체 디자인] ---
st.markdown("""
    <style>
    :root { --primary-color: #007BFF !important; }
    h1 { font-size: 40px !important; font-weight: 800 !important; text-align: center; margin-bottom: 30px !important; }
    
    /* 차수 바 스타일 */
    .cycle-header {
        background-color: #007BFF; color: white; padding: 8px 15px; border-radius: 10px;
        font-weight: bold; margin: 25px 0 15px 0; font-size: 18px; text-align: center;
        box-shadow: 0px 4px 10px rgba(0, 123, 255, 0.2);
    }
    .cycle-header.end { background-color: #6c757d !important; }

    /* 일반 버튼 스타일 */
    div.stButton > button { background-color: #007BFF; color: white; border-radius: 8px; font-weight: bold; height: 3.5em; width: 100%; }
    
    /* 상태 카드 */
    .status-card {
        background-color: #f8f9fa; border-radius: 12px; padding: 20px; text-align: center;
        border: 2px solid #007BFF; margin-bottom: 25px;
    }

    /* 기록 카드 */
    .record-card { 
        border-radius: 15px; padding: 22px; margin-bottom: 20px; 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        box-shadow: 0px 4px 12px rgba(0,0,0,0.05); 
        background-color: white;
    }
    .weight-box { font-size: 26px; font-weight: 800; color: #007BFF !important; }
    
    /* [수정] X 버튼: 파란 배경색과 테두리를 완전히 제거 */
    button[key^="del_"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #ff4b4b !important;
        font-size: 20px !important;
        padding: 0 !important;
        height: auto !important;
        width: auto !important;
        line-height: 1 !important;
    }
    button[key^="del_"]:hover { color: #d32f2f !important; background-color: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        m_df = conn.read(ttl=0).fillna("").astype(str)
        c_df = conn.read(worksheet="차수정보", ttl=0).fillna("").astype(str)
        
        # [수정] .0 제거 및 nan 처리
        for df_obj in [m_df, c_df]:
            for col in df_obj.columns:
                df_obj[col] = df_obj[col].apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
                df_obj[col] = df_obj[col].replace(['nan', 'None', 'NaT', 'NaN'], '')
        
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
        try:
            ws = pd.to_numeric(df['몸무게'], errors='coerce').dropna()
            if not ws.empty: last_w = float(ws.iloc[-1])
        except: pass
    
    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)
    pain = st.number_input("통증 정도 (0~10)", min_value=0, max_value=10, value=0, step=1)
    notes = st.text_area("메모", placeholder="여기에 오늘의 특이사항을 기록해 주세요.")

    if st.button("기록 저장하기"):
        new_row = pd.DataFrame([{"날짜": datetime.now().strftime('%Y-%m-%d'), "아침기록": morning, "저녁기록": evening, "몸무게": weight, "통증": int(pain), "메모": notes}])
        updated_df = pd.concat([df.drop(columns=['날짜_dt'], errors='ignore'), new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.success("저장 완료!")
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
        # 상단 진행 알림 (.0 제거 적용)
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
        
        # [중요] 정렬 로직: 종료바(0) -> 기록카드(1) -> 시작바(2)
        # 역순 정렬하면 같은 날짜 내에서 종료바가 가장 위, 시작바가 가장 아래에 위치함
        sorted_events = sorted(events, key=lambda x: (x['date'], {'e_bar': 2, 'record': 1, 's_bar': 0}[x['type']]), reverse=True)

        for event in sorted_events:
            if event['type'] == 's_bar':
                st.markdown(f'<div class="cycle-header">항암 {event["num"]}차 시작 ({event["d_str"]})</div>', unsafe_allow_html=True)
            elif event['type'] == 'e_bar':
                st.markdown(f'<div class="cycle-header end">항암 {event["num"]}차 종료 ({event["d_str"]})</div>', unsafe_allow_html=True)
            elif event['type'] == 'record':
                row, i = event['val'], event['id']
                col_card, col_del = st.columns([0.9, 0.1])
                with col_del:
                    if st.button("❌", key=f"del_{i}"):
                        conn.update(data=df.drop(i).drop(columns=['날짜_dt'], errors='ignore'))
                        st.rerun()
                with col_card:
                    w_v, m_v, e_v = str(row['몸무게']), str(row['아침기록']), str(row['저녁기록'])
                    p_v, memo = str(row['통증']), str(row['메모'])
                    
                    pain_html = f'<div style="font-size:16px; margin-top:5px;">통증: {p_v}/10</div>' if p_v and p_v != '0' else ""
                    # [에러 해결] 이중 중괄호를 사용하여 f-string 스타일 에러 방지
                    memo_html = f'<div style="margin-top:10px; font-size:16px; border-top: 1px solid #eee; padding-top:8px;">{memo}</div>' if memo else ""
                    
                    st.markdown(f"""
                    <div class="record-card">
                        <div style="display: flex; justify-content: space-between; align-items: baseline;">
                            <span style="font-size:19px; font-weight:bold;">{event['date'].strftime('%m월 %d일')}</span>
                            <span class="weight-box">{w_v} <small style="font-size:16px;">kg</small></span>
                        </div>
                        <div style="font-size:17px; margin-top:10px;">아침: {m_v} | 저녁: {e_v}</div>
                        {pain_html}
                        {memo_html}
                    </div>
                    """, unsafe_allow_html=True)
