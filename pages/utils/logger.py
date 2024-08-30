import streamlit as st
import openai
from openai import OpenAI
import json
import os
import wikienv, wrappers
import requests
import pandas as pd
from streamlit_float import *
import re
import gspread
from google.oauth2.service_account import Credentials
import toml
from datetime import datetime
import pages.utils.logger as logger

def write_data_to_sheet(data):
    sheet = st.session_state['sheet']
    user_worksheet = st.session_state['user_worksheet']
    # write the data in the format of: user, quetion idx, step #, action, time?
    sheet.worksheet('all actions').append_row(data)
    user_worksheet.append_row(data)
    
def write_to_user_sheet(data):
    sheet = st.session_state['sheet']
    sheet.worksheet('users').append_row(data)

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
        header_list = ["user", "question idx", "total steps", "action space", "observations", "answer", "condition", "time"]
        worksheet.append_row(header_list)
    return worksheet

