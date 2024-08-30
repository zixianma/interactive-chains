import streamlit as st
import requests
# from streamlit_float import *
from google.oauth2.service_account import Credentials
import toml
import random
from pages.utils.logger import *
import toml
import gspread
from google.oauth2.service_account import Credentials

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

# Function to assign a condition based on the counts
def assign_condition(condition_counts):
    # Find the condition with the minimum count
    min_count = min(condition_counts.values())
    balanced_conditions = [condition for condition, count in condition_counts.items() if count == min_count]

    # Randomly choose a condition from the balanced list
    chosen_condition = random.choice(balanced_conditions)
    condition_counts[chosen_condition] += 1

    return chosen_condition

# Retrieve condition counts from Google Sheets
def get_condition_counts(client):
    sheet = client.open("Condition Counts")
    worksheet = sheet.worksheet("Pilot")
    records = worksheet.get_all_records()

    condition_counts = {record['Condition']: record['Count'] for record in records}
    return condition_counts, worksheet

# Update condition count in Google Sheets
def update_condition_count(worksheet, condition, count):
    cell = worksheet.find(condition)
    worksheet.update_cell(cell.row, cell.col + 1, count)

# Find a user by username and IP
def find_user_row(client, location_data):
    sheet = client.open("Condition Counts")
    worksheet = sheet.worksheet("Pilot User Data")
    records = worksheet.get_all_records()
    for idx, record in enumerate(records, start=2):  # start=2 to account for header row
        if record['Username'] == st.session_state.username and record['IP'] == location_data['ip']:
            return idx, record
    return None, None

def update_pilot_user_data(client, location_data, seen=False, idx = -1):
    sheet = client.open("Condition Counts")
    worksheet = sheet.worksheet("Pilot User Data")
    if seen:
        # User exists, update their visit count and last visit time
        visits = int(worksheet.cell(idx, 3).value) + 1  # Column 3 is 'Visits'
        worksheet.update_cell(idx, 3, visits)
        visit_times = worksheet.cell(idx, 4).value  # Column 4 is 'Visit Times'

        # Convert visit_times string back to a list
        if visit_times:
            visit_times_list = visit_times.split(', ')
        else:
            visit_times_list = []

        # Append the new visit time
        visit_times_list.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        worksheet.update_cell(idx, 4, ', '.join(visit_times_list))
    else:
        # User does not exist, add a new row
        new_row = [st.session_state.username, str(location_data['ip']), 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), st.session_state.condition, str(location_data)]
        worksheet.append_row(new_row)

def submit_consent(username_input):
    if not username_input or username_input == "":
        st.warning("Please fill in a valid user name.")
    else:
        st.session_state['username_submitted'] = True
        st.session_state.username = st.session_state.username_input
        # st.session_state['username_submitted'] = True

        if 'sheet' not in st.session_state:
            toml_data = toml.load(".streamlit/secrets.toml")
            credentials_data = toml_data["connections"]["gsheets"]

            # Define the scope for the Google Sheets API
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

            # Authenticate using the credentials from the TOML file
            credentials = Credentials.from_service_account_info(credentials_data, scopes=scope)
            client = gspread.authorize(credentials)
            location_data = get_user_ip()

            # check if user exists prior, if so we re-route them to where they last were + keep same condition. otherwise update condition count + log
            row, user_record = find_user_row(client, location_data)

            if user_record:
                # need to fetch the condition they were on and set it for them
                # also need to get the question_idx
                # update visit count?
                update_pilot_user_data(client, location_data, seen=True, idx = row)
                # st.write("continuing where you left off: " + str(user_record['Condition']))
                print("continuing where you left off: " + str(user_record['Condition']))
                st.session_state.condition = user_record['Condition']
                sheet_condition = st.session_state.condition.split(' ', 1)[1]
                # now that we have condition, open the corresponding condition sheet to get last question idx
                st.session_state['sheet'] = client.open(sheet_condition)
                st.session_state['user_worksheet'] = st.session_state['sheet'].worksheet(st.session_state.username)
                num_rows = len(st.session_state['user_worksheet'].get_all_values()) - 1
                print(num_rows)
                # we can compute this by taking the # of rows and subtract by 1 to include header to figure out # of questions?
                st.session_state.last_question = num_rows
            else:
                # open sheet to get the count
                condition_counts, worksheet = get_condition_counts(client)

                # Assign a condition and update the count
                assigned_condition = "C. hai-answer" # assign_condition(condition_counts)
                update_condition_count(worksheet, assigned_condition, condition_counts[assigned_condition])

                print(f"You have been assigned to: {assigned_condition}") # debugging purposes

                st.session_state.condition = assigned_condition
                # Open the Google Sheet by name based on condition
                sheet_condition = st.session_state.condition.split(' ', 1)[1]
                # print(f"after the substring: " + str(sheet_condition))
                sheet = client.open(sheet_condition)
                st.session_state['sheet'] = sheet

                # record user in pilot user data
                update_pilot_user_data(client, location_data)
                
                st.session_state.last_question = -1

                # make sheet per user
                user_worksheet = create_user_worksheet()
            
                if 'user_worksheet' not in st.session_state:
                    st.session_state['user_worksheet'] = user_worksheet
        st.session_state.page = "instruction" #"main_study"

def login():
    # if 'username' not in st.session_state:
    #     st.session_state.username = ''

    if 'username' not in st.session_state or st.session_state.username == '': 

        if 'user_data' not in st.session_state:
            st.session_state.user_data = {
                "visits": 0,
                'last question idx done': -1,
                'location data': get_user_ip()
            }


        st.title("👋 Welcome to the study")

        st.subheader("Please carefully read below before proceeding.")
        st.write("You are invited to participate in a research study on AI-assisted question answering. You will be asked to answer multiple choice questions with the help of an AI model. You will not be recorded via audio or video.\n")
        st.write("TIME INVOLVEMENT: Your participation will take approximately 60 minutes.\n")
        st.write("PAYMENTS: You will receive \$15 via the Prolific upon completion of the study, and you will receive additional compensation of \$0.10 per correct answer afterwards, as payment for your participation. A total of up to $3 in bonuses is available.\n")
        st.write("RISKS AND BENEFITS: The risks associated with this study are minimal. A potential data breach or breach of confidentiality should not adversely affect employment or reputation. Study data will be stored securely, in compliance with University of Washington standards, minimizing the risk of confidentiality breach. You may be exposed to content that is upsetting, as this study involves a wide array of statements to validate, some of which contain harmful text (e.g., profanity, slurs, expressions of bigotry like racism/sexism/homophobia/religious intolerance, discussion of violence, jokes about tragedies). The benefits which may reasonably be expected to result from this study are none. We cannot and do not guarantee or promise that you will receive any benefits from this study.\n")
        st.write("PARTICIPANT’S RIGHTS: If you have read this form and have decided to participate in this project, please understand your participation is voluntary and you have the right to withdraw your consent or discontinue participation at any time without penalty or loss of benefits to which you are otherwise entitled. The alternative is not to participate. You have the right to refuse to answer particular questions. The results of this research study may be presented at scientific or professional meetings or published in scientific journals. Your individual privacy will be maintained in all published and written data resulting from the study.\n")
        st.write("CONTACT INFORMATION: If you have any questions, concerns or complaints about this research, its procedures, risks and benefits, contact the Protocol Director, Zixian Ma, at zixianma@uw.edu.\n")
        st.write("Independent Contact: If you are not satisfied with how this study is being conducted, or if you have any concerns, complaints, or general questions about the research or your rights as a participant, please contact the University of Washington Institutional Review Board (IRB) to speak to someone independent of the research team at 206-543-0098, or email at hsdreprt@uw.edu. You can also write to the University of Washington IRB at Human Subjects Division, University of Washington, Box 359470, 4333 Brooklyn Ave NE, Seattle, WA 98195-9470.")
        st.subheader("If you consent to participate in our study, please enter your username from Prolific to continue:")
        # Input field for the username
        username_input = st.text_input("Username", key="username_input").strip()

        if 'username_submitted' not in st.session_state:
            st.session_state['username_submitted'] = False
        # Submit button
        button = st.button("Submit", on_click=submit_consent, args=(username_input,))

        if st.session_state.page != "login" or st.session_state['username_submitted']: #'username' in st.session_state and st.session_state.username != "" and 'sheet' in st.session_state and 'user_worksheet' in st.session_state: #  and 
            st.rerun()
