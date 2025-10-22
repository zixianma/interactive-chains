import openai
import streamlit as st
import json
import random
from streamlit_float import *
import re
from datetime import datetime
import pages.utils.logger as logger
from pages.utils.utils import *
import time
import unicodedata
# def select_indices(file_path="question_bank_cleaned.jsonl"):
#     """
#     Loads a JSONL file with questions and returns a list of indices that:
#       1. First includes all indices where is_correct == True and dataset != "train"
#       2. Then includes 5 random indices where is_correct == False and dataset == "math"
#       3. Then includes 5 random indices where is_correct == False and dataset == "gsm8k"
    
#     Args:
#         file_path (str): Path to the JSONL file.
    
#     Returns:
#         list: A list of selected indices.
#     """
#     # Load the dataset from JSONL file into a list of dictionaries
#     with open(file_path, "r", encoding="utf-8") as f:
#         data = [json.loads(line.strip()) for line in f]
    
#     # Get indices for correct answers and dataset not 'train'
#     correct_indices = [
#         i for i, entry in enumerate(data)
#         if entry.get("is_correct") is True and entry.get("dataset") != "train"
#     ]
    
#     # Get indices for incorrect answers where dataset is 'math'
#     math_incorrect_indices = [
#         i for i, entry in enumerate(data)
#         if entry.get("is_correct") is False and entry.get("dataset").lower() == "math"
#     ]
    
#     # Get indices for incorrect answers where dataset is 'gsm8k'
#     gsm_incorrect_indices = [
#         i for i, entry in enumerate(data)
#         if entry.get("is_correct") is False and entry.get("dataset").lower() == "gsm8k"
#     ]
    
#     # Randomly sample 5 indices from math_incorrect_indices if available
#     math_sampled = random.sample(math_incorrect_indices, 3) if len(math_incorrect_indices) >= 5 else math_incorrect_indices
    
#     # Randomly sample 5 indices from gsm_incorrect_indices if available
#     gsm_sampled = random.sample(gsm_incorrect_indices, 3) if len(gsm_incorrect_indices) >= 5 else gsm_incorrect_indices
    
#     correct_indices = random.sample(correct_indices, 6) if len(correct_indices) >= 6 else correct_indices
    
#     # Concatenate the indices list in the specified order
#     selected_indices = correct_indices + math_sampled + gsm_sampled
    
#     random.shuffle(selected_indices)
    
#     return selected_indices


def get_test_ids():
    # Use the already-created user worksheet stored in session state
    user_ws = st.session_state.get('user_worksheet')
    if user_ws is None:
        # Handle the case where the worksheet was not correctly saved.
        st.error("User worksheet not found!")
        return None
    
    test_ids_cell = user_ws.acell("K2").value
    if test_ids_cell:
        try:
            test_ids = json.loads(test_ids_cell)
        except Exception as e:
            st.error(f"Error parsing test IDs: {e}")
            return None
    else:
        # If the test IDs are not already there, generate and store them.
        fixed_id = [4, 5, 6]
        ids = [7, 8, 9, 10, 11, 12, 13, 14, 15]
        random_test_ids =  random.sample(ids, len(ids))
        test_ids = fixed_id + random_test_ids

    return test_ids


def show_step_1(index):
    st.subheader("Step 1: Perceived Difficulty")

    question = st.session_state.questions[index]
    st.write("**Question:**", question["question"])

    st.markdown("**How hard do you find this question?**  \n"
                "1 = Very Easy, 2 = Easy, 3 = Neither Easy nor Hard, 4 = Hard, 5 = Very Hard / No idea")

    # Initialize submission flag
    if "step_1_submitted" not in st.session_state:
        st.session_state.step_1_submitted = False

    # Hide the default radio placeholder label
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

    # Build options and labels
    response_placeholder = "Select difficulty"
    labels = {
        "1": "Very Easy",
        "2": "Easy",
        "3": "Neutral",
        "4": "Hard",
        "5": "Very Hard / No idea"
    }
    options = [response_placeholder] + list(labels.keys())

    # Render the radio with formatted labels
    response = st.radio(
        "Your selection",
        options=options,
        key=f"response_{index}",
        format_func=lambda x: x if x == response_placeholder else f"{x} -- {labels[x]}",
        label_visibility="collapsed",
        horizontal=False
    )

    warning = st.empty()
    st.divider()

    # Submit button
    if st.button("Submit", key=f"submit_{index}"):
        if response != response_placeholder:
            # Store as integer 1–5
            st.session_state.step_1_response = int(response)
            st.session_state.step_1_submitted = True
            st.success(f"Response submitted: {response} – {labels[response]}")
        else:
            warning.warning("Please select a difficulty before submitting.")

    # Next button: only enabled after submission
    if st.session_state.step_1_submitted:
        if st.button("Next", key=f"next_{index}"):
            st.session_state.step_phase = 2
            # reset the submission flag for the next question
            st.session_state.step_1_submitted = False
            st.rerun()
    else:
        st.button("Next", key=f"next_disabled_{index}", disabled=True, help="Please submit your response first.")

def normalize_text(text):
    # 1. Normalize Unicode
    text = unicodedata.normalize("NFKC", text)
    # 2. Remove Markdown symbols (*, _, $, `)
    text = re.sub(r'[*_$`]', '', text)
    # 3. Replace any remaining fancy Unicode (like 𝑎, 𝑏) with ASCII equivalents
    return ''.join(
        c if ord(c) < 128 else unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode("ascii")
        for c in text
    )

def show_step_2(index):
    st.subheader("Step 2: Model's Help & Your Decision")

    question = st.session_state.questions[index]
    st.write("**Question:**", question["question"])

    condition = st.session_state.condition

    # Flag to control whether Accept/Reject is allowed
    can_accept_reject = True

    if condition == "A. Answer only":
        st.markdown("**Model's Final Answer:**")
        st.warning(question.get("model_answer", "No answer available"))
    
    elif condition == "B. Paragraph CoT":
        #st.markdown("**Model's Paragraph Chain-of-thought**")
        st.write(question.get("paragraph_reasoning", "No paragraph CoT available"))
        
        '''
        if index in st.session_state.idxtoimage:
            st.image(
                st.session_state.idxtoimage[index],
                caption="Image for the above question",
                use_container_width=True,
            )
        '''
        
        st.markdown("**Model's Final Answer:**")
        st.warning(question.get("model_answer", "No answer available."))
    
    elif condition == "C. Step-by-step CoT -- All at once":
        #st.markdown("**Model's Step-by-step Chain-of-thought:**")
        step_str = question.get("reasoning_steps", "")
        
        if step_str:
            parts = re.split(r"Step\s*\d+:", step_str)
            steps_list = [part.strip() for part in parts if part.strip()]
            # Directly display all steps without an expander
            for i, step_text in enumerate(steps_list, start=1):
                st.write(f"**Step {i}:** {step_text}")
        else:
            st.info("No step-by-step CoT available.")
        
        st.markdown("**Model's Final Answer:**")
        st.warning(question.get("model_answer", "No answer available."))
    
    elif condition == "D. Step-by-step CoT -- Sequential":
        #st.markdown("**Model's Step-by-step Chain-of-thought:**")
        step_str = question.get("reasoning_steps", "")
        
        if step_str:
            parts = re.split(r"(?:\*\*)?Step\s*\d+:", step_str, flags=re.IGNORECASE)
            steps_list = [part.strip() for part in parts if part.strip()]

            if "current_step" not in st.session_state:
                st.session_state.current_step = 0

            total_steps = len(steps_list)

            # Display all steps up to (and including) the current step
            for i in range(st.session_state.current_step + 1):
                st.markdown(f"**Step {i+1}:** {steps_list[i]}", unsafe_allow_html=True)

            # If not at the final step, show the "Next Step" button centered
            if st.session_state.current_step < total_steps - 1:
                left_spacer, mid_col, right_spacer = st.columns([1, 2, 1])
                with left_spacer:
                    if st.button("Next Step", key="next_step"):
                        st.session_state.current_step += 1
                        st.rerun()
                can_accept_reject = False
            else:
                # When at final step, display the final answer on a new line
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**Model's Final Answer:**")
                st.warning(question.get("model_answer", "No answer available."))
                can_accept_reject = True
        else:
            st.info("No step-by-step CoT available.")
            can_accept_reject = False
   
    
    elif condition == "E. Editable Local Suggestion":
        #st.markdown("**Model's Editable Local Chain-of-thought (Step-by-step)**")

        # Initialize session state variables
        if "text_input_buffer" not in st.session_state:
            st.session_state.text_input_buffer = ""
        if "last_sent_input" not in st.session_state:
            st.session_state.last_sent_input = ""
        if "completion" not in st.session_state:
            st.session_state.completion = ""
        new_text = st.text_area(
            "Your answer",
            value=st.session_state.text_input_buffer,
            key="text_input_F",
            height=200
        )

        # Only update if user typed something new
        if new_text != st.session_state.text_input_buffer:
            st.session_state.text_input_buffer = new_text
        st.session_state["Answer in text"] = st.session_state.get("text_input_buffer", "")
        # st.session_state.text_input_buffer = st.text_area(
        #     "Your answer",
        #     value=st.session_state.text_input_buffer,
        #     key="text_input_F",
        #     height=200
        # )

        # If "Final Answer:" is in the answer box, show and stop generating
        if "Final Answer:" in st.session_state.text_input_buffer:
            st.markdown("**Model's Final Answer:**")
            final_answer = st.session_state.text_input_buffer.split("Final Answer:")[-1].strip()
            st.warning(final_answer if final_answer else "No final answer found.")
            can_accept_reject = True
        else:
            # Only generate if user changed input
            if st.session_state.text_input_buffer.strip() != st.session_state.last_sent_input.strip():
                prompt = f"""
                You are a helpful and concise math tutor. 
                The student may has already completed some steps. Your task is autocomplete the current step.
                Do not repeat previous words or jump ahead to the next step.  
                Maintain the "Step X" format if applicable.
                Provide pure text only, no highlight, LaTex, italic, markdown or other decorations.
                If it's your final step, include the final answer in your response, and start the sentence with "Final Answer: " in a separate line.



                Question: {question["question"]}

                Current step: "{st.session_state.text_input_buffer}"
                Instructions: Continue directly from the the current step orovide  the next step.
        """
                try:
                    from openai import OpenAI
#client = OpenAI(api_key=st.secrets["openai"]["api_key"])
                    
                    #openai.api_key = st.secrets["openai"]["api_key"]

#respond=client.chat.completions.create
                    #client = OpenAI(api_key=st.secrets["openai"]["api_key"])
                                        
                    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=200,
                        temperature=0.4,
                        #stop=["\n"]#
                    )
                    reply = normalize_text(response.choices[0].message.content.strip())
                    cleaned_reply = normalize_text(reply)
                    st.session_state.completion = cleaned_reply
                    st.session_state.last_sent_input = st.session_state.text_input_buffer
                except Exception as e:
                    st.error(f"Error fetching completion: {e}")

            # accept/clear suggestion
            if st.session_state.completion:
                st.markdown("Suggestion")
                st.write(st.session_state.completion)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Accept this suggestion"):
                            st.session_state.text_input_buffer += " " + st.session_state.completion
                            st.session_state.completion = ""
                            st.session_state.last_sent_input = st.session_state.text_input_buffer
                            st.session_state["Answer in text"] = st.session_state.text_input_buffer
                            user_id = st.session_state.get("user_id", "test_user")
                            q_id = question.get("id", "Q_unknown")
                            logger.log_user_action(st.session_state['sheet'], user_id, "Accept", st.session_state["Answer in text"], q_id)
    
                            st.rerun()
                with col2:
                    if st.button("Clear suggestion"):
                        st.session_state.completion = ""
                        user_id = st.session_state.get("user_id", "test_user")
                        q_id = question.get("id", "Q_unknown")
                        logger.log_user_action( st.session_state['sheet'], user_id, "Clear", st.session_state["Answer in text"], q_id)

                        st.rerun()

    elif condition == "F. Editable Global Suggestion":
        #st.markdown("**Model's Editable Global Chain-of-thought (Step-by-step)**")

        # Initialize session state variables
        if "text_input_buffer" not in st.session_state:
            st.session_state.text_input_buffer = ""
        if "last_sent_input" not in st.session_state:
            st.session_state.last_sent_input = ""
        if "completion" not in st.session_state:
            st.session_state.completion = ""

        st.session_state.text_input_buffer = st.text_area(
            "Your answer",
            value=st.session_state.text_input_buffer,
            key="text_input_F",
            height=200
        )
        
        st.session_state["Answer in text"] = st.session_state.get("text_input_buffer", "")
        
        # If "Final Answer:" is in the answer box, show and stop generating
        if "Final Answer:" in st.session_state.text_input_buffer:
            st.markdown("**Model's Final Answer:**")
            final_answer = st.session_state.text_input_buffer.split("Final Answer:")[-1].strip()
            st.warning(final_answer if final_answer else "No final answer found.")
            can_accept_reject = True
        else:
            # Only generate if user changed input
            if st.session_state.text_input_buffer.strip() != st.session_state.last_sent_input.strip():
                prompt = f"""
    You are a helpful and concise math tutor assisting a student with step-by-step problem solving.
    Question: {question["question"]}
    So far, we have completed "{st.session_state.text_input_buffer}"
    Your task:
        -First autocomplete the current step, and then complete the rest until you got the final answer.
        -DON'T repeat what the student already said.
        -pure text only, no highlight, LaTex, italic, markdown or other decorations.
        -mark "Step X:" before a new step, end each step with a newline.
        -If it's your final step, include the final answer in your response, and start the sentence with "Final Answer: " in a separate line.
    """
                try:
                    from openai import OpenAI
#client = OpenAI(api_key=st.secrets["openai"]["api_key"])
                    
                    #openai.api_key = st.secrets["openai"]["api_key"]

#respond=client.chat.completions.create

                    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        #max_tokens=700,
                        temperature=0.4
                    )
                    reply = normalize_text(response.choices[0].message.content.strip())
                    cleaned_reply = normalize_text(reply)
                    st.session_state.completion = cleaned_reply
                    st.session_state.last_sent_input = st.session_state.text_input_buffer
                except Exception as e:
                    st.error(f"Error fetching completion: {e}")

            # accept/clear suggestion
            if st.session_state.completion:
                st.markdown("Suggestion")
                st.write(st.session_state.completion)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Accept this suggestion"):
                        st.session_state.text_input_buffer += " " + st.session_state.completion
                        st.session_state.completion = ""
                        st.session_state.last_sent_input = st.session_state.text_input_buffer
                        st.session_state["Answer in text"] = st.session_state.text_input_buffer
                        user_id = st.session_state.get("user_id", "test_user")
                        q_id = question.get("id", "Q_unknown")
                        logger.log_user_action( st.session_state['sheet'], user_id, "Accept", st.session_state["Answer in text"], q_id)

                        st.rerun()
                with col2:
                    if st.button("Clear suggestion"):
                        st.session_state.completion = ""
                        user_id = st.session_state.get("user_id", "test_user")
                        q_id = question.get("id", "Q_unknown")
                        logger.log_user_action( st.session_state['sheet'], user_id, "Clear", st.session_state["Answer in text"], q_id)

                        st.rerun()

    # Accept/Reject Section: Only available if allowed
    if not can_accept_reject:
        st.info("Please finish reading all steps before deciding.")
        return

    st.markdown("**Do you ACCEPT or REJECT the model's answer?**")

    if "step_2_submitted" not in st.session_state:
        st.session_state.step_2_submitted = False

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
    
    response_placeholder = "Select your response"
    response = st.radio(
        "Your selection",
        options=[response_placeholder, "Yes, I ACCEPT the model's answer", "No, I REJECT the model's answer"],
        key=f"response_{index}",
        label_visibility="collapsed"
    )

    mapping = {
        "Yes, I ACCEPT the model's answer": "Accept",
        "No, I REJECT the model's answer": "Reject"
    }
    warning = st.empty()
    st.divider()

    if st.button("Submit", key=f"submit_{index}"):
        if response and response != response_placeholder:
            st.session_state.step_2_response = mapping[response]
            st.session_state.step_2_submitted = True
            st.success("Response submitted!")
        else:
            warning.warning("Please select an option before submitting.")
    # clear the buffer at the end of a full question
    # if st.session_state.get("step_2_submitted", False) and "text_input_buffer" in st.session_state:
    #     st.session_state.text_input_buffer = ""
    #     st.session_state.completion = ""

    # As soon as step_2_submitted is True, show the helpfulness radio
    if st.session_state.get("step_2_submitted", False):
        st.markdown("## Step 3: How helpful was the AI model's information for your decision?", unsafe_allow_html=True)
        helpfulness_placeholder = "Select helpfulness"
        helpful_key = f"helpfulness_{index}"
        helpfulness = st.radio(
            "", options=[0,1,2,3,4,5],
            format_func=lambda x: {
                0:helpfulness_placeholder,
                1:"1 — Very unhelpful",
                2:"2 — Somewhat unhelpful",
                3:"3 — Neutral",
                4:"4 — Somewhat helpful",
                5:"5 — Very helpful"
            }[x],
            key=helpful_key
        )

    if st.session_state.get("step_2_submitted", False) and f"helpfulness_{index}" in st.session_state and helpfulness != 0:
        if st.button("Next", key=f"next_{index}"):
            st.session_state.step_phase = 1
            st.session_state.step_2_submitted = False
            st.session_state.current_step = 0
            st.session_state.next_clicked = True
            st.session_state["Answer in text"] = st.session_state.get("text_input_buffer", "")
            st.session_state.text_input_buffer = ""
            st.session_state.completion = ""
            return
    else:
        st.button(
            "Next",
            key=f"next_disabled_{index}",
            disabled=True,
            help="Please submit your decision and rate helpfulness first."
        )       

# def finished():
#     st.title("Thank you for your time!")
#     st.subheader("You will be compensated after we review your answers and footage. Click the link below to complete the study.")
#     st.write("https://app.prolific.com/submissions/complete?cc=C1IZ4VLN")   ## Need change this!!
    

def main_study():

    if "count" not in st.session_state:
        if st.session_state.questions_done == -1:
            st.session_state.count = 0
        else:
            st.session_state.count = st.session_state.questions_done

    if "question_start_time" not in st.session_state:
        st.session_state["question_start_time"] = time.time()

    if "completion" not in st.session_state:
        st.session_state["completion"] = ""
    
    question = load_data(path="data/question_bank_final_cleaned.jsonl")
    
    if "questions" not in st.session_state:
        st.session_state.questions = question

    # Need to finalize when creating the final question bank
    train_ids = [0, 1, 2, 3]
    test_ids = get_test_ids()

    test_ids_str = json.dumps(test_ids)
    
    if 'train_ids' not in st.session_state:
        st.session_state["train_ids"] = train_ids
    if 'test_ids' not in st.session_state:
        st.session_state["test_ids"] = test_ids
    
    all_ids = train_ids + test_ids

    """
    if "idxtoimage" not in st.session_state:
        st.session_state.idxtoimage = {
            61: "data/images/sciqa_61_image.png",
            841: "data/images/sciqa_841_image.png",
            2788: "data/images/sciqa_2788_image.png",
            9120: "data/images/sciqa_9120_image.png",
            20245: "data/images/sciqa_20245_image.png"
        }
    """

    all_conditions = ["A. Answer only", "B. Paragraph CoT", "C. Step-by-step CoT -- All at once",
                      "D. Step-by-step CoT -- Sequential", "E. Editable Local Suggestion", "F. Editable Global Suggestion"]

    if st.session_state.count >= len(all_ids):
        st.session_state.page = "end_tutorial"
        st.rerun()

    
    if st.session_state.count < len(st.session_state['train_ids']):
        # Training Phase.
        # Show the transition screen for training if not already done.
        if show_transition(
            stage_key="training_transition_done",
            stage_title="The Training Phase",
            instructions=(
                "In this training phase, you will answer 4 questions to get familiar with the study process. "
                "In Step 1, rate how difficult you find the math problem on a scale from 1 (Very Easy) to 5 (Very Hard). "
                "In Step 2, evaluate the AI model's answer by choosing to ACCEPT or REJECT it. Good luck!"
            ),
            button_label="Proceed to Training Phase"
        ):
            return
    #for method ef
        if st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
            st.title("📚 Training phase")
            # st.markdown("""
            # ###### During this training phase, you will answer 4 questions to help you get familiar with the study process.

            # **Step 1:** You will be asked to rate how hard you think the question is, on a scale from 1 (Very Easy) to 5 (Very Hard).  
            # Please be honest—your response to Step 1 will not influence the reward you receive.

            # **Step 2:** You will then see a text box where you can write your answer.  
            # As you type, the AI model may **autocomplete your response** (either step-by-step or all at once, depending on your condition).  
            # When you reach your final answer, please clearly mark it with:  **`Final Answer:`**  
            # You will decide whether to **ACCEPT** or **REJECT** the model's answer based on the information provided:
            # ✅ Accept when the model is correct.  
            # ❌ Reject when the model is wrong.

            # **Step 3:** After each question, you will answer a brief survey about how helpful the AI model's information was in guiding your decision.  
            # This refers to whether the explanation made it easier to identify an error (and reject the answer) or helped you follow the reasoning to a correct answer (and accept it).  
            # You will rate this from 1 (Very unhelpful) to 5 (Very helpful).
            # """)
        #for method cd     
        else:
            st.title("📚 Training phase")
            # st.markdown("""
            # ###### During this training phase, you will answer 4 questions to help you get familiar with the study process.

            # **Step 1:** You will be asked to rate how hard you think the question is, on a scale from 1 (Very Easy) to 5 (Very Hard).  
            # Please be honest—your response to Step 1 will not influence the reward you receive.

            # **Step 2:** You will be shown the model's answer and (optionally) its explanation.  
            # You will decide whether to **ACCEPT** or **REJECT** the model's answer based on the information provided:

            # ✅ Accept when the model is correct.  
            # ❌ Reject when the model is wrong.

            # **Step 3:** After each question, you will answer a brief survey about how helpful the AI model's information was in guiding your decision.  
            # This refers to whether the explanation made it easier to identify an error (and reject the answer) or helped you follow the reasoning to a correct answer (and accept it).  
            # You will rate this from 1 (Very unhelpful) to 5 (Very helpful).
            # """)
        total_num = len(st.session_state['train_ids'])
        curr_pos = st.session_state.count + 1
    else:
        # Actual Study Phase.
        # Show the transition screen for study phase if not already done.
        if show_transition(
            stage_key="study_transition_done",
            stage_title="The Study Phase",
            instructions=(
                "You have now entered the Study Phase. In this phase, you will answer 12 questions.\n\n"
                "Your performance will determine your reward, and you will NOT be shown whether your answer is correct.\n\n"
                ":red[**You will be provided AI assistance throughout the study. Please do not use any other external tools or AI models during the study. "
                "We might reject your submission if we believe your answers are abnormal due to the use of other tools.**]\n\n"
                "Good luck!"
            ),
            button_label="Proceed to Study Phase"
        ):
            return

        st.title("📝 Study phase")
        st.markdown("###### You are now in the study phase, where you will answer 20 questions in total and be rewarded if you answer more questions correctly.")
        total_num = len(st.session_state['test_ids'])
        curr_pos = st.session_state.count + 1 - len(st.session_state.train_ids)

    with st.expander("***See task instructions***"):
        #for method ef
        if st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
            # st.title("📚 Training phase")
            # During this training phase, you will answer 4 questions to help you get familiar with the study process.
            st.markdown("""
            ###### For each question, please follow the steps below:
                        
            **Step 1:** You will be asked to rate how hard you think the question is, on a scale from 1 (Very Easy) to 5 (Very Hard).  
            Please be honest—your response to Step 1 will not influence the reward you receive.

            **Step 2:** You will then see a text box where you can write your answer.  
            As you type, the AI model may **autocomplete your response**, and you can choose to accept or ignore its suggestions.
            When you reach your final answer, please clearly mark it with:  **`Final Answer:`**  
            You will decide whether to **ACCEPT** or **REJECT** the model's answer based on the AI response.

            **Step 3:** After each question, you will answer a brief survey about how helpful the AI model's information was in guiding your decision.  
            """)
        #for method cd     
        else:
            # st.title("📚 Training phase")
            # During this training phase, you will answer 4 questions to help you get familiar with the study process.
            st.markdown("""
            ###### For each question, please follow the steps below:
            **Step 1:** You will be asked to rate how hard you think the question is, on a scale from 1 (Very Easy) to 5 (Very Hard).  
            Please be honest—your response to Step 1 will not influence the reward you receive.

            **Step 2:** You will be shown the model's answer and (optionally) its explanation.  
            You will decide whether to **ACCEPT** or **REJECT** the model's answer based on the information provided:

            ✅ Accept when the model is correct.  
            ❌ Reject when the model is wrong.

            **Step 3:** After each question, you will answer a brief survey about how helpful the AI model's information was in guiding your decision.  
            This refers to whether the explanation made it easier to identify an error (and reject the answer) or helped you follow the reasoning to a correct answer (and accept it).  
            You will rate this from 1 (Very unhelpful) to 5 (Very helpful).
            """)
        note = st.markdown("""
            :red[**Note:** Please base your decision **only** on the information shown in this interface (the AI's answer and/or its explanations).  
            Relying on external sources like Google or ChatGPT may lead you to incorrect conclusions.]
        """)


    if "next_clicked" not in st.session_state:
        st.session_state["next_clicked"] = False
    
    st.text(f"You are at {curr_pos} / {total_num} questions.")

    idx = all_ids[st.session_state.count]

    question = st.session_state.questions[idx]
    
    warning = st.empty()
    st.divider()
    

    # st.session_state['Model Reasoning'] = question["model_explanation"]
    st.session_state['Model answer'] = question["model_answer"]
    st.session_state['gt_answer'] = question["correct_answer"]
    st.session_state['Answer in text'] = st.session_state.completion

    if "step_phase" not in st.session_state:
        st.session_state.step_phase = 1
    if "step_1_response" not in st.session_state:
        st.session_state.step_1_response = ""
    if "step_2_response" not in st.session_state:
        st.session_state.step_2_response = ""
    

    if st.session_state.step_phase == 1:
        show_step_1(idx)
    elif st.session_state.step_phase == 2:
        show_step_2(idx)
    else:
        raise NotImplementedError
    
    # "Username", "Question idx", "Condition", "Model Answer", "Step 1", "Step 2", "Gt Answer"
    if st.session_state["next_clicked"]:
        # if not st.session_state[idx]['submitted']:
        #     warning.warning("You need to submit your answer before going to the next question.", icon="⚠️")
        #     # print(f'session state count vs total num: {st.session_state.count} {total_num}')]
        #     st.session_state["next_clicked"] = False
        # else:
            time_spent = time.time() - st.session_state["question_start_time"]
        
            help_score = st.session_state.get(f"helpfulness_{idx}", "")
        

            answer_text = st.session_state.get("Answer in text", "") or st.session_state.get("text_input_buffer", "")
            final_answer_from_text = ""
        # Check if the "Final Answer:" substring exists in the user's input
            if "Final Answer:" in answer_text:
            # Split the string and get the part after "Final Answer:", then strip whitespace
                final_answer_from_text = answer_text.split("Final Answer:")[-1].strip()
            logger.write_to_user_sheet(
                [
                    st.session_state.username,
                    st.session_state.condition,
                    idx,
                    final_answer_from_text,
                    st.session_state.step_1_response,
                    st.session_state.step_2_response,
                    help_score,
                    st.session_state["gt_answer"],
                    time_spent,
                    st.session_state.count + 1,
                    test_ids_str,
                    answer_text
                ],
                #answer_text=answer_text
            )

            
            st.session_state['Model Reasoning'] = ""
            st.session_state['Model answer'] = ""
            st.session_state['gt_answer'] = ""
            # if st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
            #     st.session_state['Answer in text'] = ""
            st.session_state.step_1_response = ""
            st.session_state.step_2_response = ""
            # remove the helpfulness rating
            st.session_state.pop(f"helpfulness_{idx}", None)
            # optionally also clear the radio selection itself
            st.session_state.pop(f"response_{idx}",    None)
            st.session_state.step_phase = 1
            st.session_state.count += 1
            st.session_state["question_start_time"] = time.time()
            st.session_state["next_clicked"] = False
            st.rerun()
    
