import streamlit as st
from pages.main_study_new import show_step_2, load_data

st.set_page_config(layout="wide")

if "condition" not in st.session_state:
    st.session_state.condition = "F. Editable Global Suggestion" 
    #"D. Step-by-step CoT -- Sequential"
    #"G. Streamlit autorefresh" 
    #E. Verifiable CoT

if "questions" not in st.session_state:
    st.session_state.questions = load_data(path="data/question_bank_final_cleaned.jsonl")

if "question_index" not in st.session_state:
    st.session_state.question_index = 1

show_step_2(st.session_state.question_index)