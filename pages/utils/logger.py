import streamlit as st
import pandas as pd
from streamlit_float import *
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from pages.utils.exponential_backoff import exponential_backoff
    
def write_to_user_sheet(data):
    sheet = st.session_state['user_worksheet']
    exponential_backoff(sheet.append_row, data)
    
    user_data_sheet = st.session_state['sheet']
    all_actions_sheet = exponential_backoff(user_data_sheet.worksheet, 'Main Study')  
    exponential_backoff(all_actions_sheet.append_row, data)  

def write_survey_response(data, sheet, key_list):
    responses = []
    responses.append(st.session_state.username)
    for key in key_list:
        value = data[key]
        if value is not None:
            # print(f'response: {key} , {value}')
            responses.append(value)
    exponential_backoff(sheet.append_row, responses)

def create_user_worksheet():
    sheet = st.session_state['sheet']
    try:
        worksheet = exponential_backoff(sheet.worksheet, st.session_state.username)  
    except gspread.exceptions.WorksheetNotFound:
        # Create a new worksheet for the user if it doesn't exist
        worksheet = exponential_backoff(sheet.add_worksheet, title=st.session_state.username, rows=100, cols=20)  
        
        if st.session_state.condition.find("verifiasble") > -1:
            header_list = []  # Not implement yet
        else:
            header_list = ["Username", "Condition", "Question idx", "Model Answer", "Step 1", "Step 2", "Helpfulness" "Gt Answer", "Time Spent", "Question Answered", "Question ID"]
        
        exponential_backoff(worksheet.append_row, header_list)  
    
    return worksheet


def ensure_demo_worksheet():
    sheet = st.session_state['sheet']
    try:
        # Try to get the "Demographics" worksheet
        demographics_sheet = exponential_backoff(sheet.worksheet, "Demographics")  
    except gspread.exceptions.WorksheetNotFound:
        # If it doesn't exist, create it
        demographics_sheet = exponential_backoff(sheet.add_worksheet, title="Demographics", rows=100, cols=20)  
        # Add a header row for the demographics sheet
        exponential_backoff(demographics_sheet.append_row, ["Username", "Gender", "Self-Described Gender", "Race/Ethnicity", "Other Race/Ethnicity", "Age", "Job Title"])  
    
    return demographics_sheet
        

def write_demo_response(data):
    print(st.session_state)
    demo_worksheet = st.session_state['demographics']
    
    responses = [tuple[1] for tuple in data]
    exponential_backoff(demo_worksheet.append_row, responses)
    

def ensure_eval_worksheet():
    sheet = st.session_state['sheet']
    try:
        # Try to get the "Evaluation" worksheet
        eval_sheet = exponential_backoff(sheet.worksheet, "Evaluation")
    except gspread.exceptions.WorksheetNotFound:
        # Create the eval sheet if not found
        eval_sheet = exponential_backoff(sheet.add_worksheet, title="Evaluation", rows=100, cols=20)
        # Add a header row for the eval sheet
        exponential_backoff(eval_sheet.append_row, ["Username", "Condition", "Question idx", "Question Answered", "Choices", "Chosen Answer", "gt Answer", "IsCorrect", "Time"])
    
    return eval_sheet


def write_eval_response(data):
    print(st.session_state)
    eval_worksheet = st.session_state['evaluation']
    
    # responses = [tuple[1] for tuple in data]
    exponential_backoff(eval_worksheet.append_row, data)


