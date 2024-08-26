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

def write_to_sheet(data):
        # write the data in the format of: user, quetion idx, step #, action, time?
        sheet.worksheet('actions').append_row(data)
        user_worksheet.append_row(data)
    
def write_to_user_sheet(data):
    sheet.worksheet('users').append_row(data)

def write_survey_response(data, header=False):
    if header:
        user_worksheet.append_row(["SURVEY INFORMATION", '-', '-'])
    responses = []
    for tuple in data:
         responses.append(tuple[1])
    user_worksheet.append_row(responses)

def create_user_worksheet():
    # Check if a worksheet for this user already exists
    try:
        worksheet = sheet.worksheet(st.session_state.username)
    except gspread.exceptions.WorksheetNotFound:
        # Create a new worksheet for the user if it doesn't exist
        worksheet = sheet.add_worksheet(title=st.session_state.username, rows=100, cols=20)
        worksheet.append_row(['user','question idx', 'total steps', 'action space', 'answer', 'condition', 'time'])
    
    return worksheet

if 'username' not in st.session_state:
    st.session_state.username = ''

toml_data = toml.load(".streamlit/secrets.toml")
credentials_data = toml_data["connections"]["gsheets"]

# Define the scope for the Google Sheets API
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

if st.session_state.username != '':
    # Authenticate using the credentials from the TOML file
    credentials = Credentials.from_service_account_info(credentials_data, scopes=scope)
    client = gspread.authorize(credentials)

    # Open the Google Sheet by name
    sheet = client.open('interactive chains') # TODO: should add condition here so it goes to correct Sheet

    # make sheet per user
    user_worksheet = create_user_worksheet()
