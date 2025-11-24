import json
import streamlit as st
import pandas as pd
from streamlit_float import *
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from pages.utils.exponential_backoff import exponential_backoff
def flatten_actions_for_sheet(action_history):
    return [f"{action}: {text}" for action, text in action_history]

def write_to_user_sheet(data):
    sheet = st.session_state['user_worksheet']
    action_columns = []
    if st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
        for action, text in st.session_state.get("action_history", []):
            action_columns.append(f"{action}: {text}")
        final_answer_text = st.session_state.get("Answer in text", "")
        row_data = data + action_columns+ [final_answer_text]
    else:
        row_data = data

    exponential_backoff(sheet.append_row, row_data)
    
    user_data_sheet = st.session_state['sheet']
    all_actions_sheet = exponential_backoff(user_data_sheet.worksheet, 'Main Study')  
    exponential_backoff(all_actions_sheet.append_row, row_data)
    st.session_state["action_history"] = []  # Clear action history  

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
        elif st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
            header_list = ["Username", "Condition", "Question idx", "Model Answer", "Step 1", "Step 2", "Helpfulness", "Gt Answer", "Time Spent", "Question Answered", "Question ID", "Answer in text"]
        else:
             header_list = ["Username", "Condition", "Question idx", "Model Answer", "Step 1", "Step 2", "Helpfulness", "Gt Answer", "Time Spent", "Question Answered", "Question ID"]
        
        exponential_backoff(worksheet.append_row, header_list)  
    else:
        # Worksheet already exists: make sure header contains "Answer in text"
        try:
            existing_headers = exponential_backoff(worksheet.row_values, 1)
        except Exception:
            existing_headers = []

        if "Answer in text" not in existing_headers and st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
            # Append the missing header at the end of the header row
            col_to_write = len(existing_headers) + 1
            exponential_backoff(worksheet.update_cell, 1, col_to_write, "Answer in text")
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


