import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="오늘 하루 기록", layout="centered")

# 2. CSS 스타일
st.markdown("""
    <style>
    :root { --primary-color: #007BFF !important; }
    h1 { font-size: 40px !important; font-weight: 800 !important; text-align: center; margin-bottom: 30px !important; }
    
    .cycle-header {
        background-color: #007BFF; color: white; padding: 8px 15px; border-radius: 10px;
        font-weight: bold; margin: 25px 0 15px 0; font-size: 18px; text-align: center;
        box-shadow: 0px 4px 10px rgba(0, 123, 255, 0.2);
    }
    .cycle-header.end { background-color: #6c757d !important; }

    button[kind="primary"] { 
        background-color: #007BFF !important; color: white !important; 
        border-radius: 8px !important; font-weight: bold !important; height: 3.5em !important; 
    }
    
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
    
    button[kind="secondary"] {
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        color: #ff4b4b !important;
        box-shadow: none !important;
        font-size: 22px !important;
        padding: 0 !important;
    }
    button[kind="secondary"]:hover {
        color: #d32f2f !important;
        background-color: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 및 클리닝
def clean_val(val):
    s = str(val).replace('.0', '').strip()
    if s.lower() in ['nan', 'none', 'nat', '']: return ""
    return s

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        m_df = conn.read(ttl=0).fillna("")
        c_df = conn.read(worksheet="차수정보", ttl=0).fillna("")
        for col in m_df.columns:
            m_df[col] = m_df[col].map(clean_val)
        for col in c_df.columns:
            c_df[col] = c_df[col].map(clean_val)
        if not m_df.empty:
            m_df['dt'] = pd.to_datetime(m_df['날짜'], errors='coerce')
        return m_df, c_df
    except:
        return pd.DataFrame(), pd.DataFrame(columns=["차수", "시작일", "종료일"])

df, c_df = get_data()

# 기록 수정하기 팝업창(Dialog) 구현
@st.dialog("기록 수정하기")
def edit_record_dialog(rid, current_val):
    st.markdown(f"### {pd.to_datetime(current_val['날짜']).strftime('%m월 %d일')} 기록 수정")
    
    m_options = ["약 복용", "주사 맞음", "복용 안함"]
    m_idx = m_options.index(current_val['아침기록']) if current_val['아침기록'] in m_options else 0
    edit_morning = st.radio("아침 기록", m_options, index=m_idx, horizontal=True)
    
    e_options = ["약 복용", "주사 맞음", "복용 안함"]
    e_idx = e_options.index(current_val['저녁기록']) if current_val['저녁기록'] in e_options else 0
    edit_evening = st.radio("저녁 기록", e_options, index=e_idx, horizontal=True)
    
    try: curr_w = float(current_val['몸무게'])
    except: curr_w = 55.0
    try: curr_p = int(current_val['통증'])
    except: curr_p = 0
        
    edit_weight = st.number_input("몸무게 (kg)", min_value=30.0, max_value=120.0, value=curr_w, step=0.1)
    edit_pain = st.number_input("통증 정도 (0~10)", min_value=0, max_value=10, value=curr_p, step=1)
    edit_notes = st.text_area("메모", value=current_val['메모'], height=180)
    
    if st.button("수정 완료", type="primary", use_container_width=True):
        try:
            fresh_df = conn.read(ttl=0).fillna("")
            if fresh_df.empty:
                st.error("⚠️ 인터넷 연결이 잠시 끊겼습니다. '수정 완료' 버튼을 다시 한번만 눌러주세요!")
            else:
                for col in fresh_df.columns:
                    fresh_df[col] = fresh_df[col].map(clean_val)
                
                fresh_df.at[rid, "아침기록"] = edit_morning
                fresh_df.at[rid, "저녁기록"] = edit_evening
                fresh_df.at[rid, "몸무게"] = str(edit_weight)
                fresh_df.at[rid, "통증"] = str(int(edit_pain))
                fresh_df.at[rid, "메모"] = edit_notes
                
                conn.update(data=fresh_df)
                st.success("수정 완료!")
                st.rerun()
        except:
            st.error("⚠️ 인터넷 연결이 잠시 끊겼습니다. '수정 완료' 버튼을 다시 한번만 눌러주세요!")

# 4. 화면 구성
st.title("오늘 하루 기록")
tab1, tab2, tab3, tab4 = st.tabs(["기록하기", "항암 차수", "기록보기", "기록요약"])

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
    notes = st.text_area("메모", placeholder="여기에 오늘의 특이사항을 기록해 주세요.", height=180)

    if st.button("기록 저장하기", type="primary", use_container_width=True):
        try:
            fresh_df = conn.read(ttl=0).fillna("")
            if fresh_df.empty and not df.empty:
                st.error("⚠️ 인터넷 연결이 잠시 끊겼습니다. '기록 저장하기' 버튼을 다시 한번만 눌러주세요!")
            else:
                for col in fresh_df.columns:
                    fresh_df[col] = fresh_df[col].map(clean_val)
                new_row = pd.DataFrame([{"날짜": datetime.now().strftime('%Y-%m-%d'), "아침기록": morning, "저녁기록": evening, "몸무게": weight, "통증": int(pain), "메모": notes}])
                conn.update(data=pd.concat([fresh_df, new_row], ignore_index=True))
                st.success("저장 완료!")
                st.rerun()
        except:
            st.error("⚠️ 인터넷 연결이 잠시 끊겼습니다. '기록 저장하기' 버튼을 다시 한번만 눌러주세요!")

with tab2:
    st.subheader("항암 차수 관리")
    ongoing = c_df[c_df['종료일'] == ''] if not c_df.empty else pd.DataFrame()
    if not ongoing.empty:
        curr = ongoing.iloc[-1]
        st.markdown(f'<div class="status-card"><h3 style="color:#007BFF; margin:0;">현재 {curr["차수"]}차 진행 중</h3><p style="margin:10px 0 0 0;">시작일: {curr["시작일"]}</p></div>', unsafe_allow_html=True)
        if st.button(f"{curr['차수']}차 종료하기", type="primary", use_container_width=True):
            idx = c_df[c_df['종료일'] == ''].index[-1]
            c_df.at[idx, '종료일'] = datetime.now().strftime('%Y-%m-%d')
            conn.update(worksheet="차수정보", data=c_df)
            st.rerun()
    else:
        st.info("현재 진행 중인 차수가 없습니다.")
        with st.form("new_cycle"):
            c_num = st.number_input("진행할 차수", min_value=1, step=1, value=len(c_df)+1)
            s_date = st.date_input("시작 날짜")
            if st.form_submit_button("새로운 차수 시작", type="primary", use_container_width=True):
                new_c = pd.DataFrame([{"차수": str(int(c_num)), "시작일": s_date.strftime('%Y-%m-%d'), "종료일": ""}])
                conn.update(worksheet="차수정보", data=pd.concat([c_df, new_c], ignore_index=True))
                st.rerun()

with tab3:
    if not df.empty:
        ongoing = c_df[c_df['종료일'] == '']
        if not ongoing.empty:
            st.markdown(f'<div class="status-card" style="background-color:#eef7ff;"><h3 style="color:#007BFF; margin:0;">항암 {ongoing.iloc[-1]["차수"]}차 진행 중</h3></div>', unsafe_allow_html=True)

        items = []
        for i, r in df.iterrows():
            if pd.notnull(r['dt']): 
                items.append({'d': r['dt'], 'p': 1, 'type': 'rec', 'v': r, 'id': i})
        for _, c in c_df.iterrows():
            sd = pd.to_datetime(c['시작일'], errors='coerce')
            ed = pd.to_datetime(c['종료일'], errors='coerce')
            if pd.notnull(sd): items.append({'d': sd, 'p': 0, 'type': 'start', 'v': c['차수'], 'ds': c['시작일']})
            if pd.notnull(ed): items.append({'d': ed, 'p': 2, 'type': 'end', 'v': c['차수'], 'ds': c['종료일']})
        
        items.sort(key=lambda x: (x['d'], x['p']), reverse=True)

        for item in items:
            if item['type'] == 'end':
                st.markdown(f'<div class="cycle-header end">항암 {item["v"]}차 종료 ({item["ds"]})</div>', unsafe_allow_html=True)
            elif item['type'] == 'start':
                st.markdown(f'<div class="cycle-header">항암 {item["v"]}차 시작 ({item["ds"]})</div>', unsafe_allow_html=True)
            elif item['type'] == 'rec':
                v, rid = item['v'], item['id']
                c1, c2, c3 = st.columns([0.8, 0.1, 0.1])
                with c3:
                    if st.button("❌", key=f"del_{rid}"):
                        try:
                            fresh_df = conn.read(ttl=0).fillna("")
                            if not fresh_df.empty:
                                conn.update(data=fresh_df.drop(rid).drop(columns=['dt'], errors='ignore'))
                                st.rerun()
                        except:
                            st.error("⚠️ 인터넷 연결이 잠시 끊겼습니다. 다시 한번 시도해 주세요.")
                with c2:
                    if st.button("🖋️", key=f"edit_trig_{rid}"):
                        edit_record_dialog(rid, v)
                with c1:
                    p_val = v.get('통증', '').strip()
                    if p_val == "":
                        p_display = "통증: 기록안함"
                    else:
                        p_display = f"통증: {p_val}/10"
                    
                    p_txt = f"<div style='font-size:16px; margin-top:5px;'>{p_display}</div>"
                    m_txt = f"<div style='border-top:1px solid #eee; margin-top:10px; padding-top:8px; font-size:16px;'>{v['메모']}</div>" if v['메모'] else ""
                    
                    html_content = f"""<div class="record-card">
<div style="display: flex; justify-content: space-between; align-items: baseline;">
<span style="font-size:19px; font-weight:bold;">{item['d'].strftime('%m월 %d일')}</span>
<span class="weight-box">{v['몸무게']} <small style="font-size:16px;">kg</small></span>
</div>
<div style="font-size:17px; margin-top:10px;">아침: {v['아침기록']} | 저녁: {v['저녁기록']}</div>
{p_txt}
{m_txt}
</div>"""
                    st.markdown(html_content, unsafe_allow_html=True)
    else:
        st.info("아직 기록이 없습니다.")

with tab4:
    st.subheader("최근 30일 기록 요약")
    
    if df.empty:
        st.info("최근 30일 동안의 기록이 없습니다.")
    else:
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_df = df[df['dt'] >= cutoff_date].copy()
        
        if recent_df.empty:
            st.info("최근 30일 동안의 기록이 없습니다.")
        else:
            recent_df = recent_df.sort_values('dt')
            recent_df['weight_num'] = pd.to_numeric(recent_df['몸무게'], errors='coerce')
            recent_df['pain_num'] = pd.to_numeric(recent_df['통증'], errors='coerce')
            
            min_d = recent_df['dt'].min()
            max_d = recent_df['dt'].max()
            tick_strings = [min_d.strftime('%Y-%m-%d'), max_d.strftime('%Y-%m-%d')]
            
            fig = go.Figure()

            # 몸무게 꺾은선 (두께 1.8 / 마커 3)
            fig.add_trace(go.Scatter(
                x=recent_df['dt'].dt.strftime('%Y-%m-%d'),
                y=recent_df['weight_num'],
                mode='lines+markers', name='몸무게 (kg)',
                line=dict(color='#007BFF', width=1.8),
                marker=dict(size=3),
                connectgaps=False
            ))

            # 통증 꺾은선 (두께 1.8 / 마커 3)
            fig.add_trace(go.Scatter(
                x=recent_df['dt'].dt.strftime('%Y-%m-%d'),
                y=recent_df['pain_num'],
                mode='lines+markers', name='통증',
                yaxis='y2',
                line=dict(color='#ff4b4b', width=1.8),
                marker=dict(size=3),
                connectgaps=False
            ))

            # [수정사항] 글자들이 아래로 내려오므로 하단 마진(b)을 70으로 늘려 컷팅을 방증함
            fig.update_layout(
                xaxis=dict(
                    type='date',
                    tickmode='array',
                    tickvals=tick_strings,
                    tickformat='%m/%d',
                    showgrid=False
                ),
                yaxis=dict(
                    title=dict(text='몸무게 (kg)', font=dict(color='#007BFF', size=13)),
                    tickfont=dict(color='#007BFF', size=11),
                    tickmode='array',
                    tickvals=[35.0, 45.0, 55.0],
                    range=[35.0, 55.0],
                    tickformat='.1f',
                    showgrid=True,
                    gridcolor='#eee'
                ),
                yaxis2=dict(
                    title=dict(text='통증', font=dict(color='#ff4b4b', size=13)),
                    tickfont=dict(color='#ff4b4b', size=11),
                    tickmode='array',
                    tickvals=[0, 5, 10],
                    range=[0, 10],
                    anchor='x',
                    overlaying='y',
                    side='right',
                    showgrid=False
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=40, b=70),
                plot_bgcolor='white',
                paper_bgcolor='white',
                hovermode='x unified'
            )
            
            # [수정사항] 항암 일정을 가로축 아래 여백(yref="paper", y값 음수 영역)에 지정된 층별 높이로 배치
            # 시작은 위쪽(y=-0.18), 종료는 아래쪽(y=-0.32)으로 조율하여 오버랩 원천 해결
            for _, c in c_df.iterrows():
                sd = pd.to_datetime(c['시작일'], errors='coerce')
                ed = pd.to_datetime(c['종료일'], errors='coerce')
                if pd.notnull(sd) and (min_d <= sd <= max_d):
                    fig.add_vline(x=sd.strftime('%Y-%m-%d'), line_width=1.5, line_dash="dash", line_color="#b3b3b3")
                    fig.add_annotation(
                        x=sd.strftime('%Y-%m-%d'), y=-0.18, yref="paper",
                        text=f"{c['차수']}차 시작 ({sd.strftime('%m/%d')})",
                        showarrow=False, font=dict(size=10, color="#222222"), bgcolor="rgba(240,247,255,0.9)"
                    )
                if pd.notnull(ed) and (min_d <= ed <= max_d):
                    fig.add_vline(x=ed.strftime('%Y-%m-%d'), line_width=1.5, line_dash="dash", line_color="#b3b3b3")
                    fig.add_annotation(
                        x=ed.strftime('%Y-%m-%d'), y=-0.32, yref="paper",
                        text=f"{c['차수']}차 종료 ({ed.strftime('%m/%d')})",
                        showarrow=False, font=dict(size=10, color="#555555"), bgcolor="rgba(245,245,245,0.9)"
                    )

            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
