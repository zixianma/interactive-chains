import streamlit as st
import pandas as pd
from streamlit_float import *
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
    
def write_to_user_sheet(data):
    sheet = st.session_state['user_worksheet']
    sheet.append_row(data)
    user_data_sheet = st.session_state['sheet']
    user_data_sheet.worksheet('all actions').append_row(data)

def write_survey_response(data, header=False, survey_type=""):
    print(st.session_state)
    user_worksheet = st.session_state['user_worksheet']
    if header:
        user_worksheet.append_row([survey_type, '-', '-'])
    responses = []
    for tuple in data:
         responses.append(tuple[1])
    user_worksheet.append_row(responses)

def create_user_worksheet():
    sheet = st.session_state['sheet']
    # Check if a worksheet for this user already exists
    try:
        worksheet = sheet.worksheet(st.session_state.username)
    except gspread.exceptions.WorksheetNotFound:
        # Create a new worksheet for the user if it doesn't exist
        worksheet = sheet.add_worksheet(title=st.session_state.username, rows=100, cols=20)
        if st.session_state.condition.find("regenerate") > -1:
            header_list = ["user", "question idx", "Number of Generate AI output button clicks", "model output", "answer", "condition", "time", "number of questions completed"]
        else:
            header_list = ["user", "question idx", "total steps", "action space", "observations", "answer", "condition", "time", "number of questions completed"]
        worksheet.append_row(header_list)
    return worksheet

