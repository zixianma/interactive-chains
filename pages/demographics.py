from streamlit_float import *
import streamlit as st
from datetime import datetime
import pages.utils.logger as logger

def record_data_clear_state(keys_list = []):
    # convert the data from dict to tuple
    responses_dict = []
    keys = keys_list
    for key in keys:
        if key in st.session_state:
            # will change this later, doing as sanity checker for now
            responses_dict.append((key, st.session_state[key]))
    logger.write_survey_response(responses_dict, header=True, survey_type='DEMOGRAPHICS') # this is assuming all of this is on one page.
    # Delete all keys in the list
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]

def questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()
        
    # st.subheader("Note: You must answer all of the questions here before clicking submit to be paid. You cannot go back, please take your time answering these.")
    
    # Placeholder text for unselected options
    gender_placeholder = "Select your gender"
    race_ethnicity_placeholder = "Select your race/ethnicity"
    
    # Question 1: Gender
    # st.markdown("#### Q1: What is your gender?")
    st.session_state.gender = st.radio(
        "Q1: What is your gender?",
        options=[
            gender_placeholder,
            "Woman",
            "Man",
            "Non-binary",
            "Prefer not to disclose",
            "Self-described"
        ],
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
    # st.markdown("#### Q2: What is your race/ethnicity?")
    st.session_state.race_ethnicity = st.radio(
        "Q2: What is your race/ethnicity?",
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
    
    # Question 3: Age
    st.markdown("#### Q3: What is your age?")
    st.session_state.age = st.text_input(
        "",
        value=st.session_state.get('age', ''),
        key='age_input'
    )
    
    # Question 4: Job Title
    st.markdown("#### Q4: What is your job title?")
    st.session_state.job_title = st.text_input(
        "",
        value=st.session_state.get('job_title', ''),
        key='job_title_input'
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
        elif any([
                st.session_state.age.strip() == '',
                st.session_state.job_title.strip() == '',
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
                    record_data_clear_state([
                        'gender', 
                        'gender_self_described', 
                        'race_ethnicity', 
                        'race_ethnicity_other', 
                        'age',
                        'job_title',
                        'time_spent'
                    ])
                    st.session_state.page = "main_study"
                    st.rerun()
            except ValueError:
                st.error("Please enter a valid numeric age.")
            
    
def demographics():
    st.title("Demographics Questions")

    placeholder = st.empty()

    with placeholder.container():
        questions()

    