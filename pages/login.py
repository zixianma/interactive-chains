import streamlit as st
import requests
from streamlit_float import *
from google.oauth2.service_account import Credentials
import toml
import random
from pages.utils.exponential_backoff import exponential_backoff
from pages.utils.logger import *
import toml
import gspread
from google.oauth2.service_account import Credentials

# def get_user_ip():
#     try:
#         ip = requests.get('https://api64.ipify.org?format=json').json()["ip"]
#         response = requests.get(f'https://ipinfo.io/{ip}/json')
#         data = response.json()
#         location = {
#             'ip': data.get('ip'),
#             'city': data.get('city'),
#             'region': data.get('region'),
#             'country': data.get('country'),
#             'loc': data.get('loc'),  # Latitude and Longitude
#             'org': data.get('org'),
#             'timezone': data.get('timezone')
#         }
#         return location
#     except Exception as e:
#         return {"error": str(e)}

def assign_condition(condition_counts, weights=None):
    """
    condition_counts: Dictionary of condition counts.
    weights: Optional dictionary of weights for each condition, where the keys are condition names and values are the corresponding weights.
             If no weights are provided, default to 1 for all conditions.
    """
    # Default weights to 1 for all conditions if not provided
    if weights is None:
        weights = {condition: 1 for condition in condition_counts.keys()}
    
    # Create a list of conditions and their respective weights
    conditions = list(condition_counts.keys())
    condition_weights = [weights.get(condition, 1) for condition in conditions]
    
    # Choose a condition based on the weights
    chosen_condition = random.choices(conditions, weights=condition_weights, k=1)[0]
    
    # Increment the count of the chosen condition
    condition_counts[chosen_condition] += 1

    return chosen_condition

# Retrieve condition counts from Google Sheets
def get_condition_counts(pilot_worksheet):
    records = exponential_backoff(pilot_worksheet.get_all_records)
    condition_counts = {record['Condition']: record['Count'] for record in records}
    return condition_counts

# Update condition count in Google Sheets
def update_condition_count(worksheet, condition, count):
    cell = exponential_backoff(worksheet.find, condition)
    exponential_backoff(worksheet.update_cell, cell.row, cell.col + 1, count)

# Find a user by username and IP
def find_user_row(condition_counts_sheet):
    pilot_user_data_sheet = exponential_backoff(condition_counts_sheet.worksheet, "Pilot User Data")
    usernames = exponential_backoff(pilot_user_data_sheet.get, 'A2:A301')

    print(f'usernames: {usernames}')

    if not usernames or all(len(record) == 0 for record in usernames):
        print(f'empty usernames list')
        # Handle the case when the list is empty
        return None, None

    for idx, record in enumerate(usernames, start=2):  # start=2 to account for header row
        print(f'record: {record}')
        if record[0] == st.session_state.username:
            # if the username exists, then we can fetch the row
            print(f'record found for {idx}')
            user_condition = exponential_backoff(pilot_user_data_sheet.get, f'D{idx}')
            return idx, user_condition[0][0]
    return None, None

def update_pilot_user_data(pilot_user_data_sheet, seen=False, idx = -1):
    if seen:
        # User exists, update their visit count and last visit time
        visits = int(exponential_backoff(pilot_user_data_sheet.cell, idx, 2).value) + 1
        visit_times = exponential_backoff(pilot_user_data_sheet.cell, idx, 3).value

        cell_range = f'B{idx}:C{idx}'
        # Convert visit_times string back to a list
        if visit_times:
            visit_times_list = visit_times.split(', ')
        else:
            visit_times_list = []

        # Append the new visit time
        visit_times_list.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # Batch update the visit time and visits count for this user
        values = [[visits,', '.join(visit_times_list)]]
        updates = {
            'range': cell_range,
            'values': values
        }
        exponential_backoff(pilot_user_data_sheet.update, cell_range, values)
    else:
        # User does not exist, add a new row
        new_row = [st.session_state.username, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), st.session_state.condition]
        exponential_backoff(pilot_user_data_sheet.append_row, new_row)

def submit_consent(username_input):
    if not username_input or username_input == "":
        st.warning("Please fill in a valid user name.")
    else:
        st.session_state['username_submitted'] = True
        st.session_state.username = st.session_state.username_input

        if 'status' not in st.session_state:
            if len(st.session_state.username) < 15:
                st.session_state.status = "test"
            else:
                st.session_state.status = "prod"

        print(f'test status: {st.session_state.status}')

        if 'sheet' not in st.session_state:
            toml_data = st.secrets # toml.load(".streamlit/secrets.toml")
            credentials_data = toml_data["connections"]["gsheets"]

            # Define the scope for the Google Sheets API
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

            # Authenticate using the credentials from the TOML file
            credentials = Credentials.from_service_account_info(credentials_data, scopes=scope)
            client = gspread.authorize(credentials)

            st.session_state.condition_counts_sheet = condition_counts_sheet = exponential_backoff(client.open, f"Condition Counts {st.session_state.status}")  
            row, user_condition = find_user_row(condition_counts_sheet)

            if user_condition:
                pilot_user_data_sheet = exponential_backoff(condition_counts_sheet.worksheet, "Pilot User Data")  
                update_pilot_user_data(pilot_user_data_sheet, seen=True, idx=row)
                print("continuing where you left off: " + str(user_condition))
                st.session_state.condition = str(user_condition)
                sheet_condition = st.session_state.condition.split(' ', 1)[1] + ' ' + st.session_state.status
                print(f'sheet condition {sheet_condition}')
                st.session_state['sheet'] = exponential_backoff(client.open, sheet_condition)  
                st.session_state['user_worksheet'] = exponential_backoff(st.session_state['sheet'].worksheet, st.session_state.username)
                st.session_state['demographics'] = exponential_backoff(st.session_state['sheet'].worksheet, 'Demographics')
                all_values = exponential_backoff(st.session_state['user_worksheet'].get, 'H2:H37')
                print(f'all values: {all_values}, len: {len(all_values)}')
                if not all_values or (len(all_values) == 1 and not all_values[0]):
                    st.session_state.questions_done = -1
                    st.session_state.page =   "demographics" # begin_tutorial or instruction?
                elif len(all_values) >= 36:
                    st.session_state.questions_done = 36
                    st.session_state.page =   "end_tutorial"
                else:
                    last_question_answered = all_values[-1]
                    print(f'last_question_answered: {last_question_answered}')
                    st.session_state.questions_done = int(last_question_answered[0])
                    st.session_state.page =   "begin_tutorial" # begin_tutorial or instruction?
                print(f'st.session_state.questions_done: {st.session_state.questions_done}')
            else:
                pilot_worksheet = exponential_backoff(condition_counts_sheet.worksheet, "Pilot")
                condition_counts = get_condition_counts(pilot_worksheet)
                # this is to make static chain 2x as likely
                weights = {
                    'D. hai-static-chain': 0,
                    'C. hai-answer': 0,
                    'I. hai-regenerate': 1,
                }
                assigned_condition = assign_condition(condition_counts, weights)
                update_condition_count(pilot_worksheet, assigned_condition, condition_counts[assigned_condition])
                print(f"You have been assigned to: {assigned_condition}")
                st.session_state.condition = assigned_condition
                sheet_condition = st.session_state.condition.split(' ', 1)[1] + ' ' + st.session_state.status
                st.session_state['sheet'] = exponential_backoff(client.open, sheet_condition)
                pilot_user_data_sheet = exponential_backoff(condition_counts_sheet.worksheet, "Pilot User Data")
                update_pilot_user_data(pilot_user_data_sheet)
                st.session_state.questions_done = -1

                # make sheet per user
                user_worksheet = create_user_worksheet()
                demo_worksheet = ensure_demo_worksheet()
            
                if 'user_worksheet' not in st.session_state:
                    st.session_state['user_worksheet'] = user_worksheet
                
                if 'demographics' not in st.session_state:
                    st.session_state['demographics'] = demo_worksheet
                
                st.session_state.page =   "demographics"

        # st.session_state.page =   "main_study" # "end_tutorial" #"instruction" "main_study" "survey" # "demographics" #

def login():
    # if 'username' not in st.session_state:
    #     st.session_state.username = ''

    if 'username' not in st.session_state or st.session_state.username == '': 

        if 'user_data' not in st.session_state:
            st.session_state.user_data = {
                "visits": 0,
                'last question idx done': -1
            }


        st.title("👋 Welcome to the study")

        st.subheader("Please carefully read below before proceeding.")
        st.write("You are invited to participate in a research study on AI-assisted question answering. You will be asked to verify claims and answer multiple choice questions with the help of an AI model.\n")
        st.markdown("**You will be asked to record your screen.**")
        st.write("TIME INVOLVEMENT: Your participation will take approximately 40 minutes.\n")
        st.write("PAYMENTS: You will receive \$10 via Prolific upon completion of the study, and you will receive additional compensation of \$0.10 per correct answer afterwards, as payment for your participation. A total of up to $3 in bonuses is available.\n")
        st.write("RISKS AND BENEFITS: The risks associated with this study are minimal. A potential data breach or breach of confidentiality should not adversely affect employment or reputation. Study data will be stored securely, in compliance with University of Washington standards, minimizing the risk of confidentiality breach. The benefits which may reasonably be expected to result from this study are none. We cannot and do not guarantee or promise that you will receive any benefits from this study.\n")
        st.write("PARTICIPANT’S RIGHTS: If you have read this form and have decided to participate in this project, please understand your participation is voluntary and you have the right to withdraw your consent or discontinue participation at any time without penalty or loss of benefits to which you are otherwise entitled. The alternative is not to participate. You have the right to refuse to answer particular questions. The results of this research study may be presented at scientific or professional meetings or published in scientific journals. Your individual privacy will be maintained in all published and written data resulting from the study.\n")
        st.write("CONTACT INFORMATION: If you have any questions, concerns or complaints about this research, its procedures, risks and benefits, contact the Protocol Director, Zixian Ma, at zixianma@uw.edu.\n")
        st.write("Independent Contact: If you are not satisfied with how this study is being conducted, or if you have any concerns, complaints, or general questions about the research or your rights as a participant, please contact the University of Washington Institutional Review Board (IRB) to speak to someone independent of the research team at 206-543-0098, or email at hsdreprt@uw.edu. You can also write to the University of Washington IRB at Human Subjects Division, University of Washington, Box 359470, 4333 Brooklyn Ave NE, Seattle, WA 98195-9470.")
        st.subheader("If you consent to participate in our study, please enter your Prolific ID to continue:")
        # Input field for the username
        username_input = st.text_input("Prolific ID", key="username_input").strip()

        if 'username_submitted' not in st.session_state:
            st.session_state['username_submitted'] = False
        # Submit button
        button = st.button("Submit", on_click=submit_consent, args=(username_input,))

        if st.session_state.page != "login" or st.session_state['username_submitted']: #'username' in st.session_state and st.session_state.username != "" and 'sheet' in st.session_state and 'user_worksheet' in st.session_state: #  and 
            st.rerun()
