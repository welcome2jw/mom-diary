import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- [UI 스타일: 요청하신 원래 스타일로 고정] ---
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
    
    /* 삭제 버튼: 텍스트 형태의 빨간 X */
    .del-btn-style {
        background: none !important; border: none !important; color: #ff4b4b !important;
        font-size: 22px !important; cursor: pointer; padding: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        main_df = conn.read(ttl=0) 
        try:
            c_df = conn.read(worksheet="차수정보", ttl=0)
        except:
            c_df = pd.DataFrame(columns=["차수", "시작일", "종료일"])
        
        # [데이터 클리닝] nan 제거
        if not main_df.empty:
            for col in main_df.columns:
                main_df[col] = main_df[col].astype(str).replace(['nan', 'None', 'nan.0', 'NaN'], '')
            main_df['날짜_dt'] = pd.to_datetime(main_df['날짜'], errors='coerce')
            
        if not c_df.empty:
            for col in ['시작일', '종료일']:
                c_df[col] = c_df[col].astype(str).replace(['nan', 'None', 'NaN'], '')
            
        return main_df, c_df
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
            valid_weights = pd.to_numeric(df['몸무게'], errors='coerce').dropna()
            if not valid_weights.empty: last_w = float(valid_weights.iloc[-1])
        except: pass

    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)
    pain = st.number_input("통증 정도 (0~10)", min_value=0, max_value=10, value=0, step=1)
    notes = st.text_area("메모")

    if st.button("기록 저장하기", use_container_width=True):
        new_row = pd.DataFrame([{
            "날짜": datetime.now().strftime('%Y-%m-%d'), 
            "아침기록": morning, "저녁기록": evening, 
            "몸무게": weight, "통증": int(pain), "메모": notes
        }])
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
        if st.button(f"{curr['차수']}차 종료하기", use_container_width=True):
            idx = ongoing.index[-1]
            cycle_df.at[idx, '종료일'] = datetime.now().strftime('%Y-%m-%d')
            conn.update(worksheet="차수정보", data=cycle_df)
            st.rerun()
    else:
        st.info("현재 진행 중인 차수가 없습니다.")
        with st.form("new_cycle"):
            c_num = st.number_input("진행할 차수", min_value=1, step=1, value=len(cycle_df)+1)
            s_date = st.date_input("시작 날짜")
            if st.form_submit_button("새로운 차수 시작"):
                new_c = pd.DataFrame([{"차수": int(c_num), "시작일": s_date.strftime('%Y-%m-%d'), "종료일": ""}])
                updated_c = pd.concat([cycle_df, new_c], ignore_index=True)
                conn.update(worksheet="차수정보", data=updated_c)
                st.rerun()

# --- [TAB 3] 기록보기 ---
with tab3:
    if not df.empty:
        # 진행 중인 차수 맨 위에 표시
        ongoing = cycle_df[cycle_df['종료일'] == '']
        if not ongoing.empty:
            curr = ongoing.iloc[-1]
            st.markdown(f'<div class="status-card" style="border-width:3px; background-color:#e7f3ff;"><h3 style="color:#007BFF; margin:0;">항암 {curr["차수"]}차 진행 중</h3></div>', unsafe_allow_html=True)

        # 모든 이벤트(기록카드, 시작바, 종료바)를 하나의 타임라인으로 합치기
        events = []
        for i, row in df.iterrows():
            events.append({'type': 'record', 'date': row['날짜_dt'], 'data': row, 'id': i})
        
        for _, c in cycle_df.iterrows():
            if c['시작일']:
                events.append({'type': 'cycle_start', 'date': pd.to_datetime(c['시작일']), 'num': c['차수']})
            if c['종료일']:
                events.append({'type': 'cycle_end', 'date': pd.to_datetime(c['종료일']), 'num': c['차수']})
        
        # 날짜 내림차순 정렬 (최신이 위로)
        # 같은 날짜면 종료바 -> 기록카드 -> 시작바 순서로 보이게 정렬 가중치 부여
        def sort_priority(x):
            prio = {'cycle_end': 0, 'record': 1, 'cycle_start': 2}
            return (x['date'], prio[x['type']])
        
        sorted_events = sorted(events, key=sort_priority, reverse=True)

        for event in sorted_events:
            dt_str = event['date'].strftime('%Y-%m-%d')
            
            if event['type'] == 'cycle_start':
                st.markdown(f'<div class="cycle-header">항암 {int(float(event["num"]))}차 시작 ({dt_str})</div>', unsafe_allow_html=True)
            
            elif event['type'] == 'cycle_end':
                st.markdown(f'<div class="cycle-header" style="background-color:#6c757d;">항암 {int(float(event["num"]))}차 종료 ({dt_str})</div>', unsafe_allow_html=True)
            
            elif event['type'] == 'record':
                row = event['data']
                i = event['id']
                
                col_card, col_del = st.columns([0.9, 0.1])
                with col_del:
                    if st.button("❌", key=f"del_{i}"):
                        conn.update(data=df.drop(i).drop(columns=['날짜_dt'], errors='ignore'))
                        st.rerun()

                with col_card:
                    p_raw = str(row['통증']).replace('.0', '').strip()
                    pain_text = f"통증: {p_raw}/10" if p_raw not in ["nan", ""] else "통증: "
                    m_raw = str(row['메모']).strip()
                    memo_html = f'<div style="margin-top:10px; font-size:16px; border-top: 1px solid #eee; padding-top:8px;">{m_raw}</div>' if m_raw not in ["nan", ""] else ""
                    
                    st.markdown(f"""
                    <div class="record-card">
                        <div style="display: flex; justify-content: space-between; align-items: baseline;">
                            <span style="font-size:19px; font-weight:bold;">{event['date'].strftime('%m월 %d일')}</span>
                            <span class="weight-box">{row['몸무게']} <small style="font-size:16px;">kg</small></span>
                        </div>
                        <div style="font-size:17px; margin-top:10px;">아침: {row['아침기록']} | 저녁: {row['저녁기록']}</div>
                        <div style="font-size:16px; margin-top:5px;">{pain_text}</div>
                        {memo_html}
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("기록이 없습니다.")
