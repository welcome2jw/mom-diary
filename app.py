import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- [UI 스타일: 삭제 버튼 포함 최초 디자인으로 복구] ---
st.markdown("""
    <style>
    :root { --primary-color: #007BFF !important; }
    h1 { font-size: 40px !important; font-weight: 800 !important; text-align: center; margin-bottom: 30px !important; }
    
    .cycle-header {
        background-color: #007BFF; color: white; padding: 8px 15px; border-radius: 10px;
        font-weight: bold; margin: 25px 0 15px 0; font-size: 18px; text-align: center;
        box-shadow: 0px 4px 10px rgba(0, 123, 255, 0.2);
    }

    div.stButton > button { background-color: #007BFF !important; color: white !important; border-radius: 8px !important; font-weight: bold !important; height: 3.5em !important; }
    
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
    
    /* 삭제 버튼 디자인 복구: 빨간색 X 텍스트 스타일 */
    .del-btn {
        color: #ff4b4b !important; background: none !important; border: none !important;
        font-size: 20px !important; cursor: pointer; padding: 0 !important; font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        m_df = conn.read(ttl=0) 
        try:
            c_df = conn.read(worksheet="차수정보", ttl=0)
        except:
            c_df = pd.DataFrame(columns=["차수", "시작일", "종료일"])
        
        # [데이터 클리닝] nan, None, NaT를 실제 빈 문자열로 강제 변환
        m_df = m_df.fillna("").astype(str)
        for col in m_df.columns:
            m_df[col] = m_df[col].replace(['nan', 'None', 'nan.0', 'NaT', 'NaN'], '')
        
        if not m_df.empty:
            m_df['날짜_dt'] = pd.to_datetime(m_df['날짜'], errors='coerce')

        c_df = c_df.fillna("").astype(str)
        for col in c_df.columns:
            c_df[col] = c_df[col].replace(['nan', 'None', 'nan.0', 'NaN'], '')
            
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
            weights = pd.to_numeric(df['몸무게'], errors='coerce').dropna()
            if not weights.empty: last_w = float(weights.iloc[-1])
        except: pass
    
    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)
    pain = st.number_input("통증 정도 (0~10)", min_value=0, max_value=10, value=0, step=1)
    # [수정] 메모 안내 문구(Placeholder) 추가
    notes = st.text_area("메모", placeholder="여기에 오늘의 특이사항을 기록해 주세요.")

    if st.button("기록 저장하기", use_container_width=True):
        new_row = pd.DataFrame([{
            "날짜": datetime.now().strftime('%Y-%m-%d'), 
            "아침기록": morning, "저녁기록": evening, 
            "몸무게": weight, "통증": int(pain), "메모": notes
        }])
        save_df = df.drop(columns=['날짜_dt'], errors='ignore')
        updated_df = pd.concat([save_df, new_row], ignore_index=True)
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
        if st.button(f"{curr['차수']}차 종료하기", use_container_width=True):
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
                updated_c = pd.concat([cycle_df, new_c], ignore_index=True)
                conn.update(worksheet="차수정보", data=updated_c)
                st.rerun()

# --- [TAB 3] 기록보기 ---
with tab3:
    if not df.empty:
        # 1. 진행 중 알림
        ongoing = cycle_df[cycle_df['종료일'] == '']
        if not ongoing.empty:
            st.markdown(f'<div class="status-card" style="background-color:#eef7ff;"><h3 style="color:#007BFF; margin:0;">항암 {ongoing.iloc[-1]["차수"]}차 진행 중</h3></div>', unsafe_allow_html=True)

        # 2. 모든 이벤트 통합
        events = []
        for i, row in df.iterrows():
            if pd.notnull(row['날짜_dt']):
                events.append({'type': 'record', 'date': row['날짜_dt'], 'val': row, 'id': i})
        
        for _, c in cycle_df.iterrows():
            s_dt = pd.to_datetime(c['시작일'], errors='coerce')
            e_dt = pd.to_datetime(c['종료일'], errors='coerce')
            if pd.notnull(s_dt): events.append({'type': 's_bar', 'date': s_dt, 'num': c['차수'], 'd_str': c['시작일']})
            if pd.notnull(e_dt): events.append({'type': 'e_bar', 'date': e_dt, 'num': c['차수'], 'd_str': c['종료일']})
        
        # 3. [정렬 로직 고정] 종료(0:위) -> 기록(1:중간) -> 시작(2:아래)
        def s_prio(x):
            prio = {'e_bar': 0, 'record': 1, 's_bar': 2}
            return (x['date'], prio[x['type']])
        
        sorted_events = sorted(events, key=s_prio, reverse=True)

        for event in sorted_events:
            if event['type'] == 's_bar':
                st.markdown(f'<div class="cycle-header">항암 {event["num"]}차 시작 ({event["d_str"]})</div>', unsafe_allow_html=True)
            elif event['type'] == 'e_bar':
                st.markdown(f'<div class="cycle-header" style="background-color:#6c757d;">항암 {event["num"]}차 종료 ({event["d_str"]})</div>', unsafe_allow_html=True)
            elif event['type'] == 'record':
                row, i = event['val'], event['id']
                
                col_card, col_del = st.columns([0.9, 0.1])
                with col_del:
                    # [수정] 삭제 버튼 디자인 복구
                    if st.button("❌", key=f"del_{i}"):
                        conn.update(data=df.drop(i).drop(columns=['날짜_dt'], errors='ignore'))
                        st.rerun()
                
                with col_card:
                    # [수정] 데이터 정제 출력 (.0 제거 및 nan 공백화)
                    w_v = str(row['몸무게']).replace('.0', '').strip()
                    m_v = str(row['아침기록']).strip()
                    e_v = str(row['저녁기록']).strip()
                    p_v = str(row['통증']).replace('.0', '').strip()
                    memo = str(row['메모']).strip()
                    
                    # 통증 0이거나 비었을 때 처리
                    pain_html = f'<div style="font-size:16px; margin-top:5px;">통증: {p_v}/10</div>' if p_v and p_v != '0' else ""
                    
                    # [에러 해결] 메모 섹션 HTML을 f-string 밖에서 미리 정의하거나 중괄호를 이중으로 사용하여 에러 방지
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
    else:
        st.info("기록이 없습니다.")
