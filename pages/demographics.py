from streamlit_float import *
import re
import gspread
from google.oauth2.service_account import Credentials
import toml
from datetime import datetime
import pages.utils.logger as logger
import sys

def record_data_clear_state(keys_list = []):
    # convert the data from dict to tuple
    responses_dict = []
    keys = keys_list
    for key in keys:
        if key in st.session_state:
            # will change this later, doing as sanity checker for now
            responses_dict.append((key, st.session_state[key]))
    logger.write_survey_response(responses_dict)
    # Delete all keys in the list
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]

# Change this to get to the correct next page
def finished():
    st.title("Thank you for your time!")
    st.session_state.page = "main_study"
    st.rerun()
    # st.subheader("Click below to complete the study.")
    # st.write("Insert link here.")
    
def free_form_questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()
        
    st.title("Free Form Response Questions")
    st.subheader("Note: You cannot go back, please take your time answering these.")
    st.subheader("You must answer all of the questions here before clicking submit to be paid.")
    
    # Question 1: Age
    st.markdown("#### What is your age?")
    st.session_state.age = st.text_input(
        "Please enter your age:",
        value=st.session_state.get('age', ''),
        key='age_input'
    )
    
    # Question 2: Job Title
    st.markdown("#### What is your job title?")
    st.session_state.job_title = st.text_input(
        "Please enter your job title:",
        value=st.session_state.get('job_title', ''),
        key='job_title_input'
    )
    
    # Question 3: Area of expertise
    st.markdown("#### What are your areas of expertise?")
    st.session_state.areas_of_expertise = st.text_input(
        "Please enter your areas of expertise:",
        value=st.session_state.get('areas_of_expertise', ''),
        key='expertise_input'
    )
    
    if st.button('Submit', key="submit_answers"):
        if any([
                st.session_state.age.strip() == '',
                st.session_state.job_title.strip() == '',
                st.session_state.areas_of_expertise.strip() == ''
            ]):
            st.error("Please fill in all the text boxes before submitting.")
        else:
            try:
                # ensure the age input is a valid number and in a valid range
                age = int(st.session_state.age.strip())
                if age <= 0 or age > 120:
                    st.error("Please enter a valid age between 1 and 120.")
                else:
                    end_time = datetime.now()
                    st.session_state.time_spent = str((end_time - st.session_state.time_spent).total_seconds())
                    record_data_clear_state(['age', 'job_title', 'areas_of_expertise'])
                    # Navigate to completion page
                    st.session_state.qa_page = 'complete'
                    st.rerun()
            except ValueError:
                st.error("Please enter a valid numeric age.")

def multiple_choice_questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()
        
    st.title("Multiple Choice Questions")
    st.subheader("Note: You cannot go back, please take your time answering these.")
    st.subheader("You must answer all of the questions here before clicking submit to be paid.")
    
    # Placeholder text for unselected options
    gender_placeholder = "Select your gender"
    race_ethnicity_placeholder = "Select your race/ethnicity"
    ai_ml_placeholder = "Select your familiarity level with AI/ML"
    
    # Question 1: Gender
    st.markdown("#### Q1: What is your gender?")
    st.session_state.gender = st.radio(
        "Please select your gender:",
        options=[
            gender_placeholder,
            "Woman",
            "Man",
            "Non-binary",
            "Prefer not to disclose",
            "Self-described"
        ],
        horizontal=True,
        key='gender_radio'
    )
    
    if st.session_state.gender == "Self-described":
        st.session_state.gender_self_described = st.text_input(
            "Please describe your gender:",
            value=st.session_state.get('gender_self_described', ''),
            key='gender_self_described_input'
        )
    else:
        st.session_state.gender_self_described = "" 
    
    # Question 2: Race/Ethnicity
    st.markdown("#### Q2: What is your race/ethnicity?")
    st.session_state.race_ethnicity = st.radio(
        "Please select your race/ethnicity:",
        options=[
            race_ethnicity_placeholder,
            "American Indian or Alaska Native",
            "Asian",
            "Black or African American",
            "Hispanic or Latino",
            "Native Hawaiian or Other Pacific Islander",
            "White",
            "Prefer not to say",
            "Other"
        ],
        horizontal=True,
        key='race_ethnicity_radio'
    )
    
    if st.session_state.race_ethnicity == "Other":
        st.session_state.race_ethnicity_other = st.text_input(
            "Please specify your race/ethnicity:",
            value=st.session_state.get('race_ethnicity_other', ''),
            key='race_ethnicity_other_input'
        )
    else:
        st.session_state.race_ethnicity_other = ""
        
    # Question 3: Familiarity with AI/ML
    st.markdown("#### Q3: How familiar are you with Artificial Intelligence (AI)/Machine Learning (ML)?")
    st.session_state.ai_ml_familiarity = st.radio(
        "Please select your familiarity with AI/ML:",
            options=[
                ai_ml_placeholder,
                "Very unfamiliar (I've never heard about AI/ML.)",
                "Unfamiliar (I've heard very little about AI/ML.)",
                "Somewhat unfamiliar (I've heard about AI/ML, but I don't know how AI/ML works.)",
                "Neutral (I kind of know how AI/ML works, and I've used a couple of AI/ML models.)",
                "Somewhat familiar (I know how AI/ML works, and I've trained a couple of AI/ML models end to end.)",
                "Familiar (I know exactly how AI/ML works, and I've trained multiple AI/ML models end to end.)",
                "Very familiar (I've earned a degree in AI/ML, or I'm very familiar with training AI/ML models end to end.)"
            ],
            horizontal=True,
            key='ai_ml_familiarity_radio'
    )
    
    if st.button("Submit", key="submit_mcq"):
        # Check if the "Self-described" or "Other" field is filled if selected
        if st.session_state.gender == gender_placeholder:
            st.error("Please select your gender.")
        elif st.session_state.gender == "Self-described" and st.session_state.gender_self_described.strip() == '':
            st.error("Please describe your gender in the 'Self-described' field.")
        elif st.session_state.race_ethnicity == race_ethnicity_placeholder:
            st.error("Please select your race/ethnicity.")
        elif st.session_state.race_ethnicity == "Other" and st.session_state.race_ethnicity_other.strip() == '':
            st.error("Please specify your race/ethnicity in the 'Other' field.")
        elif st.session_state.ai_ml_familiarity == ai_ml_placeholder:
            st.error("Please select your familiarity level with AI/ML.")
        else:
            end_time = datetime.now()
            st.session_state.time_spent = str((end_time - st.session_state.time_spent).total_seconds())
            record_data_clear_state([
                'gender', 
                'gender_self_described', 
                'race_ethnicity', 
                'race_ethnicity_other', 
                'ai_ml_familiarity', 
                'time_spent'
            ])
            st.session_state.qa_page = 'frq'
            st.rerun()
    
def demographics():
    st.title("Demographics Questions")

    if 'qa_page' not in st.session_state:
        st.session_state.qa_page = 'multi_choice_questions'

    placeholder = st.empty()

    with placeholder.container():
        if st.session_state.qa_page == 'multi_choice_questions':
            multiple_choice_questions()
        elif st.session_state.qa_page == 'frq':
            free_form_questions()
        elif st.session_state.qa_page =='complete':
            finished()
    