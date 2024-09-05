import streamlit as st
import json
import time
from hotjar import load_hotjar

@st.cache_data
def load_examples():
    examples_file = 'data/examples.json'
    with open(examples_file, 'r') as f:
        examples = json.load(f)
    return examples

def instruction():
    load_hotjar()

    st.title("Task Instruction")
    st.subheader("Please take at least 2 minutes to read the task instructions below carefully before proceeding.")
    st.text("A Next button will show up at the bottom after 2 minutes for you to go to the next page.")
    ph = st.empty()
    goal = st.markdown("In this study, you will decide with the help of an AI model if there is evidence in the **Observation** that SUPPORTS or REFUTES a **Claim**, or if there is NOT ENOUGH INFORMATION.")
    definitions = st.markdown("""An **Observation** is some text returned by an **Action**, which includes *Search*, *Lookup* and *Finish*.""")
                  
    action_definitions = st.markdown('''
    - The *Search* action searches for the document that's the most related to the keyword you enter. 
    - The *Lookup* action finds a text in the last document found by Search or returns “no more results” if the text is not found. 
    - The *Finish* action submits one of the three answers: SUPPORTS, REFUTES, or NOT ENOUGH INFO about the claim.''')
    
    # if st.session_state.condition == "C. hai-answer":
    #     left_inst = "On the left, you are given the AI model's suggested answer, which may be incorrect."
    #     left_inst = st.markdown(left_inst)

    #     right_inst = "On the right, you can perform either a Search or Lookup action to gather information about this claim and verify the AI's answer. "
    #     right_inst = st.markdown(right_inst)
    # elif st.session_state.condition == "D. hai-static-chain":
    #     left_inst = "On the left, you are given the AI model's suggested answer along with its reasoning chain, which may be incorrect. "
    #     left_inst += "A reasoning chain is a list of thoughts, actions, and observations that help the model reason and reach its final answer. "
    #     left_inst = st.markdown(left_inst)

    #     right_inst = "On the right, you can perform either a Search or Lookup action to gather information about this claim and verify the AI's answer. "
    #     right_inst = st.markdown(right_inst)
        
    # elif st.session_state.condition == "I. hai-regenerate":
    #     left_inst = "On the left, you are given the AI model's suggested answer along with its reasoning chain, which may be incorrect. "
    #     left_inst += "A reasoning chain is a list of thoughts, actions, and observations that help the model reason and reach its final answer. "
    #     left_inst = st.markdown(left_inst)

    #     right_inst = st.markdown("On the right, you can edit the AI model's thought or action anywhere in the reasoning chain.")
    #     right_inst_details = st.markdown(''' 
    #     - If you edit a thought and submit it, the action will be automatically updated by the AI. 
    #     - If you edit an action and submit it, the observation will be automatically updated. 
    #     - If you edit AI's thought or action at step $i$, all the steps at $i+1$ and after will be gone. You can then “Update the AI model's output” to complete the reasoning chain and obtain a new answer. ''')

    # else:
    #     raise NotImplementedError
    
    note = st.markdown(":red[Note that you should make your decision based ONLY on the **Observations** on this interface. You will reach wrong answers if you rely on information from Wikipedia or ChatGPT.]")
    ex_str = st.markdown("You can find examples for SUPPORTS, REFUTES, and NOT ENOUGH INFO below.")
    expander = st.expander("Examples:", expanded=True)
    
    examples = load_examples()
    for k, ex in examples.items():
        expander.markdown(f"#### {k}")
        expander.write(ex['claim'])
        model_output = ex['steps']
        for i, step_str in enumerate(model_output):
            keywords = ['thought', 'action', 'observation']
            if i == len(model_output) - 1:
                keywords = ['thought', 'action']

            if st.session_state.condition.find("hai-answer") > -1:
                # step_container = expander.chat_message("user")
                step_container = expander.container()
                keywords = ["action", "observation"]
            else:
                step_container = expander.chat_message("assistant")
            

            for kw in keywords:
                if len(step_str[kw]) == 0:
                    continue
                if st.session_state.condition.find("hai-answer") > -1:
                    content_str = step_str[kw]
                else:
                    content_str = f"{kw[0].upper()+kw[1:]} {i+1}: " + step_str[kw]

                if kw == "observation":
                    expander.chat_message("user", avatar="🌐").write(content_str)

                elif kw == "action":
                    step_container.text_input("", content_str, label_visibility="collapsed", disabled=True)
                else:
                    step_container.text_area("", content_str, label_visibility="collapsed", disabled=True)
        expander.divider()
    if "instruction_done" not in st.session_state:
        st.session_state["instruction_done"] = False

    def click_next():
        st.session_state['instruction_done'] = True
        
    if not st.session_state['instruction_done']:
        N = 2*10
        for secs in range(N,0,-1):
            mm, ss = secs//60, secs%60
            ph.metric("", f"{mm:02d}:{ss:02d}")
            time.sleep(1)
    next = st.button("Next", on_click=click_next)
    if st.session_state['instruction_done']:
        st.session_state.page = "main_study"
        st.rerun()
