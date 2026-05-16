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
    notes = st.text_area("메모", placeholder="여기에 오늘의 특이사항을 기록해 주세요.")

    if st.button("기록 저장하기", type="primary", use_container_width=True):
        new_row = pd.DataFrame([{"날짜": datetime.now().strftime('%Y-%m-%d'), "아침기록": morning, "저녁기록": evening, "몸무게": weight, "통증": int(pain), "메모": notes}])
        conn.update(data=pd.concat([df.drop(columns=['dt'], errors='ignore'), new_row], ignore_index=True))
        st.success("저장 완료!")
        st.rerun()

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
                c1, c2 = st.columns([0.9, 0.1])
                with c2:
                    if st.button("❌", key=f"del_{rid}"):
                        conn.update(data=df.drop(rid).drop(columns=['dt'], errors='ignore'))
                        st.rerun()
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
            
            # 1) X축 표시 날짜 구하기 및 호환성 높은 '문자열' 포맷으로 변경
            min_d = recent_df['dt'].min()
            max_d = recent_df['dt'].max()
            tick_dates = [min_d, max_d]
            
            for _, c in c_df.iterrows():
                sd = pd.to_datetime(c['시작일'], errors='coerce')
                ed = pd.to_datetime(c['종료일'], errors='coerce')
                if pd.notnull(sd) and (min_d <= sd <= max_d):
                    tick_dates.append(sd)
                if pd.notnull(ed) and (min_d <= ed <= max_d):
                    tick_dates.append(ed)
                    
            tick_dates = sorted(list(set(tick_dates)))
            tick_strings = [d.strftime('%Y-%m-%d') for d in tick_dates]
            
            # 2) 왼쪽 Y축 (몸무게) 유효성 및 타입 검사
            valid_w = recent_df['weight_num'].dropna()
            
            # 3) 그래프 객체 생성
            fig = go.Figure()

            # 몸무게 선
            fig.add_trace(go.Scatter(
                x=recent_df['dt'].dt.strftime('%Y-%m-%d'),
                y=recent_df['weight_num'],
                mode='lines+markers', name='몸무게 (kg)',
                line=dict(color='#007BFF', width=3),
                marker=dict(size=8),
                connectgaps=False
            ))

            # 통증 선
            fig.add_trace(go.Scatter(
                x=recent_df['dt'].dt.strftime('%Y-%m-%d'),
                y=recent_df['pain_num'],
                mode='lines+markers', name='통증',
                yaxis='y2',
                line=dict(color='#ff4b4b', width=3),
                marker=dict(size=8),
                connectgaps=False
            ))

            # [에러 해결 핵심] 기본 안전 레이아웃 구성
            layout_kwargs = dict(
                xaxis=dict(
                    tickmode='array',
                    tickvals=tick_strings,
                    tickformat='%m/%d',
                    showgrid=False
                ),
                yaxis=dict(
                    title='몸무게 (kg)',
                    titlefont=dict(color='#007BFF'),
                    tickfont=dict(color='#007BFF', size=11),
                    showgrid=True,
                    gridcolor='#eee'
                ),
                yaxis2=dict(
                    title='통증',
                    tickmode='array',
                    tickvals=[0, 5, 10],
                    range=[0, 10],
                    titlefont=dict(color='#ff4b4b'),
                    tickfont=dict(color='#ff4b4b', size=11),
                    anchor='x',
                    overlaying='y',
                    side='right',
                    showgrid=False
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=40, b=0),
                plot_bgcolor='white',
                paper_bgcolor='white',
                hovermode='x unified'
            )
            
            # 몸무게 수치가 존재할 때만 3개 점 눈금을 순수 float형태로 주입해 ValueError 차단
            if not valid_w.empty:
                w_max = float(valid_w.max())
                w_min = float(valid_w.min())
                if w_max == w_min:
                    w_ticks = [w_min]
                else:
                    w_ticks = [w_min, float((w_min + w_max) / 2), w_max]
                layout_kwargs['yaxis']['tickmode'] = 'array'
                layout_kwargs['yaxis']['tickvals'] = w_ticks
                layout_kwargs['yaxis']['tickformat'] = '.1f'

            fig.update_layout(**layout_kwargs)
            st.plotly_chart(fig, use_container_width=True)
