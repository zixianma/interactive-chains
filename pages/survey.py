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
from pages.utils.utils import show_transition

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
        'parents': ['1KvxSd68eBlUnybl4jtoTiTMsrFpUlSoWh1VBBtSA6J4tPCWE2ZL3rVG7_12qSkrpVtVqPo2N']
    }

    # Convert the Streamlit file uploader object to a BytesIO object for the upload
    file_io = io.BytesIO(file.getvalue())

    # Use a larger chunk size for large file uploads (10MB? may swap to 5MB if suffering performance issues)
    chunk_size = 10 * 1024 * 1024  # 10 MB

    # Create the MediaIoBaseUpload object with resumable=True for large file upload
    media = MediaIoBaseUpload(file_io, mimetype='video/webm', chunksize=chunk_size, resumable=True)

    # Initiate the upload request
    request = drive_service.files().create(body=file_metadata, media_body=media, fields='id')

    # Initialize response and progress tracking
    response = None
    progress_bar = st.progress(0)
    retries = 5  # Number of retry attempts
    retry_delay = 5  # Retry delay in seconds

    while response is None:
        try:
            # Track progress during upload
            status, response = request.next_chunk()
            if status:
                # Update progress bar based on the upload status
                st.session_state.upload_progress = int(status.progress() * 100)
                progress_bar.progress(st.session_state.upload_progress)

        except (ConnectionError, TimeoutError, Exception) as e:
            # Retry logic in case of failure
            retries -= 1
            if retries <= 0:
                raise Exception(f"Upload failed after multiple retries: {e}. Please contact the Protocol Director, Zixian Ma, at zixianma@uw.edu")
            print(f"Upload failed for {st.session_state.username}, retrying in {retry_delay} seconds... ({retries} retries left)")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff like implementation

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
    # Check if the page has already been submitted
    submission_key = f"submitted_{survey_page}"
    
    if submission_key in st.session_state and st.session_state[submission_key]:
        st.info(f"You have already submitted the {survey_page} page.")
        return  # Exit if the page has already been submitted
    
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

    st.session_state[submission_key] = True

def finished():
    st.title("Thank you for your time!")
    st.subheader("You will be compensated after we review your answers and footage. Click the link below to complete the study.")
    st.write("https://app.prolific.com/submissions/complete?cc=C1IZ4VLN")

def video_submission():
    st.title("Video Upload")
#https://docs.google.com/forms/d/e/1FAIpQLSdDALOwdvSMo6JqMDpv1OXeoel_bDPD_8u1XLPJTjz6kHO-BQ/viewform?usp=header
    st.markdown("Please submit your video through this [Google form](https://docs.google.com/forms/d/e/1FAIpQLSdDALOwdvSMo6JqMDpv1OXeoel_bDPD_8u1XLPJTjz6kHO-BQ/viewform?usp=header).\n") 

    st.write("After submitting the form, at the end there will be a password for you to enter below to complete the study.")

    # Create a password input field
    password = st.text_input("Enter password", type="password", key="password_video")

    # Button to check the password
    if st.button("Submit"):
        trimmed_password = password.strip()
        if trimmed_password == st.secrets["video_password"]['password']:
            update_user_data("complete", 6)
            st.session_state.last_progress = -1
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")

    # # Initialize session state for tracking submission and upload progress
    # if "uploading" not in st.session_state:
    #     st.session_state.uploading = False

    # if "video_submitted" not in st.session_state:
    #     st.session_state.video_submitted = False  # Tracks if the video was already submitted

    # # File uploader that only accepts video files
    # uploaded_video = st.file_uploader("Upload a video file", type=["webm"])  # You can add other file types if needed

    # # Ensure the user uploads a video before enabling the submit button
    # if uploaded_video is None:
    #     st.warning("Please upload a video file before proceeding.")
    #     st.button("Submit", disabled=True)
    # else:
    #     try:
    #         st.success("Video uploaded successfully!")
    #         # Display the video in the app
    #         st.video(uploaded_video)

    #         st.markdown("Alternatively, if you're experiencing issues uploading your video, you can submit it through this [Google form](https://docs.google.com/forms/d/e/1FAIpQLSfDRHCootB91wKYUUvq5_qKmzk6lpYg0aS_adslML9dWkCCTQ/viewform).")

    #         # Disable the submit button if the video has already been submitted
    #         if st.button("Submit", key="submit_recording", disabled=st.session_state.uploading or st.session_state.video_submitted):
    #             # Immediately disable the button to prevent spamming
    #             st.session_state.uploading = True

    #             # Progress bar
    #             st.session_state.upload_progress = 0

    #             # Call function to upload the large video to Google Drive
    #             video_id = upload_to_drive(uploaded_video, uploaded_video.name)
    #             st.success(f"Video uploaded successfully!")
    #             print(f'video uploaded succesfully!  File ID: {video_id} for user: {st.session_state.username}')

    #             # Update session state after submission to prevent future submissions
    #             st.session_state.video_submitted = True
    #             st.session_state.uploading = False

    #             # Update user data and reset after completion
    #             update_user_data("complete", 6)
    #             st.session_state.last_progress = -1
    #             st.rerun()  # Refresh the page to reflect changes
    #     except Exception as e:
    #         st.error(f"Error with the video save: {e}.\n Please contact for help.")
    #         st.session_state.uploading = False

def free_form_questions():
    survey_page = "Free Form Questions"
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()
    if f"submit_disabled_{survey_page}" not in st.session_state:
        st.session_state[f"submit_disabled_{survey_page}"] = False
    if 'submitted_once' not in st.session_state:
        st.session_state.submitted_once = False

    if st.session_state[f"submit_disabled_{survey_page}"]:
        update_user_data("complete", 5)
        st.session_state.last_progress = 5
        st.rerun()

    st.title("Final Questions & Feedback")
    st.subheader("Note: You cannot go back, please take your time answering these.")

    # Preserve input across reruns
    st.session_state.strategy = st.text_area(
        ":red[*]How did you evaluate whether the AI model's answer was correct?",
        value=st.session_state.get('strategy', ''), key='strategy_frq'
    )
    
    st.session_state.ai_model_usage = st.text_area(
        ":red[*]In what ways did you use the AI's information to make your decision?",
        value=st.session_state.get('ai_model_usage', ''), key='ai_model_usage_frq'
    )
    
    st.session_state.ai_info_usage = st.text_area(
        ":red[*]What did you think about the information the AI model provided? Was it helpful in guiding your decision? Please explain why you think it is helpful or not.", 
        value=st.session_state.get('ai_info_usage', ''), key='ai_info_usage_frq'
    )

    st.session_state.misc_comments = st.text_area(
        "Optional: Do you have any additional comments or feedback about the study?",
        value=st.session_state.get('misc_comments', ''), key='misc_comments_frq'
    )
    
    # Perform validation and submission
    if st.button("Submit", key="submit_answers", disabled=st.session_state.get(f"submit_disabled_{survey_page}", False)):
        # Immediately disable the submit button.
        st.session_state[f"submit_disabled_{survey_page}"] = True

        # Validation: Check if any of the required fields are empty.
        if any([
            st.session_state.strategy.strip() == '',
            st.session_state.ai_model_usage.strip() == '',
            st.session_state.ai_info_usage.strip() == '',
        ]):
            st.error("Please answer all the required questions before submitting.")
            st.session_state[f"submit_disabled_{survey_page}"] = False  # Re-enable the button on error.
        elif count_words(st.session_state.strategy) < 10:
            st.error("Please write at least 10 words for your strategy.")
            st.session_state[f"submit_disabled_{survey_page}"] = False
        elif count_words(st.session_state.ai_model_usage) < 10:
            st.error("Please write at least 10 words describing how you used the AI model.")
            st.session_state[f"submit_disabled_{survey_page}"] = False
        elif count_words(st.session_state.ai_info_usage) < 10:
            st.error("Please write at least 10 words describing your thoughts on the AI model's provided information.")
            st.session_state[f"submit_disabled_{survey_page}"] = False
        else:
            # Mark that the submission has occurred to prevent multiple submissions.
            st.session_state.submitted_once = True
            
            # Calculate elapsed time.
            end_time = datetime.now()
            st.session_state["elapsed_time"] = str((end_time - st.session_state.time_spent).total_seconds())
            
            # Submit the data and clear state for selected fields.
            record_data_clear_state(
                ['strategy', 'ai_model_usage', 'ai_info_usage', 'misc_comments', 'elapsed_time'],
                survey_page=survey_page
            )        


def interaction_questions():
    survey_page = "Interaction Questions"
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()
    if f"submit_disabled_{survey_page}" not in st.session_state:
        st.session_state[f"submit_disabled_{survey_page}"] = False

    st.title("Interaction Reflection Questions")
    st.subheader("Note: You cannot go back, please take your time answering these.")

    st.markdown(
        """
        <style>
            div[role='radiogroup'] label:first-of-type {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    confidence_scale = [
        "Select an Option",
        "1 - Very un-confident",
        "2 - Slightly confident",
        "3 - Somewhat confident",
        "4 - Confident",
        "5 - Very confident"
    ]

    accuracy_scale = [
        "Select an Option",
        "1 - 0-20% accurate",
        "2 - 20-40% accurate",
        "3 - 40-60% accurate",
        "4 - 60-80% accurate",
        "5 - 80-100% accurate"
    ]

    helpfulness_scale = [
        "Select an Option",
        "1 - Not at all helpful",
        "2 - Slightly helpful",
        "3 - Somewhat helpful",
        "4 - Helpful",
        "5 - Very helpful"
    ]
    
    def ask_question(label, key, scale):
        st.markdown(f"### {label}")
        return st.radio("", scale, index=0, horizontal=False, key=key)
    
    st.session_state.confidence = ask_question("How confident were you about completing the tasks?", "confidence_radio", confidence_scale)
    st.session_state.self_accuracy = ask_question("How accurate do you think your answers were?", "self_accuracy_radio", accuracy_scale)
    st.session_state.ai_accuracy = ask_question("How accurate do you think the AI model's answers were?", "ai_accuracy_radio", accuracy_scale)
    st.session_state.ai_helpfulness = ask_question("How helpful do you think the AI model's outputs were?", "ai_helpfulness_radio", helpfulness_scale)
    
    if st.button("Next", key="interaction_questions_next", disabled=st.session_state[f"submit_disabled_{survey_page}"]):
        if any([
            st.session_state.confidence == 'Select an Option',
            st.session_state.self_accuracy == 'Select an Option',
            st.session_state.ai_accuracy == 'Select an Option',
            st.session_state.ai_helpfulness == 'Select an Option'
        ]):
            st.error("Please make sure to select an option for all questions before submitting.")
        else:
            end_time = datetime.now()
            st.session_state[f"submit_disabled_{survey_page}"] = True
            st.session_state["elapsed_time"] = str((end_time - st.session_state.time_spent).total_seconds())
            
            record_data_clear_state([
                'confidence', 'self_accuracy', 'ai_accuracy', 'ai_helpfulness', 'elapsed_time'
            ], survey_page=survey_page)
            
            update_user_data("complete", 4)
            st.session_state.last_progress = 4
            st.rerun()


def ai_usage_questions():
    survey_page = "AI Usage Questions"
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()
    if f"submit_disabled_{survey_page}" not in st.session_state:
        st.session_state[f"submit_disabled_{survey_page}"] = False

    st.title("AI Usage Reflection Questions")
    st.subheader("Note: You cannot go back, please take your time answering these.")

    st.markdown(
        """
        <style>
            div[role='radiogroup'] label:first-of-type {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    frequency_options = [
        'Select an Option',
        'Never',
        'Rarely (once a year)',
        'Occasionally (once every few months)',
        'Sometimes (once a month)',
        'Frequently (once a week)',
        'Usually (once every few days)',
        'Always (at least once a day)'
    ]

    st.markdown("### 1. How often do you use AI models (e.g. ChatGPT, Claude, Gemini)?")
    st.radio(
        label="",
        options=frequency_options,
        index=0,
        horizontal=False,
        key='ai_frequency'
    )

    st.markdown("### 2. Which AI models have you used before? *(e.g., ChatGPT, Claude, Gemini, etc.)*")
    st.text_area("Your answer:", key='ai_models_used')

    st.markdown("### 3. How accurate do you think AI models are in general?")
    st.text_area("Your answer:", key='ai_accuracy_opinion')

    if st.button("Next", key="ai_usage_questions_next", disabled=st.session_state[f"submit_disabled_{survey_page}"]):
        if (
            st.session_state.ai_frequency == 'Select an Option' or
            not st.session_state.ai_models_used.strip() or
            not st.session_state.ai_accuracy_opinion.strip()
        ):
            st.error("Please make sure to answer all questions before continuing.")
        else:
            end_time = datetime.now()
            st.session_state[f"submit_disabled_{survey_page}"] = True
            st.session_state["elapsed_time"] = str((end_time - st.session_state.time_spent).total_seconds())
            record_data_clear_state([
                'ai_frequency', 
                'ai_models_used', 
                'ai_accuracy_opinion', 
                'elapsed_time'
            ], survey_page=survey_page)
            update_user_data("complete", 2)
            st.session_state.last_progress = 2
            st.rerun()


def tasks_demand_questions():
    survey_page = "Task Demand Questions"
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()    
    for slider_key in ['mental_moved', 'success_moved', 'effort_moved', 'pace_moved', 'stress_moved']:
        if slider_key not in st.session_state:
            st.session_state[slider_key] = False
    if f"submit_disabled_{survey_page}" not in st.session_state:
        st.session_state[f"submit_disabled_{survey_page}"] = False

    def check_slider_movement(slider_name, slider_value):
        if slider_value != 50:
            st.session_state[slider_name] = True

    st.title("🧠 Task Reflection Questions")
    st.subheader("Note: You must answer all of the questions here to be paid. You cannot go back, so please take your time.")

    st.markdown(
        """
        <style>
            div[role='radiogroup'] label:first-of-type {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Answer the following in terms of your general preferences (NOT related to the tasks you just did):")
    likert_options = ['Select an Option', 'Strongly Disagree', 'Disagree', 'Somewhat Disagree', 'Neutral', 'Somewhat Agree', 'Agree', 'Strongly Agree']

    def large_question(label, key):
        st.markdown(f"### {label}")
        return st.radio("", likert_options, index=0, horizontal=False, key=key)

    st.session_state.complex_to_simple = large_question("I would prefer complex to simple problems.", "complex_to_simple_slider")
    st.session_state.thinking = large_question("I like to have the responsibility of handling a situation that requires a lot of thinking.", "thinking_slider")
    st.session_state.thinking_fun = large_question("Thinking is not my idea of fun.", "thinking_fun_slider")
    st.session_state.thought = large_question("I would rather do something that requires little thought than something that is sure to challenge my thinking abilities.", "thought_slider")
    st.session_state.new_solutions = large_question("I really enjoy a task that involves coming up with new solutions to problems.", "new_solutions_slider")
    st.session_state.difficulty = large_question("I would prefer a task that is intellectual, difficult, and important to one that is somewhat important but does not require much thought.", "difficulty_slider")

    st.subheader("Now reflect on how you feel after answering all the questions:")

    def slider_with_label(label, key_name):
        st.markdown(f"### {label}")
        value = st.slider("", 0, 100, step=5, key=key_name, value=50)
        check_slider_movement(f"{key_name.split('_')[0]}_moved", value)
        st.markdown('<div id="custom-slider-container"><div class="slider-text">Not at all</div><div class="slider-text">Extremely</div></div>', unsafe_allow_html=True)

    slider_with_label("How mentally demanding were the tasks?", "mental_slider")
    slider_with_label("How successful were you in accomplishing what you were asked to do?", "success_slider")
    slider_with_label("How hard did you have to work to accomplish your level of performance?", "effort_slider")
    slider_with_label("How hurried or rushed was the pace of the tasks?", "pace_slider")
    slider_with_label("How insecure, discouraged, irritated, stressed, and annoyed were you?", "stress_slider")

    if st.button("Next", key="tasks_demand_questions_next", disabled=st.session_state[f"submit_disabled_{survey_page}"]):
        if any([
            st.session_state.complex_to_simple == 'Select an Option',
            st.session_state.thinking == 'Select an Option',
            st.session_state.thinking_fun == 'Select an Option',
            st.session_state.thought == 'Select an Option',
            st.session_state.new_solutions == 'Select an Option',
            st.session_state.difficulty == 'Select an Option'
        ]):
            st.error("Please make sure to select an option for all questions before submitting.")
        elif not all([
            st.session_state.mental_moved,
            st.session_state.success_moved,
            st.session_state.effort_moved,
            st.session_state.pace_moved,
            st.session_state.stress_moved
        ]):
            st.error("Please interact with all the sliders before proceeding.")
        else:
            end_time = datetime.now()
            st.session_state[f"submit_disabled_{survey_page}"] = True
            st.session_state["elapsed_time"] = str((end_time - st.session_state.time_spent).total_seconds())
            record_data_clear_state(
                ['complex_to_simple', 'thinking', 'thinking_fun', 'thought', 'new_solutions', 'difficulty',
                 'mental_slider', 'success_slider', 'effort_slider', 'pace_slider', 'stress_slider', "elapsed_time"],
                survey_page=survey_page
            )
            update_user_data("complete", 3)
            st.session_state.last_progress = 3
            st.rerun()


def survey():
    # st.title("Reflection Questions & Feedback")
    if show_transition(
        stage_key="survey_intro_done",
        stage_title="Survey Page",
        instructions=(
            "🎉 Thank You! Congratulations on completing the main study! 🎉\n\n"
            "We really appreciate your time and effort.\n\n"
            "Before you finish, please take a moment to answer a few short survey questions. "
            "Your responses help us improve future research and understand your experience better. Thank you!"
        ),
        button_label="Proceed to Survey"
    ):
        return

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
            ai_usage_questions()
        elif st.session_state.last_progress == 2:
            tasks_demand_questions()
        elif st.session_state.last_progress == 3:
            interaction_questions()
        elif st.session_state.last_progress == 4:
            free_form_questions()
        elif st.session_state.last_progress == 5:
            video_submission()
