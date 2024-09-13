import streamlit as st
from streamlit_float import *
from datetime import datetime
import pages.utils.logger as logger
import gspread
import os
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from pages.utils.exponential_backoff import exponential_backoff
import time
import io

def check_user_data():
    toml_data = st.secrets # toml.load(".streamlit/secrets.toml")
    credentials_data = toml_data["connections"]["gsheets"]

    # Define the scope for the Google Sheets API
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    # Authenticate using the credentials from the TOML file
    credentials = Credentials.from_service_account_info(credentials_data, scopes=scope)
    client = gspread.authorize(credentials)
    survey_tracker = exponential_backoff(st.session_state.condition_counts_sheet.worksheet, "Survey Tracker")

    usernames = survey_tracker.col_values(1)

    if st.session_state.username in usernames:
        row_idx = usernames.index(st.session_state.username) + 1
        user_record = survey_tracker.row_values(row_idx)

        for i in range(1, len(user_record)):
            print(f'User record for index {i} is {user_record[i]}')
            if user_record[i].lower() != 'complete':
                print(f"index that is starting for survey: {i}")
                return i
        return -1
    else:
        return 1

def upload_to_drive(file, file_name):
    toml_data = st.secrets
    credentials_data = toml_data["connections"]["gsheets"]
    
    # Authenticate with Google Drive using the credentials
    credentials = service_account.Credentials.from_service_account_info(credentials_data)
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # Append the username and condition to the filename
    new_file_name = f"{st.session_state.username}_{st.session_state.condition}_{file_name}"
    
    # Create metadata for the file
    file_metadata = {
        'name': new_file_name,
        'parents': ['1qTeHaCMkaRWJ4P2Jq9qmkdDWs7BvgeuH']  # Replace with your Google Drive folder ID
    }

    # Convert the Streamlit file uploader object to a BytesIO object for the upload
    file_io = io.BytesIO(file.getvalue())

    # Create the MediaIoBaseUpload object with resumable=True for large file upload
    media = MediaIoBaseUpload(file_io, mimetype='video/webm', chunksize=1024*1024, resumable=True)

    # Initiate the upload request
    request = drive_service.files().create(body=file_metadata, media_body=media, fields='id')
    
    response = None
    progress_bar = st.progress(0)
    while response is None:
        # Track progress during upload
        status, response = request.next_chunk()
        if status:
            # Update progress bar based on the upload status
            st.session_state.upload_progress = int(status.progress() * 100)
            progress_bar.progress(st.session_state.upload_progress)

    return response['id']

def update_user_data(page_finished = "", column_idx = -1):
    toml_data = st.secrets # toml.load(".streamlit/secrets.toml")
    credentials_data = toml_data["connections"]["gsheets"]

    # Define the scope for the Google Sheets API
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    # Authenticate using the credentials from the TOML file
    credentials = Credentials.from_service_account_info(credentials_data, scopes=scope)
    client = gspread.authorize(credentials)
    user_data = exponential_backoff(st.session_state.condition_counts_sheet.worksheet, "Pilot User Data")
    survey_tracker = exponential_backoff(st.session_state.condition_counts_sheet.worksheet, "Survey Tracker")

    usernames = survey_tracker.col_values(1)

    if st.session_state.username in usernames:
        # just update the col based on what they finished
        row_idx = usernames.index(st.session_state.username) + 1
        survey_tracker.update_cell(row_idx, column_idx, page_finished)
        print(f"updated user {st.session_state.username} with finishing survey page {page_finished} in column {column_idx}")
    else:
        new_row = [st.session_state.username, 'complete', 'no', 'no', 'no', 'no']
        survey_tracker.append_row(new_row)
        print(f"created user {st.session_state.username} with finishing survey page {page_finished} in column {column_idx}")

def count_words(text):
    return len(text.split())

def record_data_clear_state(keys_list = [], survey_page = ""):
    # convert the data from dict to tuple
    responses = {}
    for key in keys_list:
        if key in st.session_state:
            responses[key] = st.session_state[key]
    
    survey_worksheet = exponential_backoff(st.session_state['sheet'].worksheet, survey_page)
    logger.write_survey_response(responses, survey_worksheet, keys_list)
    # Delete all keys in the list
    for key in keys_list:
        if key in st.session_state:
            del st.session_state[key]

def finished():
    st.title("Thank you for your time!")
    st.subheader("You will be compensated after we review your answers and footage. Click the link below to complete the study.")
    st.write("https://app.prolific.com/submissions/complete?cc=C1IZ4VLN")

def video_submission():
    st.title("Video Upload")

    # File uploader that only accepts video files
    uploaded_video = st.file_uploader("Upload a video file", type=["webm"]) # "mp4", "mov", "avi", 

    # Ensure the user uploads a video before enabling the submit button
    if uploaded_video is None:
        st.warning("Please upload a video file before proceeding.")
        st.button("Submit", disabled=True)
    else:
        try:
            st.success("Video uploaded successfully!")            
            # Display the video in the app
            st.video(uploaded_video)
            
            if st.button("Submit", key="submit_recording", disabled=st.session_state.uploading):
                 # Disable the button and show progress
                st.session_state.uploading = True

                # Progress bar
                st.session_state.upload_progress = 0

                # Call function to upload the large video to Google Drive
                video_id = upload_to_drive(uploaded_video, uploaded_video.name)
                st.success(f"Video uploaded successfully!")
                print(f"Video uploaded to Google Drive successfully! File ID: {video_id}")
                # Update session state and reset after completion
                update_user_data("complete", 6)
                st.session_state.last_progress = -1
                st.session_state.uploading = False
                st.rerun()
        except Exception as e:
            st.error(f"Error with the video save: {e}.\n Please contact for help.")
            st.session_state.uploading = False


def free_form_questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()

    st.title("Final Questions & Feedback")
    st.subheader("Note: You cannot go back, please take your time answering these.")

    # Use st.session_state.get to avoid overwriting existing text when rerunning
    st.session_state.strategy = st.text_area(
        ":red[*]What was your strategy for answering the questions?",
        value=st.session_state.get('strategy', ''), key='strategy_frq'
    )
    st.session_state.ai_model_usage = st.text_area(
        ":red[*]How did you use the AI model to help you answer the questions?",
        value=st.session_state.get('ai_model_usage', ''), key='ai_model_usage_frq'
    )
    if st.session_state.condition.find("hai-answer") == -1:
        st.session_state.error_finding = st.text_area(
            ":red[*]What did you think of the AI model's reasoning chains? Did you find them accurate and helpful? If not, what errors did you find in them?",
            value=st.session_state.get('error_finding', ''), key='error_finding_frq'
        )
    else:
        st.session_state.error_finding = None

    if st.session_state.condition.find("hai-regenerate") > -1:
        st.session_state.ai_model_interaction_usage = st.text_area(
            ":red[*]How did you interact with the AI model? Was anything confusing or demanding? If so, what was it and why?",
            value=st.session_state.get('ai_model_interaction_usage', ''), key='ai_model_interaction_usage_frq'
        )
    else:
        st.session_state.ai_model_interaction_usage = None


    st.session_state.misc_comments = st.text_area(
        "[Optional] Any other comments or remarks regarding the study?",
        value=st.session_state.get('misc_comments', ''), key='misc_comments_frq'
    )

    if st.button("Submit", key="submit_answers"):
        if any([
            st.session_state.strategy.strip() == '',
            st.session_state.error_finding is not None and st.session_state.error_finding.strip() == '',
            st.session_state.ai_model_usage.strip() == '',
            st.session_state.ai_model_interaction_usage is not None and st.session_state.ai_model_interaction_usage.strip() == '',
            # st.session_state.misc_comments is None or st.session_state.misc_comments.strip() == ''
        ]):
            st.error("Please answer all the required questions before submitting.")
        elif count_words(st.session_state.strategy) < 10:
            st.error("Please write at least 10 words for your strategy.")
        elif st.session_state.condition.find("hai-answer") == -1 and count_words(st.session_state.error_finding) < 10:
            st.error("Please write at least 10 words regarding errors.")
        elif count_words(st.session_state.ai_model_usage) < 10:
            st.error("Please write at least 10 words for how you used the AI model.")
        elif st.session_state.condition.find("hai-regenerate") > -1 and count_words(st.session_state.ai_model_interaction_usage) < 10:
            st.error("Please write at least 10 words regarding how you interacted with the model.")
        else:
            end_time = datetime.now()
            st.session_state["elapsed_time"] = str((end_time - st.session_state.time_spent).total_seconds())
            # submit data
            record_data_clear_state(['strategy', 'ai_model_usage', 'error_finding', 'ai_model_interaction_usage', 'misc_comments', 'elapsed_time'], survey_page = "Free Form Questions")
            update_user_data("complete", 5)
            # create clickable link so worker can be paid
            st.session_state.last_progress = 5
            st.rerun()

def interaction_questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()

    st.title("Interaction Reflection Questions")
    st.subheader("Note: You cannot go back, please take your time answering these.")

    options = ['Select an Option', 'Strongly Disagree', 'Disagree', 'Somewhat Disagree', 'Neutral', 'Somewhat Agree', 'Agree', 'Strongly Agree'] 
    st.subheader("Rate the following statements")
    st.markdown(
        """
        <style>
            div[role=radiogroup] label:first-of-type {
                visibility: hidden;
                height: 0px;
                width: 0px;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.session_state.answer_helpful = st.radio("I found it helpful to **read the AI model's answer** when answering the question.", options, horizontal=True, key='answer_helpful_radio')
    # condition based
    if st.session_state.condition.find("hai-answer") == -1:
        # st.write("I found the AI's highlights helpful in determining what to edit")
        st.session_state.chain_helpful = st.radio("I found it helpful to **read the AI model's reasoning chain** when answering the question (A reasoning chain is the list of thoughts, actions, and observations that help the model reason and reach its final answer).", options, horizontal=True, key='chain_helpful_radio')
    else:
        st.session_state.chain_helpful = None
    st.session_state.search_helpful = st.radio("I found **Search** helpful when answering the question.", options, horizontal=True, key='search_helpful_radio')
    st.session_state.lookup_helpful = st.radio("I found **Lookup** helpful when answering the question.", options, horizontal=True, key='lookup_helpful_radio')
    if st.session_state.condition.find("hai-regenerate") > -1:
        st.session_state.interaction_helpful = st.radio("I found it helpful to **interact with the AI model** when answering the question (Interaction includes editing AI's thought/action and updating its output).", options, horizontal=True, key='interact_helpful_radio')
        st.session_state.chain_edit_helpful = st.radio("I found it helpful to **edit the AI model's reasoning chain** when answering the question.", options, horizontal=True, key='edit_chain_helpful_radio')
        st.session_state.thought_edit_helpful = st.radio("I found it helpful to **edit the AI model's thought(s)** when answering the question.", options, horizontal=True, key='edit_thought_helpful_radio')
        st.session_state.action_edit_helpful = st.radio("I found it helpful to **edit the AI model's action(s)** when answering the question.", options, horizontal=True, key='edit_action_helpful_radio')
        st.session_state.update_output_helpful = st.radio("I found it helpful to **update the AI model's output** when answering the question.", options, horizontal=True, key='update_helpful_radio')
    else:
        st.session_state.interaction_helpful = None
        st.session_state.chain_edit_helpful = None
        st.session_state.thought_edit_helpful = None
        st.session_state.action_edit_helpful  = None
        st.session_state.update_output_helpful = None
    # st.session_state.willing_to_pay = st.radio("I would be willing to pay to access the AI’s code completions.", options, horizontal=True, key='willing_to_pay_radio')
    # st.session_state.willing_to_pay_highlights = st.radio("I would be willing to pay to access the AI’s highlights.", options, horizontal=True, key='willing_to_pay_highlights_radio')
    # st.session_state.code_completion_distracting = st.radio("I found the AI’s code completions distracting.", options, horizontal=True, key='code_completion_distracting_radio')
    # st.session_state.highlights_distracting = st.radio("I found the AI’s highlights distracting.", options, horizontal=True, key='highlights_distracting_radio')

    if st.button("Next", key="interaction_questions_next"):
        if (
            st.session_state.answer_helpful == 'Select an Option' or
            st.session_state.chain_helpful == 'Select an Option' or
            st.session_state.search_helpful == 'Select an Option' or
            st.session_state.lookup_helpful == 'Select an Option' or
            st.session_state.interaction_helpful == 'Select an Option' or
            st.session_state.chain_edit_helpful == 'Select an Option' or
            st.session_state.thought_edit_helpful == 'Select an Option' or
            st.session_state.action_edit_helpful == 'Select an Option' or
            st.session_state.update_output_helpful == 'Select an Option'
        ):
            st.error("Please make sure to select an option for all questions before submitting.")
        else:
            end_time = datetime.now()
            st.session_state["elapsed_time"] = str((end_time - st.session_state.time_spent).total_seconds())
            # log data
            record_data_clear_state(['answer_helpful', 'chain_helpful', 'search_helpful', 'lookup_helpful', 'interaction_helpful', 'chain_edit_helpful', 'thought_edit_helpful', 'action_edit_helpful', 'update_output_helpful' ,'elapsed_time'], survey_page = "Interaction Questions")
            update_user_data("complete", 4)
            st.session_state.last_progress = 4
            st.rerun()

def ai_usage_questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()
    
    st.markdown(
        """
        <style>
            div[role=radiogroup] label:first-of-type {
                visibility: hidden;
                height: 0px;
                width: 0px;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.title("AI Usage Reflection Questions")
    st.subheader("Note: You cannot go back, please take your time answering these.")
    options_frequency = ['Select an Option', 'Never', 'Rarely (10%)', 'Occasionally (30%)', 'Sometimes (50%)', 'Frequently (70%)', 'Usually (90%)', 'Always']
    # options_helpful = ['Select an Option', 'Very Unhelpful', 'Not Helpful', 'Sometimes', 'Neutral', 'Helpful', 'Very helpful']

    st.session_state.ai_frequency = st.radio("How often do you use AI models (e.g. ChatGPT, DaLLE, CoPilot)?", ['Select an Option', 'Never', 'Rarely (once a year)', 'Occasionally (once a few months)', 'Sometimes (once a month)', 'Frequently (once a week)', 'Usually (once a few days)', 'Always (at least once a day)'], horizontal=True, key='ai_frequency_radio')
    st.session_state.ai_answer_usage = st.radio("How often did you use the **AI model's answer** to help answer the question?", options_frequency, horizontal=True, key='ai_answer_usage_radio')
    # st.session_state.ai_answer_helpful = st.radio("How helpful did you find the AI model's answer chain when trying to come to an answer?", options_helpful, horizontal=True, key='ai_answer_helpful_radio')
    if st.session_state.condition.find("hai-answer") == -1:
        st.session_state.ai_reasoning_chain_usage = st.radio("How often did you use the **AI model's reasoning chain** to help answer the question?", options_frequency, horizontal=True, key='ai_reasoning_chain_usage_radio')
    else:
        st.session_state.ai_reasoning_chain_usage = None
    # st.session_state.ai_reasoning_chain_helpful = st.radio("How helpful did you find the AI model's reasoning chain when trying to come to an answer?", options_helpful, horizontal=True, key='ai_reasoning_chain_helpful_radio')
    if st.session_state.condition.find("regenerate") > -1:
        st.session_state.interaction_usage = st.radio("How often did you **interact with the AI model** to help answer the question?", options_frequency, horizontal=True, key='interaction_usage_radio')
        st.session_state.human_search = None
        st.session_state.human_lookup = None
    else:
        st.session_state.interaction_usage = None
        st.session_state.human_search = st.radio("How often did you perform a **Search** action to help answer the question?", options_frequency, horizontal=True, key='human_search_radio')
        st.session_state.human_lookup = st.radio("How often did you perform a **Lookup** action to help answer the question?", options_frequency, horizontal=True, key='human_lookup_radio')
    # st.session_state.interaction_helpfulness = st.radio("How helpful did you find the interactions with the model when trying to come to an answer?", options_helpful, horizontal=True, key='interaction_helpfulness_radio')
    # st.session_state.explanation_usage = st.radio("How often did you use the AI model's explanations to come to an answer?", options_frequency, horizontal=True, key='explanation_usage_radio')
    # st.session_state.explanation_helpfulness = st.radio("How helpful did you find the AI model's explanations when trying to come to an answer?", options_helpful, horizontal=True, key='explanation_helpfulness_radio')

    if st.button("Next", key="ai_usage_questions_next"):
        if (
            st.session_state.ai_frequency == 'Select an Option' or
            st.session_state.ai_answer_usage == 'Select an Option' or
            # st.session_state.ai_answer_helpful == 'Select an Option' or
            st.session_state.ai_reasoning_chain_usage == 'Select an Option' or
            # st.session_state.ai_reasoning_chain_helpful == 'Select an Option' or
            st.session_state.interaction_usage == 'Select an Option' or
            # st.session_state.interaction_helpfulness == 'Select an Option' or
            st.session_state.human_search == 'Select an Option' or
            st.session_state.human_lookup == 'Select an Option'
            # st.session_state.explanation_helpfulness == 'Select an Option'
        ):
            st.error("Please make sure to select an option for all questions before submitting.")
        else:
            end_time = datetime.now()
            st.session_state["elapsed_time"] = str((end_time - st.session_state.time_spent).total_seconds())
            # log data
            record_data_clear_state(['ai_frequency', 'ai_answer_usage', 'ai_reasoning_chain_usage', 'interaction_usage', 'human_search', 'human_lookup', 'elapsed_time'], survey_page = "AI Usage Questions")
            update_user_data("complete", 3)
            st.session_state.last_progress = 3
            st.rerun()

def tasks_demand_questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()    
    if 'mental_moved' not in st.session_state:
        st.session_state.mental_moved = False
    if 'success_moved' not in st.session_state:
        st.session_state.success_moved = False
    if 'effort_moved' not in st.session_state:
        st.session_state.effort_moved = False
    if 'pace_moved' not in st.session_state:
        st.session_state.pace_moved = False
    if 'stress_moved' not in st.session_state:
        st.session_state.stress_moved = False

    # Function to update slider movement state
    def check_slider_movement(slider_name, slider_value):
        if slider_value != 50:
            st.session_state[slider_name] = True
    
    st.markdown(
        """
        <style>
            div[role=radiogroup] label:first-of-type {
                visibility: hidden;
                height: 0px;
                width: 0px;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.title("Task Reflection Questions")
    st.subheader("Note: You must answer all of the questions here to be paid. You cannot go back, please take your time answering these.")
    
    st.subheader("Answer the following in terms of your general preferences (NOT related to the questions you just did)")  
    options = ['Select an Option', 'Strongly Disagree', 'Disagree', 'Somewhat Disagree', 'Neutral', 'Somewhat Agree', 'Agree', 'Strongly Agree'] 
    st.session_state.complex_to_simple = st.radio("I would prefer complex to simple problems.", options, horizontal=True, key="complex_to_simple_slider")
    st.session_state.thinking = st.radio("I like to have the responsibility of handling a situation that requires a lot of thinking.", options, horizontal=True, key="thinking_slider")
    st.session_state.thinking_fun = st.radio("Thinking is not my idea of fun.", options, horizontal=True, key="thinking_fun_slider")
    st.session_state.thought = st.radio("I would rather do something that requires little thought than something that is sure to challenge my thinking abilities.", options, horizontal=True, key="thought_slider")
    st.session_state.new_solutions = st.radio("I really enjoy a task that involves coming up with new solutions to problems.", options, horizontal=True, key="new_solutions_slider")
    st.session_state.difficulty = st.radio("I would prefer a task that is intellectual, difficult, and important to one that is somewhat important but does not require much thought.", options, horizontal=True, key="difficulty_slider")

    # Display the sliders and update movement state directly
    st.subheader("Reflect on how you feel after answering all of the questions")

    st.session_state.mental_demand = st.slider(
        "How mentally demanding were the tasks?", 0, 100, step=5, key="mental_slider", value=50)
    check_slider_movement('mental_moved', st.session_state.mental_demand)
    st.markdown('<div id="custom-slider-container"><div class="slider-text">Not at all</div><div class="slider-text">Extremely</div></div>', unsafe_allow_html=True)

    st.session_state.success = st.slider(
        "How successful were you in accomplishing what you were asked to do?", 0, 100, step=5, key='success_slider', value=50)
    check_slider_movement('success_moved', st.session_state.success)
    st.markdown('<div id="custom-slider-container"><div class="slider-text">Not at all</div><div class="slider-text">Extremely</div></div>', unsafe_allow_html=True)

    st.session_state.effort = st.slider(
        "How hard did you have to work to accomplish your level of performance?", 0, 100, step=5, key="effort_slider", value=50)
    check_slider_movement('effort_moved', st.session_state.effort)
    st.markdown('<div id="custom-slider-container"><div class="slider-text">Not at all</div><div class="slider-text">Extremely</div></div>', unsafe_allow_html=True)

    st.session_state.pace = st.slider(
        "How hurried or rushed were the pace of the tasks?", 0, 100, step=5, key="pace_slider", value=50)
    check_slider_movement('pace_moved', st.session_state.pace)
    st.markdown('<div id="custom-slider-container"><div class="slider-text">Not at all</div><div class="slider-text">Extremely</div></div>', unsafe_allow_html=True)

    st.session_state.stress = st.slider(
        "How insecure, discouraged, irritated, stressed, and annoyed were you?", 0, 100, step=5, key="stress_slider", value=50)
    check_slider_movement('stress_moved', st.session_state.stress)
    st.markdown('<div id="custom-slider-container"><div class="slider-text">Not at all</div><div class="slider-text">Extremely</div></div>', unsafe_allow_html=True)
    
    if st.button("Next", key="tasks_demand_questions_next"):
        if (
            st.session_state.complex_to_simple == 'Select an Option' or
            st.session_state.thinking == 'Select an Option' or
            st.session_state.thinking_fun == 'Select an Option' or
            st.session_state.thought == 'Select an Option' or
            st.session_state.new_solutions == 'Select an Option' or
            st.session_state.difficulty == 'Select an Option'
            ):
            st.error("Please make sure to select an option for all questions before submitting.")
        elif (any([not st.session_state.mental_moved, not st.session_state.success_moved, 
                not st.session_state.effort_moved, not st.session_state.pace_moved, 
                not st.session_state.stress_moved])):
            st.error("Please interact with the sldiers")
        else:
            end_time = datetime.now()
            st.session_state["elapsed_time"] = str((end_time - st.session_state.time_spent).total_seconds())
            # log data
            record_data_clear_state( ['complex_to_simple', 'thinking', 'thinking_fun', 'thought', 'new_solutions', 'difficulty', 'mental_demand', 'success', 'effort', 'pace', 'stress','elapsed_time'], survey_page="Task Demand Questions")
            update_user_data() # since this is the first call, we can have this be parameterless
            st.session_state.last_progress = 2
            st.rerun()

def survey():
    # st.title("Reflection Questions & Feedback")

    # Initialize the page in session state if not already set
    if 'qa_page' not in st.session_state:
        st.session_state.qa_page = 'tasks_demand'
    
    # Initialize session state for the submit button and progress bar
    if 'uploading' not in st.session_state:
        st.session_state.uploading = False
    
    if 'last_progress' not in st.session_state:
        st.session_state.last_progress = check_user_data()
        print(f'sanity check: {st.session_state.last_progress}')

    st.markdown(
        """
        <style>
        /* Increase the font size of the radio button header (only the first label) */
        div[class*="stRadio"] > label > div[data-testid="stMarkdownContainer"] > p {
            font-size: 36px !important;
        }

        /* Increase the font size of the radio button options */
        div[role='radiogroup'] label div p {
            font-size: 24px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Create a placeholder for dynamic content
    placeholder = st.empty()

    # Control which set of questions to display
    with placeholder.container():
        if st.session_state.last_progress == -1:
            finished()
        elif st.session_state.last_progress == 1:
            tasks_demand_questions()
        elif st.session_state.last_progress == 2:
            ai_usage_questions()
        elif st.session_state.last_progress == 3:
            interaction_questions()
        elif st.session_state.last_progress == 4:
            free_form_questions()
        elif st.session_state.last_progress == 5:
            video_submission()
