import streamlit as st
from PIL import Image

def end_tutorial():
    st.title("Congrats! You've finished all the questions.")

    st.markdown("### :red[IMPORTANT! Please follow the steps below to end your screen recording and save it. You will need to upload the recording at the end to complete the study.]")

    container = st.container(border=True)
    
    _, cent_col, _ = container.columns([2, 8, 2])
    record_screenshots = ["data/images/stop-record-1.png", "data/images/stop-record-2.png"]

    for i in range(len(record_screenshots)):
        image_path = record_screenshots[i]
        image = cent_col.image(image_path, caption=f"Step {i+1}", use_column_width=True)
    
    left_col, _, right_col = st.columns([2, 8, 2])
    next = right_col.button("Next", use_container_width=True)
    if next:
        st.session_state.page = "survey"
        st.rerun()


def begin_tutorial():
    
    condition2screenshots = {
                                "C. hai-answer": ["data/images/hai-answer-1.png", "data/images/hai-answer-2.png", "data/images/hai-answer-3.png", "data/images/hai-answer-4.png"], 
                                "D. hai-static-chain": ["data/images/hai-static-chain-1.png", "data/images/hai-static-chain-2.png", "data/images/hai-static-chain-3.png", "data/images/hai-static-chain-4.png"], 
                                "I. hai-regenerate": ["data/images/hai-regenerate-1.png", "data/images/hai-regenerate-2.png", "data/images/hai-regenerate-3.png", "data/images/hai-regenerate-4.png", "data/images/hai-regenerate-5.png"]
                            }
    record_screenshots = ["data/images/screen-record-1.png", "data/images/screen-record-2.png", "data/images/screen-record-3.png",]
    if 'condition2screenshots' not in st.session_state:
        st.session_state['condition2screenshots'] = condition2screenshots
    screenshots = condition2screenshots[st.session_state.condition]
    total_num_screenshots = len(screenshots) + 1
    num_tutorial_screenshots = len(screenshots)

    if "tutorial_idx" not in st.session_state:
        st.session_state["tutorial_idx"] = 0
    if "next_step" not in st.session_state:
        st.session_state["next_step"] = False
    if "prev_step" not in st.session_state:
        st.session_state["prev_step"] = False
    
    # print(st.session_state["tutorial_idx"], st.session_state["prev_step"], st.session_state["next_step"])
    # Create a placeholder for dynamic content
    st.title("Tutorial")
    if st.session_state['tutorial_idx'] < num_tutorial_screenshots:
    
        st.subheader("Here's a step-by-step tutorial on how to use the interface.")
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
    else:
        st.markdown("### :red[IMPORTANT! It's recommended to complete the study in one setting. Please only refresh the page if you have to. Now, please follow the steps below to start a recording of your screen. You will need to upload the recording at the end to complete the study.]")
        
    warning = st.empty()
    placeholder = st.empty()
    
    def click_next():
        st.session_state["next_step"] = True
    
    def click_prev():
        st.session_state["prev_step"] = True
    
    if st.session_state["next_step"]:
        if st.session_state["tutorial_idx"] == total_num_screenshots - 1:
            # st.warning("You're at the end of all examples. There is no next example.", icon="⚠️")
            st.session_state.page = "main_study" # "end_tutorial" # 
        else:
            st.session_state["tutorial_idx"] += 1
            st.session_state["next_step"] = False
        st.rerun()

    if st.session_state["prev_step"]:
        if st.session_state["tutorial_idx"] == 0:
            warning.warning("You're at the first step. There is no previous step.", icon="⚠️")
            st.session_state["prev_step"] = False
        else:
            st.session_state["tutorial_idx"] -= 1
            st.session_state["prev_step"] = False
            st.rerun()
    # Control which set of questions to display
    container = placeholder.container(border=True)
    if st.session_state['tutorial_idx'] < num_tutorial_screenshots:
        _, cent_col, _ = container.columns([1, 10, 1])
        image_path = screenshots[st.session_state["tutorial_idx"]]
        image = cent_col.image(image_path, caption=f"Step {st.session_state['tutorial_idx']+1}", use_column_width=True)
    else:
        _, cent_col, _ = container.columns([2, 8, 2])
        for i in range(len(record_screenshots)):
            image_path = record_screenshots[i]
            image = cent_col.image(image_path, caption=f"Step {i+1}", use_column_width=True)
    left_col, _, right_col = st.columns([2, 8, 2])
    prev = left_col.button("Prev", on_click=click_prev, use_container_width=True)
    next = right_col.button("Next", on_click=click_next, use_container_width=True)

    
