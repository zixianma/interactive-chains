from streamlit_float import *
import streamlit as st
from datetime import datetime
import pages.utils.logger as logger
import gspread
import os
from google.oauth2.service_account import Credentials
from pages.utils.exponential_backoff import exponential_backoff

def check_user_data():
    # Open the "Demo Tracker" worksheet
    demo_tracker = exponential_backoff(st.session_state.condition_counts_sheet.worksheet, "Demo Tracker")

    # Get all usernames in the first column of "Demo Tracker"
    usernames = demo_tracker.col_values(1)

    # Check if the current user's username exists in the tracker
    if st.session_state.username in usernames:
        row_idx = usernames.index(st.session_state.username) + 1
        user_record = demo_tracker.row_values(row_idx)

        # Check if the user has already completed the demographics page (assuming column 2 for demo)
        if user_record[1].lower() == 'complete':
            print(f"User {st.session_state.username} has already completed the demographics page.")
            return -1  # Return -1 to indicate completion
        else:
            print(f"User {st.session_state.username} has not completed the demographics page.")
            return 1  # Return 1 to indicate they need to complete the page
    else:
        print(f"User {st.session_state.username} not found in the demo tracker.")
        return 1  # New user, needs to complete the page


def update_user_data():
    # Open the "Demo Tracker" worksheet
    demo_tracker = exponential_backoff(st.session_state.condition_counts_sheet.worksheet, "Demo Tracker")

    # Get all usernames in the first column of "Demo Tracker"
    usernames = demo_tracker.col_values(1)

    # Check if the current user's username exists in the tracker
    if st.session_state.username in usernames:
        # Update the "complete" status for the demographics page (assuming column 2 for demo)
        row_idx = usernames.index(st.session_state.username) + 1
        demo_tracker.update_cell(row_idx, 2, 'complete')
        print(f"Updated user {st.session_state.username} with completing demographics in column 2")
    else:
        # Create a new row for the user if not found and mark the demographics page as complete
        new_row = [st.session_state.username, 'complete']
        demo_tracker.append_row(new_row)
        print(f"Created new entry for user {st.session_state.username} and marked demographics as complete.")


def record_data_clear_state(keys_list = []):
    # convert the data from dict to tuple
    responses_dict = []
    user_name = st.session_state.username
    responses_dict.append(('username', user_name))
    keys = keys_list
    for key in keys:
        if key in st.session_state:
            # will change this later, doing as sanity checker for now
            responses_dict.append((key, st.session_state[key]))
    logger.write_demo_response(responses_dict)
    # Delete all keys in the list
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]

def questions():
        
    # st.subheader("Note: You must answer all of the questions here before clicking submit to be paid. You cannot go back, please take your time answering these.")
    
    # Placeholder text for unselected options
    gender_placeholder = "Select your gender"
    race_ethnicity_placeholder = "Select your race/ethnicity"
    
    
    st.markdown(
        """
        <style>
            div[role=radiogroup] label:first-of-type {
                visibility: hidden;
                height: 0px;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )
    
    # Question 1: Gender
    st.markdown("#### Q1: What is your gender?")
    st.session_state.gender = st.radio(
        "gender",
        options=[
            gender_placeholder,
            "Woman",
            "Man",
            "Non-binary",
            "Prefer not to disclose",
            "Self-described"
        ],
        key='gender_radio',
        label_visibility="collapsed"
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
        "race/ethnicity",
        options=[
            race_ethnicity_placeholder,
            "American Indian or Alaska Native",
            "Asian",
            "Black or African American",
            "Hispanic or Latino",
            "Native Hawaiian or Other Pacific Islander",
            "White",
            "Prefer not to say",
            "Mixed-race",
            "Other"
        ],
        key='race_ethnicity_radio',
        label_visibility="collapsed"
    )
    
    if st.session_state.race_ethnicity == "Other" or st.session_state.race_ethnicity == "Mixed-race":
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
        "Age",
        value=st.session_state.get('age', ''),
        key='age_input',
        label_visibility="collapsed"
    )
    
    # Question 4: Job Title
    st.markdown("#### Q4: What is your job title?")
    st.session_state.job_title = st.text_input(
        "job title",
        value=st.session_state.get('job_title', ''),
        key='job_title_input',
        label_visibility="collapsed"
    )
    
    if st.button("Submit", key="submit_mcq"):
        # Check if the "Self-described" or "Other" field is filled if selected
        if st.session_state.gender == gender_placeholder:
            st.error("Please select your gender.")
        elif st.session_state.gender == "Self-described" and st.session_state.gender_self_described.strip() == '':
            st.error("Please describe your gender in the 'Self-described' field.")
        elif st.session_state.race_ethnicity == race_ethnicity_placeholder:
            st.error("Please select your race/ethnicity.")
        elif (st.session_state.race_ethnicity == "Other" or st.session_state.race_ethnicity == "Mixed-race") and st.session_state.race_ethnicity_other.strip() == '':
            st.error("Please specify your race/ethnicity in the 'Other/Mixed-race' field.")
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
                    record_data_clear_state([
                        'gender', 
                        'gender_self_described', 
                        'race_ethnicity', 
                        'race_ethnicity_other', 
                        'age',
                        'job_title',
                    ])
                    update_user_data()
                    st.session_state.page = "instruction"
                    st.rerun()
            except ValueError:
                st.error("Please enter a valid numeric age.")
            
    
def demographics():
    st.title("Demographics Questions")

    placeholder = st.empty()
    
    if 'demo_progress' not in st.session_state:
        st.session_state.demo_progress = check_user_data()
        print(f'sanity check: {st.session_state.demo_progress}')

    with placeholder.container():
        if st.session_state.demo_progress == -1:
            st.session_state.page = "instruction"
            st.rerun()
        elif st.session_state.demo_progress == 1:
            questions()

    