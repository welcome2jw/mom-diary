import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="간편 기록", layout="centered")

# 2. CSS 스타일 (가장 단순하고 강력한 선택자 사용)
st.markdown("""
    <style>
    /* 전체 폰트 및 배경 */
    .stApp { background-color: white; }
    
    /* 차수 바 */
    .bar {
        padding: 10px; border-radius: 10px; text-align: center; font-weight: bold;
        margin: 20px 0; color: white;
    }
    .start-bar { background-color: #007BFF; }
    .end-bar { background-color: #6c757d; }

    /* 기록 카드 */
    .card {
        border: 1px solid #ddd; border-radius: 15px; padding: 20px;
        margin-bottom: 15px; background-color: #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    /* [수정] X 버튼: 투명 배경, 테두리 없음, 빨간 글자만 */
    button[kind="secondary"] {
        background: transparent !important;
        border: none !important;
        color: #ff4b4b !important;
        box-shadow: none !important;
        font-size: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 로드 및 클리닝 함수 (가장 확실한 전처리)
def clean_val(val):
    """모든 데이터를 문자열로 바꾸고 .0과 nan을 제거"""
    s = str(val).replace('.0', '').strip()
    if s.lower() in ['nan', 'none', 'nat', '']: return ""
    return s

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    m_df = conn.read(ttl=0).fillna("")
    c_df = conn.read(worksheet="차수정보", ttl=0).fillna("")
    # 전체 데이터 클리닝
    m_df = m_df.applymap(clean_val)
    c_df = c_df.applymap(clean_val)
    if not m_df.empty:
        m_df['dt'] = pd.to_datetime(m_df['날짜'], errors='coerce')
    return m_df, c_df

df, c_df = get_data()

# 4. 화면 구성
st.title("오늘 하루 기록")
t1, t2, t3 = st.tabs(["기록하기", "차수 관리", "기록보기"])

with t1:
    with st.form("input_form"):
        st.write(f"### {datetime.now().strftime('%Y년 %m월 %d일')}")
        m = st.radio("아침", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
        e = st.radio("저녁", ["약 복용", "주사 맞음", "복용 안함"], horizontal=True)
        w = st.number_input("몸무게 (kg)", value=55.0, step=0.1)
        p = st.number_input("통증 (0~10)", min_value=0, max_value=10, step=1)
        memo = st.text_area("메모", placeholder="여기에 오늘의 특이사항을 기록해 주세요.")
        if st.form_submit_button("기록 저장"):
            new_data = pd.DataFrame([{"날짜": datetime.now().strftime('%Y-%m-%d'), "아침기록": m, "저녁기록": e, "몸무게": w, "통증": p, "메모": memo}])
            conn.update(data=pd.concat([df.drop(columns=['dt'], errors='ignore'), new_data], ignore_index=True))
            st.rerun()

with t2:
    st.subheader("항암 차수 설정")
    ongoing = c_df[c_df['종료일'] == ""]
    if not ongoing.empty:
        cur = ongoing.iloc[-1]
        st.info(f"현재 {cur['차수']}차 진행 중 (시작: {cur['시작일']})")
        if st.button(f"{cur['차수']}차 종료하기"):
            c_df.loc[c_df['종료일'] == "", '종료일'] = datetime.now().strftime('%Y-%m-%d')
            conn.update(worksheet="차수정보", data=c_df)
            st.rerun()
    else:
        with st.form("cycle_form"):
            c_num = st.number_input("신규 차수", value=len(c_df)+1, step=1)
            c_start = st.date_input("시작일")
            if st.form_submit_button("차수 시작"):
                new_c = pd.DataFrame([{"차수": str(int(c_num)), "시작일": c_start.strftime('%Y-%m-%d'), "종료일": ""}])
                conn.update(worksheet="차수정보", data=pd.concat([c_df, new_c], ignore_index=True))
                st.rerun()

with t3:
    if not df.empty:
        # 이벤트 통합 (날짜, 우선순위, 데이터)
        items = []
        for i, r in df.iterrows():
            if r['dt']: items.append({'d': r['dt'], 'p': 1, 'type': 'rec', 'v': r, 'id': i})
        for _, c in c_df.iterrows():
            sd = pd.to_datetime(c['시작일'], errors='coerce')
            ed = pd.to_datetime(c['종료일'], errors='coerce')
            if sd: items.append({'d': sd, 'p': 0, 'type': 'start', 'v': c['차수'], 'ds': c['시작일']})
            if ed: items.append({'d': ed, 'p': 2, 'type': 'end', 'v': c['차수'], 'ds': c['종료일']})
        
        # 정렬: 날짜 최신순 -> 같은 날짜면 종료(2)-기록(1)-시작(0) 순서
        items.sort(key=lambda x: (x['d'], x['p']), reverse=True)

        for item in items:
            if item['type'] == 'end':
                st.markdown(f"<div class='bar end-bar'>항암 {item['v']}차 종료 ({item['ds']})</div>", unsafe_allow_html=True)
            elif item['type'] == 'start':
                st.markdown(f"<div class='bar start-bar'>항암 {item['v']}차 시작 ({item['ds']})</div>", unsafe_allow_html=True)
            elif item['type'] == 'rec':
                v, rid = item['v'], item['id']
                c1, c2 = st.columns([0.9, 0.1])
                with c2:
                    if st.button("❌", key=f"del_{rid}"):
                        conn.update(data=df.drop(rid).drop(columns=['dt'], errors='ignore'))
                        st.rerun()
                with c1:
                    # 통증/메모 조건부 출력 (HTML 에러 방지 위해 별도 변수화)
                    p_txt = f"<div style='color:red; margin-top:5px;'>통증: {v['통증']}/10</div>" if v['통증'] not in ["0", ""] else ""
                    m_txt = f"<div style='border-top:1px solid #eee; margin-top:10px; padding-top:10px;'>{v['메모']}</div>" if v['메모'] else ""
                    
                    st.markdown(f"""
                    <div class="card">
                        <div style="display:flex; justify-content:space-between;">
                            <b style="font-size:1.2rem;">{item['d'].strftime('%m월 %d일')}</b>
                            <b style="color:#007BFF; font-size:1.4rem;">{v['몸무게']}kg</b>
                        </div>
                        <div style="margin-top:10px;">아침: {v['아침기록']} | 저녁: {v['저녁기록']}</div>
                        {p_txt}
                        {m_txt}
                    </div>
                    """, unsafe_allow_html=True)
