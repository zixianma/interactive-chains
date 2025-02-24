import streamlit as st
from openai import OpenAI
import json
import requests
from streamlit_float import *
import re
from datetime import datetime
import time
import pages.utils.logger as logger


@st.cache_data
def load_data(path="./data/training_questions.json"):
    """Loads the training and main-study questions from JSON files."""
    with open(path, "r") as f:
        questions = json.load(f)
    
    questions = {int(k): v for k, v in questions.items()}

    return questions


def show_step_1(index):
    st.subheader("Step 1: Initial Questions")

    question = st.session_state.questions[index]

    st.write("**Question:**", question["question"])
    if index in st.session_state.idxtoimage:
        st.image(st.session_state.idxtoimage[index], caption=f"Image for the above question", use_container_width=True)
    
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

    if condition == "A. Answer only":
        st.markdown("**Model's Final Answer:**")
        st.warning(question.get("model_answer", "No answer available"))

        additional_info = None
    
    elif condition == "B. Paragraph CoT":
        st.markdown("**Model's Paragraph Chain-of-thought**")
        st.info(question.get("model_explanation", "No paragraph CoT available"))

        if index in st.session_state.idxtoimage:
            st.image(st.session_state.idxtoimage[index], caption=f"Image for the above question", use_container_width=True)

        st.markdown("**Model's Final Answer:**")
        st.warning(question.get("model_answer", "No answer available"))

        additional_info = question.get("model_explanation", None)
    
    elif condition == "C. Step-by-step CoT -- All at once":
        st.markdown("**Model's Step-by-step CoT:**")

        step_str = question.get("cot_steps", "")
        if step_str:
            parts = re.split(r"Step\s*\d+:", step_str)
            steps_list = [part.strip() for part in parts if part.strip()]

            with st.expander("Model chain of thought"):
                for i, step_text in enumerate(steps_list, start=1):
                    st.write(f"**Step {i}:** {step_text}")
        else:
            st.info("No step-by-step CoT available.")
        

        st.markdown("**Model's Final Answer:**")
        st.warning(question.get("model_answer", "No answer available."))

    elif condition == "D. Step-by-step CoT - Sequential":
        raise NotImplementedError
    
    elif condition == "E. Verifiable CoT":
        raise NotImplementedError
    

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
            # reset the submission flag for the next question.
            st.session_state.step_2_submitted = False
            st.session_state["next_clicked"] = True
            return
    else:
        st.button("Next", key=f"next_disabled_{index}", disabled=True, help="Please submit your response first.")


def main_study():

    if "count" not in st.session_state:
        st.session_state.count = 0
    
    questions = load_data(path="data/science_qa_gpt4_wrong_questions.json")  # pass in different path for different questions
    if "questions" not in st.session_state:
        st.session_state.questions = questions

    train_ids = [61, 841]
    test_ids = [2788, 9120, 20245]

    if 'train_ids' not in st.session_state:
        st.session_state["train_ids"] = train_ids
    if 'test_ids' not in st.session_state:
        st.session_state["test_ids"] = test_ids
    
    all_ids = train_ids + test_ids

    if "idxtoimage" not in st.session_state:
        st.session_state.idxtoimage = {
            61: "data/images/sciqa_61_image.png",
            841: "data/images/sciqa_841_image.png",
            2788: "data/images/sciqa_2788_image.png",
            9120: "data/images/sciqa_9120_image.png",
            20245: "data/images/sciqa_20245_image.png"
        }

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

    st.session_state.condition = "B. Paragraph CoT"  # now set to condition B for testing

    if st.session_state.count >= len(all_ids):
        st.session_state.page = "end_tutorial"
        st.rerun()
    
    if st.session_state.count < len(st.session_state['train_ids']):
        st.title("📚 Training phase")
        st.markdown("###### During this training phase, you will get to try answering 6 questions. You will see whether your answer is correct or not after you submit it. ")
        total_num = len(st.session_state['train_ids'])
        curr_pos = st.session_state.count + 1
    else:
        st.title("📝 Study phase")
        st.markdown("###### You are now in the study phase, where you will answer 30 questions in total and be rewarded if you answer more questions correctly. You will NOT see if your answer is correct or not.")
        total_num = len(st.session_state['test_ids'])

        curr_pos = st.session_state.count + 1 - len(st.session_state.train_ids)
    
    with st.expander("***See task instruction**"):
        st.markdown("In this study, you will decide whether the AI model's answer is correct or not based on the provided information. \
                    You should ACCEPT the AI model's answer when it is correct and REJECT when it is wrong")
    
        note = st.markdown(":red[Note that you should make your decision based ONLY on the **Information** on this interface (AI answer and/or AI chain-of-though). You will reach wrong answers if you rely on information from Wikipedia or ChatGPT.]")

    # Need to formolize the tutorial
    # with st.expander("**See tutorial**"):
    #     if st.session_state.condition == "C. hai-answer":
    #         left_inst = "On the left, you are given the AI model's suggested answer, which may be incorrect."
    #         left_inst = st.markdown(left_inst)

    #         right_inst = "On the right, you can perform either a Search or Lookup action to gather information about this claim and verify the AI's answer. "
    #         right_inst = st.markdown(right_inst)
    #     elif st.session_state.condition == "D. hai-static-chain":
    #         left_inst = "On the left, you are given the AI model's suggested answer along with its reasoning chain, which may be incorrect. "
    #         left_inst += "A reasoning chain is a list of thoughts, actions, and observations that help the model reason and reach its final answer. "
    #         left_inst = st.markdown(left_inst)

    #         right_inst = "On the right, you can perform either a Search or Lookup action to gather information about this claim and verify the AI's answer. "
    #         right_inst = st.markdown(right_inst)
            
    #     elif st.session_state.condition == "I. hai-regenerate":
    #         left_inst = "On the left, you are given the AI model's suggested answer along with its reasoning chain, which may be incorrect. "
    #         left_inst += "A reasoning chain is a list of thoughts, actions, and observations that help the model reason and reach its final answer. "
    #         left_inst = st.markdown(left_inst)

    #         right_inst = st.markdown("On the right, you can edit the AI model's thought or action anywhere in the reasoning chain.")
    #         right_inst_details = st.markdown(''' 
    #         - If you edit a thought and submit it, the action will be automatically updated by the AI. 
    #         - If you edit an action and submit it, the observation will be automatically updated. 
    #         - If you edit AI's thought or action at step $i$, all the steps at $i+1$ and after will be gone. You can then “Update the AI model's output” to complete the reasoning chain and obtain a new answer. ''')

    #     else:
    #         raise NotImplementedError
    #     if "condition2screenshots" not in st.session_state:
    #         st.session_state['condition2screenshots'] = {
    #                             "C. hai-answer": ["data/images/hai-answer-1.png", "data/images/hai-answer-2.png", "data/images/hai-answer-3.png", "data/images/hai-answer-4.png"], 
    #                             "D. hai-static-chain": ["data/images/hai-static-chain-1.png", "data/images/hai-static-chain-2.png", "data/images/hai-static-chain-3.png", "data/images/hai-static-chain-4.png"], 
    #                             "I. hai-regenerate": ["data/images/hai-regenerate-1.png", "data/images/hai-regenerate-2.png", "data/images/hai-regenerate-3.png", "data/images/hai-regenerate-4.png", "data/images/hai-regenerate-5.png"]
    #                         }
    #     screenshots = st.session_state['condition2screenshots'][st.session_state.condition]
    #     for i, screenshot in enumerate(screenshots):
    #         st.image(screenshot, caption=f"Step {i+1}")
    #         st.divider()


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
        st.session_state['Model Reasoning'] = question["model_explanation"]
        st.session_state['answer'] = question["answer"]
        st.session_state['gt_answer'] = question["ground_truth"]


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
    
    # "Username", "Question idx", "Condition", "Model Reasoning", "Model Answer", "Step 1", "Step 2", "Gt Answer"
    if st.session_state["next_clicked"]:
        # if not st.session_state[idx]['submitted']:
        #     warning.warning("You need to submit your answer before going to the next question.", icon="⚠️")
        #     # print(f'session state count vs total num: {st.session_state.count} {total_num}')]
        #     st.session_state["next_clicked"] = False
        # else:
            if st.session_state.condition == "E. Verifiable CoT":
                raise NotImplementedError
            else:
                logger.write_to_user_sheet([st.session_state.username, st.session_state.condition, idx,
                                            st.session_state['Model Reasoning'], st.session_state['answer'],
                                            st.session_state.step_1_response, st.session_state.step_2_response, st.session_state["gt_answer"]])
                
                st.session_state['Model Reasoning'] = ""
                st.session_state['answer'] = ""
                st.session_state['gt_answer'] = ""
                st.session_state.step_1_response = ""
                st.session_state.step_2_response = ""
                st.session_state.step_phase = 1
                st.session_state.count += 1
                st.session_state["next_clicked"] = False
                st.rerun()
    
