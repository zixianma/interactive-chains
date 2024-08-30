import streamlit as st
import json

@st.cache_data
def load_examples():
    examples_file = 'data/examples.json'
    with open(examples_file, 'r') as f:
        examples = json.load(f)
    return examples

def instruction():
    st.title("Task Instruction")
    st.session_state.condition =  "I. hai-regenerate" #, "D. hai-static-chain", "C. hai-answer""E. hai-human-thought", "F. hai-human-action", "G. hai-mixed", "H. hai-update", "I. hai-regenerate"
    task_instruction = st.session_state.condition

    st.subheader("Please read the task instructions below carefully before proceeding.")
    goal = st.markdown("In this study, you will decide with the help of an AI model if there is evidence in the **Observation** that SUPPORTS or REFUTES a **Claim**, or if there is NOT ENOUGH INFORMATION.")
    definitions = st.markdown("""An **Observation** is some text returned by an **Action**, which includes *Search*, *Lookup* and *Finish*.""")
                  
    action_definitions = st.markdown('''
    - The *Search* action searches for the document that's the most related to the keyword you enter. 
    - The *Lookup* action finds a text in the last document found by Search or returns “no more results” if the text is not found. 
    - The *Finish* action submits one of the three answers: SUPPORTS, REFUTES, or NOT ENOUGH INFO about the claim.''')
    
    if st.session_state.condition == "C. hai-answer":
        left_inst = "On the left, you are given the AI model's suggested answer, which may be incorrect."
        left_inst = st.markdown(left_inst)

        right_inst = "On the right, you can perform either a Search or Lookup action to gather information about this claim and verify the AI's answer. "
        right_inst = st.markdown(right_inst)
    elif st.session_state.condition == "D. hai-static-chain":
        left_inst = "On the left, you are given the AI model's suggested answer along with its reasoning chain, which may be incorrect. "
        left_inst += "A reasoning chain is a list of thoughts, actions, and observations that help the model reason and reach its final answer. "
        left_inst = st.markdown(left_inst)

        right_inst = "On the right, you can perform either a Search or Lookup action to gather information about this claim and verify the AI's answer. "
        right_inst = st.markdown(right_inst)
        
    elif st.session_state.condition == "I. hai-regenerate":
        left_inst = "On the left, you are given the AI model's suggested answer along with its reasoning chain, which may be incorrect. "
        left_inst += "A reasoning chain is a list of thoughts, actions, and observations that help the model reason and reach its final answer. "
        left_inst = st.markdown(left_inst)

        right_inst = st.markdown("On the right, you can edit the AI model's thought or action anywhere in the reasoning chain.")
        right_inst_details = st.markdown(''' 
        - If you edit a thought and submit it, the action will be automatically updated by the AI. 
        - If you edit an action and submit it, the observation will be automatically updated. 
        - If you edit AI's thought or action at step $i$, all the steps at $i+1$ and after will be gone. You can then “Update the AI model's output” to complete the reasoning chain and obtain a new answer. ''')

    else:
        raise NotImplementedError
    
    note = st.markdown(":red[Note that you should make your decision based ONLY on the **Observations** on this interface. You will reach wrong answers if you rely on information from Wikipedia or ChatGPT.]")
    ex_str = st.markdown("You can find examples for SUPPORTS, REFUTES, and NOT ENOUGH INFO below.")
    expander = st.expander("Examples:", expanded=True)
    
    examples = load_examples()
    for k, ex in examples.items():
        expander.markdown(f"#### {k}")
        model_output = ex['steps']
        for i, step_str in enumerate(model_output):
            step_container = expander.chat_message("assistant")
            
            keywords = ['thought', 'action', 'observation']
            if i == len(model_output) - 1:
                keywords = ['thought', 'action']


            for kw in keywords:
                if st.session_state.condition == "C. hai-answer":
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