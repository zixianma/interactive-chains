import streamlit as st
st.set_page_config(layout="wide")

from pages.login import login
from pages.main_study import main_study
from pages.survey import survey
from pages.demographics import demographics

def main():

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"][aria-expanded="true"]{
            min-width: 600px;
        }
        /* Increase the font size of the radio button header */
        .stRadio label p {
            font-size: 24px !important;
        }
        /* Increase the font size of the radio button options */
        .stRadio div[data-baseweb="radio"] div.st-cx p {
            font-size: 22px !important;
        }
        /* slider text */
        div[class*="stSlider"] > label > div[data-testid="stMarkdownContainer"] > p {
            font-size: 24px;
        }
        .stRadio {
            margin-bottom: 20px; /* Adjust this value to control the space between sliders and other elements */
        }
        .stSlider {
            width: 50% !important;
            margin-bottom: 20px; /* Adjust this value to control the space between sliders and other elements */
        }
    /* Increase the font size of the slider's min and max values */
    [data-testid="stTickBar"] > div {
        font-size: 22px !important;
    }

    /* Increase the font size of the current value displayed on the slider thumb */
    .StyledThumbValue {
        font-size: 22px !important; /* Adjust this value as needed */
    }
        """,
        unsafe_allow_html=True,
    )   

    # Initialize the session state page if not already set
    if 'page' not in st.session_state:
        st.session_state.page = 'login'

    # Display the chosen page based on session state
    if st.session_state.page == "login":
        login()
    elif st.session_state.page == 'main_study':
        main_study()
    elif st.session_state.page == 'demographics':
        demographics()
    elif st.session_state.page == 'survey':
        survey()

if __name__ == "__main__":
    main()