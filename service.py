import os
import streamlit as st
import time
import pandas as pd
from rag_load import load_rag
from gpt_make_response import call_gpt_summary, answer_query, search_similar_documents

st.set_page_config(page_title="관공서 민원 챗봇", page_icon="🏛️", layout="wide")
st.title("🏛️ 관공서 민원 챗봇 - 관공이")
st.markdown("민원 내용을 정확히 파악하여 도움을 드립니다.")

# 실행할 때마다 cache 초기화 -> cache가 기존 정보를 제공해서 응답이 희석될 수 있다고 합니다
st.cache_resource.clear()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "selected_top" not in st.session_state:
    st.session_state.selected_top = None
if "selection_locked" not in st.session_state:
    st.session_state.selection_locked = False
if "selection_confirmed" not in st.session_state:
    st.session_state.selection_confirmed = False

# 벡터 DB 및 model 불러오기
@st.cache_resource
def load_rag_cached():
    return load_rag()
model, index, documents, metadatas = load_rag_cached()

# 행민 데이터, rule base를 위한 전화번호 매핑 테이블 로드
base_dir = os.path.dirname(__file__)  # service.py가 있는 디렉토리
df_info = pd.read_excel(os.path.join(base_dir, "행정안전부_민원안내정보_20250327.xlsx"))
df_contact = pd.read_excel(os.path.join(base_dir, "대표_소관부처_민원_연락망_매핑표.xlsx"))
contact_lookup = df_contact.set_index("부처명")["대표전화"].to_dict()


for idx, entry in enumerate(st.session_state.chat_history):
    with st.chat_message("user"):
        st.markdown(entry["query"])

    with st.chat_message("assistant"):
        st.markdown("### 🔍 추천 Top 3")
        if st.session_state.selection_locked and st.session_state.selected_top and st.session_state.selected_top[0] == idx:
            selected_index = st.session_state.selected_top[1]
            result = entry["top3"][selected_index]

            st.markdown(f"#### 📜 **한줄 답변**\n {result['solution_summary']}")
            st.markdown(f"📌 **소관부처:** `{result['ministry']}`")
            st.markdown(f"📂 **담당부서:** `{result['department']}`")
            st.markdown(f"📞 **전화번호:** `{result['phone']}`")
            st.markdown(result["title"])
            with st.expander("📄 자세히 보기"):
                st.markdown(result["solution_full"])

            col_confirm, col_reset = st.columns([1, 1])
            with col_reset:
                if st.button("🔄 다시 선택하기", key=f"reselect_{idx}"):
                    st.session_state.selection_locked = False
                    st.session_state.selected_top = None
                    st.session_state.selection_confirmed = False
                    st.rerun()
            with col_confirm:
                if st.button("✅ 확정", key=f"confirm_{idx}"):
                    st.success("선택이 확정되었습니다. 다음 단계로 진행할 수 있습니다.")
                    st.session_state.selection_confirmed = True
        else:
            col1, col2, col3 = st.columns(3)
            for i, (col, result) in enumerate(zip([col1, col2, col3], entry["top3"])):
                with col:
                    selected = (st.session_state.selected_top == (idx, i))
                    if selected:
                        st.markdown(f"#### 📜 **한줄 답변**\n {result['solution_summary']}")
                        st.success("이 항목을 선택하셨습니다.")
                    else:
                        st.markdown(f"#### 📜 **한줄 답변**\n {result['solution_summary']}")
                    st.markdown(f"📌 **소관부처:** `{result['ministry']}`")
                    st.markdown(f"📂 **담당부서:** `{result['department']}`")
                    st.markdown(f"📞 **전화번호:** `{result['phone']}`")
                    st.markdown(f"👩‍💻 **사무명:** {result["title"]}")
                    with st.expander("📄 자세히 보기"):
                        st.markdown(result["solution_full"])
                    if st.button(f"✔️ Top {i+1} 선택", key=f"select_{idx}_{i}"):
                        st.session_state.selected_top = (idx, i)
                        st.session_state.selection_locked = True
                        st.rerun()

query = st.chat_input("궁금한 민원을 입력하세요:")

if query:
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        for dot in ["", ".", "..", "..."]:
            placeholder.markdown(f"⌛ 민원 처리 방법을 확인하고 있어요{dot}")
            time.sleep(0.4)
        placeholder.empty()

        # 유사도 top 3 문서 가져오기
        top3_docs = search_similar_documents(query, model, index, documents, metadatas)

        # I[0]에 담겨있는 index 3개를 바탕으로, meta데이터에서 사무명, 소관부처, 담당부서를 갖고 옵니다
        # 해당 데이터는 답변의 rule-base 정보를 뽑을 때 사용됩니다
        top3_results = []
        for doc, meta in top3_docs:
            title = meta.get("사무명", "관련 민원")
            ministry = meta.get("소관부처", "정보 없음")
            department = meta.get("담당부서", "정보 없음")
            phone = contact_lookup.get(ministry, "정보 없음")

            summary = call_gpt_summary(query)         # 질문만 보고 요약
            full = answer_query(query, meta["원문"])           # 문서 + 질문 기반 정밀 응답

            top3_results.append({
                "title": title,
                "solution_summary": summary,
                "solution_full": full,
                "ministry": ministry,
                "department": department,
                "phone": phone
            })

        st.markdown("### 🔍 추천 Top 3")
        cols = st.columns(3)
        for i, (col, result) in enumerate(zip(cols, top3_results)):
            with col:
                st.markdown(f"#### 📜 **한줄 답변**\n {result['solution_summary']}")
                st.markdown(f"📌 **소관부처:** `{result['ministry']}`")
                st.markdown(f"📂 **담당부서:** `{result['department']}`")
                st.markdown(f"📞 **전화번호:** `{result['phone']}`")
                st.markdown(f"👩‍💻 **사무명:** {result["title"]}")
                with st.expander("📄 자세히 보기"):
                    st.markdown(result["solution_full"])
                if st.button(f"✔️ Top {i+1} 선택", key=f"select_new_{i}"):
                    st.session_state.selected_top = (len(st.session_state.chat_history), i)
                    st.session_state.selection_locked = True
                    st.rerun()

        st.session_state.chat_history.append({
            "query": query,
            "top3": top3_results
        })

with st.sidebar:
    st.markdown("## 📋 사용 안내")
    st.markdown("""
    **관공서 민원 챗봇 사용법:**

    1️⃣ **민원 내용 입력**
    - 궁금한 민원 사항을 입력해주세요

    2️⃣ **결과 확인**
    - 가장 적합한 응답 3개가 나와요
    - 도움이 되는 응답 1개를 선택해주시면 됩니다!
    """)
    st.markdown("---")
    st.markdown("**💡 팁:**")
    st.markdown("""
    - 구체적으로 상황을 설명해주세요
    - 예시) "어떤 상황"에, "어떻게" 해야할까?
    - 예시) "어떤 상황"에, "무엇"일까?
    - 궁금한 점이 있으면 언제든 질문하세요
    """)
    st.markdown("---")
    if st.button("🗑️ 대화 초기화", help="현재 대화를 모두 삭제하고 새로 시작"):
        st.session_state.chat_history = []
        st.session_state.selected_top = None
        st.rerun()
