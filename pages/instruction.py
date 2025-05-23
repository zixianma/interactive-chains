import streamlit as st
from pages.utils.utils import load_data
import json
import time

@st.cache_data
def load_examples():
    examples_file = 'data/examples.json'
    with open(examples_file, 'r') as f:
        examples = json.load(f)
    return examples

def instruction():
    st.title("Task Tutorial")
    st.subheader("Please read the task instructions below carefully before proceeding.")
    st.markdown(
        "In this study, you will first be shown a math problem and asked to evaluate its difficulty by selecting a value on a Likert scale from 1 (Very Easy) to 5 (Very Hard). "
        "Next, you will review an AI model's answer (which may include its reasoning, depending on the condition). "
        "Your task is to critically evaluate the solution and decide whether to **ACCEPT** it (if the answer and reasoning are correct) or **REJECT** it (if you find any errors in the logic or result). "
        "Below are examples to help you understand when to choose each option."
    )

    # Check the current condition, defaulting to "C. Step-by-step CoT -- All at once" if not set.
    condition = st.session_state.get("condition", "C. Step-by-step CoT -- All at once")
    
    # Display condition-specific instructions.
    if condition == "A. Answer only":
        st.markdown(
            "**Instructions:** Please decide based solely on the question and the AI model's answer. "
            "For rejected examples, you may reveal the ground truth solution for an explanation."
        )
    elif condition == "B. Paragraph CoT":
        st.markdown(
            "**Instructions:** Evaluate the provided paragraph reasoning along with the model's answer. "
            "For correct examples, note that both the reasoning and answer are correct. For incorrect examples, you can review the ground truth solution that explains the error."
        )
    elif condition in ["C. Step-by-step CoT -- All at once", "D. Step-by-step CoT -- Sequential"]:
        st.markdown(
            "**Instructions:** Evaluate the detailed step-by-step reasoning, the question, and the model's answer. "
            "For rejected examples, check the ground truth solution that highlights the mistakes."
        )
    
    # Create an outer expander for the examples.
    with st.expander("Examples", expanded=True):
        examples = load_examples()
    
        # Display examples based on condition.
        for key in examples:  # key is expected to be "ACCEPT" or "REJECT"
            ex = examples[key]
    
            st.markdown(f"#### {key} Example")
            st.markdown(f"**Question:** {ex['question']}")
    
            if condition == "A. Answer only":
                st.markdown(f"**Model Answer:** {ex['model_answer']}")
                if key == "ACCEPT":
                    st.markdown("**Instruction:** Choose **ACCEPT** because the model's answer is correct.")
                else:
                    st.markdown("**Instruction:** Choose **REJECT** because the model's answer is incorrect. You can check the correct solution below.")
                    if st.checkbox("Show Ground Truth Solution", key=f"gt_{key}"):
                        st.markdown(ex['gt_solution'])
    
            elif condition == "B. Paragraph CoT":
                st.markdown(f"** Reasoning:** {ex['paragraph_reasoning']}", unsafe_allow_html=True)
                st.markdown(f"**Model Answer:** {ex['model_answer']}")
                if key == "ACCEPT":
                    st.markdown("**Instruction:** Choose **ACCEPT** because the model's reasoning and answer are correct.")
                else:
                    if st.checkbox("Show Ground Truth Solution", key=f"gt_{key}"):
                        st.markdown(ex['gt_solution'])
                    st.markdown("**Instruction:** Choose **REJECT** because the model's answer and its reasoning are incorrect. The incorrect or flawed part of the model's reasoning is highlighted in red for your reference.")
    
            elif condition in ["C. Step-by-step CoT -- All at once", "D. Step-by-step CoT -- Sequential"]:
                st.markdown("**Model's Reasoning:**")
                st.markdown(ex['reasoning_steps'], unsafe_allow_html=True)
                st.markdown(f"**Model Answer:** {ex['model_answer']}")
                if key == "ACCEPT":
                    st.markdown("**Instruction:** Choose **ACCEPT** because the step-by-step reasoning and answer are correct.")
                else:
                    if st.checkbox("Show Ground Truth Solution", key=f"gt_{key}"):
                        st.markdown(ex['gt_solution'])
                    st.markdown("**Instruction:** Choose **REJECT** because the model's answer and its reasoning are incorrect. The incorrect or flawed part of the model's reasoning is highlighted in red for your reference.")

    # Countdown timer before the "Next" button appears.
    if "instruction_done" not in st.session_state:
        st.session_state["instruction_done"] = False
    if "remaining_time" not in st.session_state:
        st.session_state["s"] = 45  # Set to 60 seconds or desired duration.

    placeholder = st.empty()

    def click_next():
        st.session_state["instruction_done"] = True

    if not st.session_state["instruction_done"]:
        for secs in range(st.session_state["remaining_time"], 0, -1):
            st.session_state["remaining_time"] = secs
            mm, ss = divmod(secs, 45)
            placeholder.metric("Remaining Time", f"{mm:02d}:{ss:02d}")
            time.sleep(1)
    next_button = st.button("Next", on_click=click_next)
    if st.session_state["instruction_done"]:
        st.session_state.page = "main_study"
        st.rerun()

if __name__ == "__main__":
    instruction()
