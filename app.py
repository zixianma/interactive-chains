import streamlit as st
st.set_page_config(layout="wide")

from pages.login import login
from pages.main_study import main_study
from pages.survey import survey
from pages.demographics import demographics
from pages.instruction import instruction
import streamlit.components.v1 as components

def main():
    
    hotjar_injection_script = """
    <script>
        (function() {
            var scriptElement = document.createElement('script');
            scriptElement.innerHTML = "(function(h,o,t,j,a,r){h.hj=h.hj||function(){(h.hj.q=h.hj.q||[]).push(arguments)};h._hjSettings={hjid:5124090,hjsv:6};a=o.getElementsByTagName('head')[0];r=o.createElement('script');r.async=1;r.src=t+h._hjSettings.hjid+j+h._hjSettings.hjsv;a.appendChild(r);})(window,document,'https://static.hotjar.com/c/hotjar-','.js?sv=');";
            document.getElementsByTagName('head')[0].appendChild(scriptElement);
        })();
    </script>
    """

    # Inject the Hotjar script using Streamlit components
    components.html(hotjar_injection_script, height=0, width=0)

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
        /* text input */
        .stTextInput [disabled=""]{
        -webkit-text-fill-color: black;
        }
        /* text area */
        .stTextArea [disabled=""]{
        -webkit-text-fill-color: black;
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
            font-size: 22px !important;
        }

        /* increase thickness of slider */
            [data-baseweb="slider"] > div > div > div {
            height: 16px !important;  /* Adjust this value to increase thickness */
        }

        /* Increase the font size of the <p> tag inside the stTextArea */
        .stTextArea label p {
            font-size: 24px !important;
        }
        """,
        unsafe_allow_html=True,
    ) 

    # Initialize the session state page if not already set
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
        # st.session_state.page =  "main_study" #

    # Display the chosen page based on session state
    if st.session_state.page == "login":
        login()
    elif st.session_state.page == "instruction":
        instruction()
    elif st.session_state.page == 'main_study':
        main_study()
    elif st.session_state.page == 'demographics':
        demographics()
    elif st.session_state.page == 'survey':
        survey()

if __name__ == "__main__":
    main()