import streamlit as st

from pages.login import login
from pages.survey import survey
from pages.demographics import demographics
from pages.instruction import instruction
from pages.tutorial import begin_tutorial, end_tutorial
from pages.main_study_new import main_study
from pages.evaluation import evaluation

st.set_page_config(layout="wide")

# Force condition to "E. Editable Local Suggestion"
for key in ["completion", "text_input_buffer", "last_sent_input"]:
    if key not in st.session_state:
        st.session_state[key] = ""

def main():
    if st.session_state.get("condition") != "E. Editable Local Suggestion" or "condition" not in st.session_state:
        st.session_state.condition = "E. Editable Local Suggestion"
    run_app()

def run_app():
    if "page" not in st.session_state:
        st.session_state.page = "login"

    if st.session_state.page == "login":
        login()
    elif st.session_state.page == "survey":
        survey()
    elif st.session_state.page == "demographics":
        demographics()
    elif st.session_state.page == "instruction":
        instruction()
    elif st.session_state.page == "begin_tutorial":
        begin_tutorial()
    elif st.session_state.page == "end_tutorial":
        end_tutorial()
    elif st.session_state.page == "main_study":
        main_study()
    elif st.session_state.page == "evaluation":
        evaluation()

if __name__ == "__main__":
    main()
