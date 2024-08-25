import streamlit as st
import requests
from streamlit_float import *
from google.oauth2.service_account import Credentials
import toml

def get_user_ip():
    try:
        ip = requests.get('https://api64.ipify.org?format=json').json()["ip"]
        response = requests.get(f'https://ipinfo.io/{ip}/json')
        data = response.json()
        location = {
            'ip': data.get('ip'),
            'city': data.get('city'),
            'region': data.get('region'),
            'country': data.get('country'),
            'loc': data.get('loc'),  # Latitude and Longitude
            'org': data.get('org'),
            'timezone': data.get('timezone')
        }
        return location
    except Exception as e:
        return {"error": str(e)}

def submit_consent(username_input):
    if not username_input:
        st.warning("Please fill in all required fields.")
    else:
        st.session_state.username = st.session_state.username_input

def login():
    if 'username' not in st.session_state:
        st.session_state.username = ''

    # if 'consent' not in st.session_state:
    #     st.session_state.consent = ''

    if 'user_data' not in st.session_state:
        st.session_state.user_data = {
            "visits": 0,
            'last question idx done': -1,
            'location data': get_user_ip()
        }

    if not st.session_state.username: #and not st.session_state.consent
        st.title("Welcome to the Application")
        

        st.subheader("Please carefully read below before proceeding.")
        st.write("""You are invited to participate in a research study on user understanding of algorithms and models. You will be asked to answer multiple choice and free response questions about different provided algorithms and their expected behavior. You will not be recorded via audio or video.\n
    TIME INVOLVEMENT: Your participation will take approximately 30 minutes.\n
    PAYMENTS: You will receive \$7.50 via the survey platform upon completion of the study, and you will receive additional compensation of \$0.10 per correct answer afterwards, as payment for your participation. A total of up to $1.50 in bonuses is available.\n
    RISKS AND BENEFITS: The risks associated with this study are minimal. A potential data breach or breach of confidentiality should not adversely affect employment or reputation. Study data will be stored securely, in compliance with University of Washington standards, minimizing the risk of confidentiality breach. You may be exposed to content that is upsetting, as this study involves a wide array of statements to validate, some of which contain harmful text (e.g., profanity, slurs, expressions of bigotry like racism/sexism/homophobia/religious intolerance, discussion of violence, jokes about tragedies). The benefits which may reasonably be expected to result from this study are none. We cannot and do not guarantee or promise that you will receive any benefits from this study.\n
    PARTICIPANT’S RIGHTS: If you have read this form and have decided to participate in this project, please understand your participation is voluntary and you have the right to withdraw your consent or discontinue participation at any time without penalty or loss of benefits to which you are otherwise entitled. The alternative is not to participate. You have the right to refuse to answer particular questions. The results of this research study may be presented at scientific or professional meetings or published in scientific journals. Your individual privacy will be maintained in all published and written data resulting from the study.\n
    CONTACT INFORMATION: If you have any questions, concerns or complaints about this research, its procedures, risks and benefits, contact the Protocol Director, Zixian Ma, at zixianma@uw.edu.\n
    Independent Contact: If you are not satisfied with how this study is being conducted, or if you have any concerns, complaints, or general questions about the research or your rights as a participant, please contact the University of Washington Institutional Review Board (IRB) to speak to someone independent of the research team at 206-543-0098, or email at hsdreprt@uw.edu. You can also write to the University of Washington IRB at Human Subjects Division, University of Washington, Box 359470, 4333 Brooklyn Ave NE, Seattle, WA 98195-9470.""")
        st.subheader("If you consent to participate in our study, please enter your username from Prolific to continue:")
        # Input field for the username
        username_input = st.text_input("Username", key="username_input").strip()

        # # Input field for the consent
        # consent_input = st.text_input("Do you consent? (Input 'Yes' or 'No')", key="consent_input").strip()

        # Submit button
        st.button("Submit", on_click=submit_consent, args=(username_input,))
        st.session_state.page = "main_study"
        st.rerun()

    else:
        toml_data = toml.load(".streamlit/secrets.toml")
        credentials_data = toml_data["connections"]["gsheets"]
        st.session_state.page = "main_study"
        st.rerun()