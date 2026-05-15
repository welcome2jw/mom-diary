import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# --- [강력 저장된 UI 스타일] ---
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
    
    /* 현재 진행 상태 카드 */
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
    
    /* 삭제 버튼 스타일 */
    button[key^="del_"] {
        background-color: transparent !important; color: #ff4b4b !important;
        border: none !important; font-size: 18px !important; padding: 0 !important;
        height: auto !important;
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
        
        # 날짜 전처리
        if not main_df.empty and "날짜" in main_df.columns:
            main_df['날짜'] = pd.to_datetime(main_df['날짜'], errors='coerce')
        if not c_df.empty:
            for col in ['시작일', '종료일']:
                if col in c_df.columns:
                    c_df[col] = c_df[col].astype(str).replace(['nan', 'None', ''], '')
            
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
            v_w = pd.to_numeric(df['몸무게'], errors='coerce').dropna()
            if not v_w.empty: last_w = float(v_w.iloc[-1])
        except: pass

    weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=last_w, step=0.1)
    pain = st.number_input("통증 정도 (0~10)", min_value=0, max_value=10, value=0)
    notes = st.text_area("메모")

    if st.button("기록 저장하기", use_container_width=True):
        new_row = pd.DataFrame([{"날짜": datetime.now().strftime('%Y-%m-%d'), "아침기록": morning, "저녁기록": evening, "몸무게": weight, "통증": int(pain), "메모": notes}])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.success("저장 완료!")
        st.rerun()

# --- [TAB 2] 항암 차수 (시작일/종료일 UI) ---
with tab2:
    st.subheader("항암 차수 관리")
    
    # 종료일이 없는(진행 중인) 차수 확인
    ongoing = cycle_df[cycle_df['종료일'] == ''] if not cycle_df.empty else pd.DataFrame()
    
    if not ongoing.empty:
        curr = ongoing.iloc[-1]
        st.markdown(f"""
        <div class="status-card">
            <h3 style="color:#007BFF; margin:0;">현재 {curr['차수']}차 진행 중</h3>
            <p style="margin:10px 0 0 0;">시작일: {curr['시작일']}</p>
        </div>
        """, unsafe_allow_html=True)
        
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
    valid_df = df.dropna(subset=['날짜']).sort_values('날짜', ascending=False) if not df.empty else pd.DataFrame()
    
    if not valid_df.empty:
        current_display_cycle = None
        for i, row in valid_df.iterrows():
            record_date = row['날짜']
            applicable_cycle = "기록 외"
            
            if not cycle_df.empty:
                for _, c in cycle_df.iterrows():
                    s_dt = pd.to_datetime(c['시작일'])
                    e_dt = pd.to_datetime(c['종료일']) if c['종료일'] != '' else pd.to_datetime('2099-12-31')
                    if s_dt <= record_date <= e_dt:
                        applicable_cycle = f"항암 {int(c['차수'])}차 진행 중"
                        break

            if applicable_cycle != current_display_cycle:
                st.markdown(f'<div class="cycle-header">{applicable_cycle}</div>', unsafe_allow_html=True)
                current_display_cycle = applicable_cycle

            col_card, col_del = st.columns([0.88, 0.12])
            with col_del:
                if st.button("✖", key=f"del_{i}"):
                    conn.update(data=df.drop(i))
                    st.rerun()

            with col_card:
                # nan 및 빈 태그 방지 로직
                p_val = str(row['통증']).strip()
                pain_text = f"통증: {p_val}/10" if p_val not in ["nan", "", "None"] else "통증: "
                
                memo_raw = str(row['메모']).strip()
                memo_html = f'<div style="margin-top:10px; font-size:16px; border-top: 1px solid #eee; padding-top:8px;">{memo_raw}</div>' if memo_raw not in ["nan", "", "None"] else ""
                
                st.markdown(f"""
                <div class="record-card">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <span style="font-size:19px; font-weight:bold;">{record_date.strftime('%m월 %d일')}</span>
                        <span class="weight-box">{row['몸무게']} <small style="font-size:16px;">kg</small></span>
                    </div>
                    <div style="font-size:17px; margin-top:10px;">아침: {row['아침기록']} | 저녁: {row['저녁기록']}</div>
                    <div style="font-size:16px; margin-top:5px;">{pain_text}</div>
                    {memo_html}
                </div>
                """, unsafe_allow_html=True)
