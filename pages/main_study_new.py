import streamlit as st
import json
import random
from streamlit_float import *
import re
from datetime import datetime
import time
import pages.utils.logger as logger
import time
import os


@st.cache_data
def load_data(path="./data/training_questions.json"):
    """Loads the training and main-study questions from JSON or JSONL files."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    # Handle JSONL files
    if path.endswith(".jsonl"):
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                data.append(json.loads(line.strip()))
        return data

    # Handle standard JSON files
    elif path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {int(k): v for k, v in data.items()}

    else:
        raise ValueError("Unsupported file format. Please use .json or .jsonl")


def select_indices(file_path="question_bank.jsonl"):
    """
    Loads a JSONL file with questions and returns a list of indices that:
      1. First includes all indices where is_correct == True and dataset != "train"
      2. Then includes 5 random indices where is_correct == False and dataset == "math"
      3. Then includes 5 random indices where is_correct == False and dataset == "gsm8k"
    
    Args:
        file_path (str): Path to the JSONL file.
    
    Returns:
        list: A list of selected indices.
    """
    # Load the dataset from JSONL file into a list of dictionaries
    with open(file_path, "r", encoding="utf-8") as f:
        data = [json.loads(line.strip()) for line in f]
    
    # Get indices for correct answers and dataset not 'train'
    correct_indices = [
        i for i, entry in enumerate(data)
        if entry.get("is_correct") is True and entry.get("dataset") != "train"
    ]
    
    # Get indices for incorrect answers where dataset is 'math'
    math_incorrect_indices = [
        i for i, entry in enumerate(data)
        if entry.get("is_correct") is False and entry.get("dataset").lower() == "math"
    ]
    
    # Get indices for incorrect answers where dataset is 'gsm8k'
    gsm_incorrect_indices = [
        i for i, entry in enumerate(data)
        if entry.get("is_correct") is False and entry.get("dataset").lower() == "gsm8k"
    ]
    
    # Randomly sample 5 indices from math_incorrect_indices if available
    math_sampled = random.sample(math_incorrect_indices, 5) if len(math_incorrect_indices) >= 5 else math_incorrect_indices
    
    # Randomly sample 5 indices from gsm_incorrect_indices if available
    gsm_sampled = random.sample(gsm_incorrect_indices, 5) if len(gsm_incorrect_indices) >= 5 else gsm_incorrect_indices
    
    # Concatenate the indices list in the specified order
    selected_indices = correct_indices + math_sampled + gsm_sampled
    
    random.shuffle(selected_indices)
    
    return selected_indices


def get_test_ids():
    # Use the already-created user worksheet stored in session state
    user_ws = st.session_state.get('user_worksheet')
    if user_ws is None:
        # Handle the case where the worksheet was not correctly saved.
        st.error("User worksheet not found!")
        return None
    
    test_ids_cell = user_ws.acell("J2").value
    if test_ids_cell:
        try:
            test_ids = json.loads(test_ids_cell)
        except Exception as e:
            st.error(f"Error parsing test IDs: {e}")
            return None
    else:
        # If the test IDs are not already there, generate and store them.
        test_ids = select_indices("data/question_bank.jsonl")
    
    return test_ids
    

def show_step_1(index):
    st.subheader("Step 1: Initial Questions")

    question = st.session_state.questions[index]

    st.write("**Question:**", question["question"])
    # if index in st.session_state.idxtoimage:
    #     st.image(st.session_state.idxtoimage[index], caption=f"Image for the above question", use_container_width=True)
    
    st.markdown("**Do you know how to solve this question?**")

    if "step_1_submitted" not in st.session_state:
        st.session_state.step_1_submitted = False

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
        options=[response_placeholder, "Yes, I know how to solve it", "I am not sure / I don't know"],
        key=f"response_{index}",
        label_visibility="collapsed"
    )

    mapping = {
        "Yes, I know how to solve it": "Yes",
        "I am not sure / I don't know": "No"
    }

    warning = st.empty()
    st.divider()

    if st.button("Submit", key=f"submit_{index}"):
        if response and response != response_placeholder:
            st.session_state.step_1_response = mapping[response]
            st.session_state.step_1_submitted = True
            st.success("Response submitted!")
        else:
            warning.warning("Please select an option before submitting.")

    if st.session_state.step_1_submitted:
        if st.button("Next", key=f"next_{index}"):
            st.session_state.step_phase = 2
            # reset the submission flag for the next question.
            st.session_state.step_1_submitted = False
            st.rerun()
    else:
        st.button("Next", key=f"next_disabled_{index}", disabled=True, help="Please submit your response first.")

    
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
        st.markdown("**Model's Paragraph Chain-of-thought**")
        st.info(question.get("paragraph_reasoning", "No paragraph CoT available"))
        
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
        st.markdown("**Model's Step-by-step Chain-of-thought:**")
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
        st.markdown("**Model's Step-by-step Chain-of-thought:**")
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
                with mid_col:
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
    
    elif condition == "E. Verifiable CoT":
        raise NotImplementedError

    st.markdown("---")  # Divider

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

    if st.session_state.step_2_submitted:
        if st.button("Next", key=f"next_{index}"):
            st.session_state.step_phase = 1
            # Reset for next question
            st.session_state.step_2_submitted = False
            st.session_state.current_step = 0
            st.session_state["next_clicked"] = True
            return
    else:
        st.button("Next", key=f"next_disabled_{index}", disabled=True, help="Please submit your response first.")


def finished():
    st.title("Thank you for your time!")
    st.subheader("You will be compensated after we review your answers and footage. Click the link below to complete the study.")
    st.write("https://app.prolific.com/submissions/complete?cc=C1IZ4VLN")   ## Need change this!!
    

def main_study():

    if "count" not in st.session_state:
        if st.session_state.questions_done == -1:
            st.session_state.count = 0
        else:
            st.session_state.count = st.session_state.questions_done

    if "question_start_time" not in st.session_state:
        st.session_state["question_start_time"] = time.time()
    

    # if st.session_state.condition == "A. Answer only":
    #     raise NotImplementedError
    # elif st.session_state.condition == "B. Paragraph CoT":
    #     questions = load_data(path="data/science_qa_gpt4_wrong_questions.json")
    # elif st.session_state.condition == "E. Verifiable CoT":
    #     raise NotImplementedError
    # else:
    #     questions = load_data(path="data/GSM8k_incorrect_example.jsonl")  # pass in different path for different questions
    
    question = load_data(path="data/question_bank.jsonl")
    
    if "questions" not in st.session_state:
        st.session_state.questions = question

    # Need to finalize when creating the final question bank
    # train_ids = [61, 841]
    # test_ids = [2788, 9120, 20245]

    train_ids = [0, 1, 2, 3, 4, 5]
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
                      "D. Step-bt-step CoT -- Sequential", "E. Verifiable CoT"]
    # condition = st.radio(
    #         "Condition",
    #         all_conditions, # "hai-interact-chain", "hai-interact-chain-delayed", 
    #         # captions=["A", "C", "D", "E", "F", "G"]
    #         index=all_conditions.index(st.session_state.condition),
    # )
    # st.session_state.condition = condition
    # print(st.session_state.condition)

    # st.session_state.condition = "B. Paragraph CoT"  # now set to condition B for testing

    if st.session_state.count >= len(all_ids):
        # st.session_state.page = "end_tutorial"
        # st.rerun()
        finished()
        return
    
    if st.session_state.count < len(st.session_state['train_ids']):
        st.title("📚 Training phase")
        st.markdown("""
            ###### During this training phase, you will answer 6 questions to help you get familiar with the study process.

            **Step 1:** You will be asked whether you can solve a math problem on your own. Please be honest—your response to Step 1 will not influence the reward you receive.

            **Step 2:** You will be shown the model's answer and (optionally) its explanation. You will decide whether to **ACCEPT** or **REJECT** the model's answer based on the information provided:  

            ✅ Accept when the model is correct.  
            ❌ Reject when the model is wrong.
        """)
        total_num = len(st.session_state['train_ids'])
        curr_pos = st.session_state.count + 1
    else:
        st.title("📝 Study phase")
        st.markdown("###### You are now in the study phase, where you will answer 20 questions in total and be rewarded if you answer more questions correctly. You will NOT see if your answer is correct or not.")
        total_num = len(st.session_state['test_ids'])

        curr_pos = st.session_state.count + 1 - len(st.session_state.train_ids)
    
    with st.expander("***See task instructions***"):
        st.markdown("""
            In this study, you will evaluate whether the AI model's answer is correct based on the information provided.

            You should **ACCEPT** the AI model's answer when it is correct, and **REJECT** it when it is wrong.
        """)

        note = st.markdown("""
            :red[**Note:** Please base your decision **only** on the information shown in this interface (the AI's answer and/or its chain of thought).  
            Relying on external sources like Wikipedia or ChatGPT may lead you to incorrect conclusions.]
        """)


    if "next_clicked" not in st.session_state:
        st.session_state["next_clicked"] = False
    
    st.text(f"You are at {curr_pos} / {total_num} questions.")

    idx = all_ids[st.session_state.count]

    question = st.session_state.questions[idx]
    
    warning = st.empty()
    st.divider()
    
    if st.session_state.condition == "A. Answer only":
        st.session_state['Model Reasoning'] = ""
    elif st.session_state.condition == "E. Verifiable CoT":
        raise NotImplementedError
    else:
        # st.session_state['Model Reasoning'] = question["model_explanation"]
        st.session_state['Model answer'] = question["model_answer"]
        st.session_state['gt_answer'] = question["correct_answer"]


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
            if st.session_state.condition == "E. Verifiable CoT":
                raise NotImplementedError
            else:
                logger.write_to_user_sheet([st.session_state.username, st.session_state.condition, idx,
                                            st.session_state['Model answer'], st.session_state.step_1_response,
                                            st.session_state.step_2_response, st.session_state["gt_answer"],
                                            time_spent, st.session_state.count + 1, test_ids_str])
                
                st.session_state['Model Reasoning'] = ""
                st.session_state['Model answer'] = ""
                st.session_state['gt_answer'] = ""
                st.session_state.step_1_response = ""
                st.session_state.step_2_response = ""
                st.session_state.step_phase = 1
                st.session_state.count += 1
                st.session_state["question_start_time"] = time.time()
                st.session_state["next_clicked"] = False
                st.rerun()
    
