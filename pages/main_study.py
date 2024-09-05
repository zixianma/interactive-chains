import streamlit as st
import openai
from openai import OpenAI
import json
import os
import wikienv, wrappers
import requests
import pandas as pd
from streamlit_float import *
import re
import gspread
from google.oauth2.service_account import Credentials
import toml
import random
from datetime import datetime
import time
import pages.utils.logger as logger

# st.set_page_config(layout="wide")
float_init(theme=True, include_unstable_primary=False)

# @st.cache_data
def step(env, action):
    attempts = 0
    while attempts < 10:
        try:
            return env.step(action)
        except requests.exceptions.Timeout:
            attempts += 1

# @st.cache_data
def llm(messages, stop=["\n"]):
    client = OpenAI(api_key=st.secrets.openai_api_key.key)

    response = client.chat.completions.create(
      model="gpt-4o",
      messages=messages,
      temperature=0,
        max_tokens=100,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=stop
    )
    return response.choices[0].message.content


@st.cache_data
def load_model_outputs():
    # df = pd.read_json("data/fever_data_with_questions.jsonl", lines=True)
    # q_id2output = {}
    # for _, row in df.iterrows():
    #     q_id = row['question_idx']
        
    #     model_output = row['all_steps']
    #     new_steps = []
    #     for i, step_str in enumerate(model_output):
    #         step_str = process_model_output(step_str, final=False) # (i == len(model_output) -1)
    #         thought_str = get_part_from_step(step_str, "Thought", "Action").strip()
    #         action_str = get_part_from_step(step_str, "Action", "Observation").strip()
    #         obs_str = get_part_from_step(step_str, "Observation", "\n").strip()
    #         new_step = {"thought": thought_str, "action": action_str, "observation": obs_str}
    #         new_steps.append(new_step)

    #     q_id2output[q_id] = new_steps
    # with open('qid2output.json', 'w') as file:
    #     json.dump(q_id2output, file, indent=4)
    with open('data/qid2output.json', 'r') as file:
        q_id2output = json.load(file)
    int_q_id2output = {int(k): v for k, v in q_id2output.items()}
    return int_q_id2output

def get_model_output(output_df, idx):
    output = output_df[output_df['question_idx'] == idx].iloc[0]
    return output['all_steps']

@st.cache_data
def process_model_output(step_str, final=False):
    for kw in ['Action', 'Observation']:
        start_idx = step_str.find(kw)
        # if step_str[start_idx-1] != "\n":
        if final and kw == "Observation":
            step_str = step_str[:start_idx]
        else:
            step_str = step_str[:start_idx] + "\n" + step_str[start_idx:]
    return step_str

@st.cache_data
def get_part_from_step(step_str, kw, stop="\n"):
    start_idx = step_str.find(kw)
    if start_idx > -1:
        step_str = step_str[start_idx:]
        if not stop or kw == "Observation":
            end_idx = len(step_str)
        else:
            end_idx = step_str.find(stop) 
        if end_idx > -1:
            return step_str[:end_idx] # start_idx+
    return ""

@st.cache_data
def extract_final_answer(model_output):
    last_step_str = model_output[-1]['action']
    # last_step_str = process_model_output(last_step_str, final=True)
    start = max(last_step_str.find("["), 0)
    end = last_step_str.find("]")
    final_ans = last_step_str[start+1:end if end > 0 else len(last_step_str)]
    return final_ans

def display_left_column(env, idx, left_column, condition):
    # question = env.reset(idx=idx)
    # left_column.text(f"You're at {st.session_state.count + 1} / 30 questions.")
    # left_column.subheader(question)
    # if 'question' not in st.session_state[idx]:
    #     st.session_state[idx]['question'] = question
    if condition == "C. hai-answer":
        left_column.subheader("AI model's output:")
        # model_output = get_model_output(model_outputs, idx)
        model_output = st.session_state.model_outputs[idx]
        final_ans = extract_final_answer(model_output)
        # left_column.divider()
        container = left_column.chat_message("assistant")
        container.write(f"AI answer: {final_ans}")

    elif condition != "A. human":
        # model_output = get_model_output(model_outputs, idx)
        model_output = st.session_state.model_outputs[idx]
        expander = left_column.expander("#### AI model's output", expanded=True)
        for i, step_str in enumerate(model_output):
            step_container = expander.chat_message("assistant")
            # step_str = process_model_output(step_str, final=(i == len(model_output) -1))
            keywords = ['thought', 'action', 'observation']
            if i == len(model_output) - 1:
                keywords = ['thought', 'action']
            for kw in keywords:
                if kw == "observation":
                    expander.chat_message("user", avatar="🌐").write(step_str[kw])
                elif kw == "action":
                    # step_container.write(step_str[kw])
                    step_container.text_input("", step_str[kw], label_visibility="collapsed", disabled=True, key=f"display {kw} {i}")
                else:
                    step_container.text_area("", step_str[kw], label_visibility="collapsed", disabled=True, key=f"display {kw} {i}")
            # left_column.button("Edit this step", key=f"update {i}")

            expander.divider()
    return left_column

@st.cache_data
def validate_action_str_format(action_str):
    pattern = r"(search|lookup)\[.+\]"
    match = re.fullmatch(pattern, action_str)
    return match is not None

# def add_thought_step(i, prompt, right_column): 
#     right_column.write(f"Step {i}")
#     thought = ""

#     thought = right_column.text_area("Enter your thought:", key=f"thought {i}")
    
#     finish_t = right_column.button("Finish", key=f"finish thought {i}")
#     # right_column.write("PROMPT:\n" + prompt + thought + f"\nAction {i}:")
#     if finish_t:
#         action = llm(prompt + thought + f"\nAction {i}:", stop=[f"\nObservation {i}:"])
#         obs, r, done, info = step(env, action[0].lower() + action[1:])

#         obs = obs.replace('\\n', '')
#         step_str = f"Thought {i}: {thought}\nAction {i}: {action}\nObservation {i}: {obs}\n"
#         right_column.write(f"STEP:\n{step_str}")
#         prompt += step_str

#     return prompt, right_column

@st.cache_data
def format_action_str(action):
    pattern = r'Action\s*\d*:'
    match = re.search(pattern, action)
    if match:
        start_idx = match.end()
        action = action[start_idx+1:].strip()
    if len(action) >= 2:
        return action[0].lower() + action[1:]
    else:
        return "none"

@st.cache_data
def parse_action_into_parts(action):
    start = action.rfind(":") + 1 # +1 so it's min 0 even if not found
    mid = action.find("[")
    end = action.find("]") 
    # end = len(action) if end == -1 else end
    action_dict = {"label": action[:start].strip(), "option": action[start:mid].strip(), "input": action[mid+1:end]}
    # action_arg = action[start+1:end if end > 0 else len(action)]
    return action_dict

@st.cache_data
def turn_step_dict_into_msg(step_dict):
    msg = "\n".join([step_dict['thought'], step_dict['action'], step_dict['observation']])
    return msg

# @st.cache_data
def format_model_output_into_msgs_for_idx(idx):
    curr_msgs = [{"role": "user", "content": st.session_state['task_prompt'] + st.session_state[idx]['question'] + "\n"}]     
    curr_msgs += [{"role": "assistant", "content": turn_step_dict_into_msg(step_dict)} for step_dict in st.session_state[idx]['curr_model_output']]
    return curr_msgs


def display_right_column(env, idx, right_column, condition):     
    def click_submit(answer):
        if st.session_state[f'{st.session_state.condition}_answer_{idx}'] is None: # answer
            right_column.warning("Please select an answer before submitting.")
        else:
            st.session_state[idx]['answer'] = answer
            st.session_state[idx]['submitted'] = True
            st.session_state[idx]['disabled_submit'] = True       
    # env = st.session_state['env']
    question = env.reset(idx=idx) # st.session_state[idx]['question'] # 
    
    # make session state dict per question
    if f"last_search_{idx}" not in st.session_state[idx]:
        st.session_state[idx][f"last_search_{idx}"] = None
    if f"last_lookup_{idx}" not in st.session_state[idx]:
        st.session_state[idx][f"last_lookup_{idx}"] = None
    if f"start_time_{idx}" not in st.session_state[idx]:
        st.session_state[idx][f"start_time_{idx}"] = datetime.now()
    if 'observations' not in st.session_state[idx]:
        st.session_state[idx]['observations'] = []
    if 'actions' not in st.session_state[idx]:
        st.session_state[idx]['actions'] = []

    if condition == "A. human" or condition == "C. hai-answer" or condition == "D. hai-static-chain":
        # right_column.subheader("Perform a Search or Lookup action:")
        right_column.markdown("#### Perform a Search or Lookup action:")
       
        search_query = right_column.text_input('Search', key=f"search {idx}")
        if search_query:
            if search_query != st.session_state[idx].get(f"last_search_{idx}"):
                st.session_state[idx][f"last_search_{idx}"] = search_query
                st.session_state[idx]['actions'].append(f"search[{search_query}]")

            obs, r, done, info = step(env, f"search[{search_query}]")
            # right_column.write(obs)
            right_column.chat_message("user", avatar="🌐").write(obs)
            st.session_state[idx]['observations'].append(obs)

        lookup_query = right_column.text_input('Lookup', key=f"lookup {idx}")

        if lookup_query:
            if lookup_query != st.session_state[idx].get(f"last_lookup_{idx}"):
                st.session_state[idx][f"last_lookup_{idx}"] = lookup_query
                st.session_state[idx]['actions'].append(f"lookup[{lookup_query}]")

            obs, r, done, info = step(env, f"lookup[{lookup_query}]")
            # right_column.write(obs)
            right_column.chat_message("user", avatar="🌐").write(obs)
            st.session_state[idx]['observations'].append(obs)

        form = right_column.form(key='user-form')
        answer = form.radio(
            "Select and submit your final answer (You can only submit once):",
            ["SUPPORTS", "REFUTES", "NOT ENOUGH INFO"],
            index=None,
            key=f"{st.session_state.condition}_answer_{idx}" # this is so the radio button clears it last saved answer because this is saved in session_state
        )
        
        if "submitted" not in st.session_state[idx]:
            st.session_state[idx]['submitted'] = False
        if "disabled_submit" not in st.session_state[idx]:
            st.session_state[idx]['disabled_submit'] = False
        # def click_submit():
        #     st.session_state[idx]['submitted'] = True
        #     st.session_state[idx]['disabled_submit'] = True

        submit = form.form_submit_button('Submit', on_click=click_submit, args=(answer, ), disabled = st.session_state[idx]['disabled_submit'])
        if st.session_state[idx]['submitted']:
            end_time = datetime.now()
            elapsed_time = (end_time - st.session_state[idx][f"start_time_{idx}"]).total_seconds()
            st.session_state[idx]['actions'].append(f"finish[{answer}]")
            # log data
            logger.write_to_user_sheet([st.session_state.username, idx, len(st.session_state[idx]['actions']), str(st.session_state[idx]['actions']), str(st.session_state[idx]['observations']), answer, st.session_state.condition, elapsed_time])
            obs, r, done, info = step(env, f"finish[{answer}]")
            st.session_state.user_data["last question idx done"] = idx
            # st.session_state['answer'] = answer
            right_column.write(f'Submitted: {answer}')
            if idx in st.session_state['train_ids']:
                if r == 1:
                    output = "Your answer is right! :)\n"
                else:
                    output = f"Your answer is wrong :( The correct answer is {info['gt_answer']}.\n"
                if idx in st.session_state['train_id2explanation']:
                    expl = st.session_state['train_id2explanation'][idx]
                    output += expl
                right_column.write(f'{output}')
            st.session_state[idx]['submitted'] = False
    else:
        
        if condition.find("thought") > -1:
            right_column.subheader("Interact with the AI model by entering your thought (actions will be generated by AI and given to you):")
            # interact = right_column.button("Interact with AI to modify thoughts/actions", key="interact with thought")
            # if interact:
            if "turn_id" not in st.session_state[idx]:
                st.session_state[idx]["turn_id"] = 1
            if "messages" not in st.session_state[idx]:
                st.session_state[idx]["messages"] = [{"role": "assistant", "content": st.session_state['task_prompt'] + question + "\n"}]
                
            init_prompt = right_column.chat_input(placeholder="Enter your thought:")
            with st.container():
                for msg in st.session_state[idx]["messages"][1:]:
                    content = msg['content']
                    if msg['content'].find("Observation") > -1:
                        right_column.chat_message(msg["role"], avatar="🌐").write(msg["content"])
                    else:
                        right_column.chat_message(msg["role"]).write(msg["content"])
                
                if prompt := init_prompt:
                    # button_b_pos = "0rem"
                    # button_css = float_css_helper(width="2.2rem", bottom=button_b_pos, transition=0)
                    # float_parent(css=button_css)
                    content = f"Thought {st.session_state[idx]['turn_id']}: " + prompt # + f"\nAction {st.session_state[idx]['turn_id']}:"
                    st.session_state[idx]["messages"].append({"role": "user", "content": content})
                    right_column.chat_message("user").write(content)
                    action = llm(st.session_state[idx]["messages"], stop=["Observation"])

                    content = action
                    st.session_state[idx]["messages"].append({"role": "assistant", "content": content})
                    right_column.chat_message("assistant").write(content)
                    action = format_action_str(action)
                    # pattern = r'Action\s\d+:'
                    # match = re.search(pattern, action)
                    # if match:
                    #     start_idx = match.end()
                    #     action = action[start_idx+1:].strip()
                    obs, r, done, info = step(env, action)
                    obs = obs.replace('\\n', '')
                    
                    if not done:
                        content = content = f"Observation {st.session_state[idx]['turn_id']}: {obs}\n"
                        st.session_state[idx]["messages"].append({"role": "user", "content": content})
                        right_column.chat_message("user", avatar="🌐").write(content)
                        st.session_state[idx]["turn_id"] += 1

        elif condition.find("action") > -1:
            right_column.subheader("Interact with the AI model by entering your action (thoughts will be generated by AI and given to you):")
            # interact = right_column.button("Interact with AI to modify thoughts/actions", key="interact with action")
            # if interact:
            if "turn_id" not in st.session_state[idx]:
                st.session_state[idx]["turn_id"] = 0
            if "messages" not in st.session_state[idx]:
                st.session_state[idx]["messages"] = [{"role": "user", "content": st.session_state['task_prompt'] + question}]

            init_prompt = right_column.chat_input(placeholder="Enter your action (e.g. search[query], lookup[text]):")
            # button_b_pos = "0rem"
            # button_css = float_css_helper(width="2.2rem", bottom=button_b_pos, transition=0)
            # float_parent(css=button_css)
            with st.container():
                for msg in st.session_state[idx]["messages"][1:]:
                    if msg['content'].find("Observation") > -1:
                        right_column.chat_message(msg["role"], avatar="🌐").write(msg["content"])
                    else:
                        right_column.chat_message(msg["role"]).write(msg["content"])

                if st.session_state[idx]["turn_id"] == 0:
                    # last_msg = st.session_state[idx]["messages"][-1]
                    # last_msg['content'] += f"\nThought {st.session_state[idx]['turn_id']+1}:" # [:-1] + [last_msg]
                    thought = llm(st.session_state[idx]["messages"], stop=["Action"])
                    # print("init thought:", thought)
                    content = f"{thought}\n" # Thought {st.session_state[idx]['turn_id']+1}: 
                    st.session_state[idx]["messages"].append({"role": "assistant", "content": content})
                    right_column.chat_message("assistant").write(content)
                    st.session_state[idx]["turn_id"] += 1

                if prompt := init_prompt:
                    wrong_format = None
                    if not validate_action_str_format(prompt):
                        wrong_format = right_column.warning("There's some issue with the entered action  . Please make sure it is either search[query] or lookup[text] and try again.", icon="⚠️")
                    if not wrong_format:
                        # thought = llm(st.session_state[idx]["messages"], stop=[f"Action:"])
                        # st.session_state[idx]["messages"].append({"role": "assistant", "content": thought})
                        # right_column.chat_message("assistant").write(thought)
                        # if prompt.find("search") > -1 or prompt.find("lookup") > -1:
                        action = prompt
                        content = f"Action {st.session_state[idx]['turn_id']}: {action}\n"
                        st.session_state[idx]["messages"].append({"role": "user", "content": content})
                        right_column.chat_message("user").write(content)
                        obs, r, done, info = step(env, action[0].lower() + action[1:])
                        
                        obs = obs.replace('\\n', '')

                        if not done:
                            content = f"Observation {st.session_state[idx]['turn_id']}: {obs}\n"
                            st.session_state[idx]["messages"].append({"role": "user", "content": content})
                            right_column.chat_message("user", avatar="🌐").write(content)
                            st.session_state[idx]["turn_id"] += 1
                            
                            # last_msg = st.session_state[idx]["messages"][-1]
                            # last_msg['content'] += f"\nThought {st.session_state[idx]['turn_id']}:"
                            # thought = llm(st.session_state[idx]["messages"][:-1] + [last_msg], stop=["Action"])
                            thought = llm(st.session_state[idx]["messages"], stop=["Action"])
                            content = f"{thought}\n" # Thought {st.session_state[idx]['turn_id']}: 
                            st.session_state[idx]["messages"].append({"role": "assistant", "content": content})
                            right_column.chat_message("assistant").write(content)

        elif condition.find("mixed") > -1:
            right_column.subheader("Interact with the AI model by entering your thought/action:")
            if "turn_id" not in st.session_state[idx]:
                st.session_state[idx]["turn_id"] = 1
            if "messages" not in st.session_state[idx]:
                st.session_state[idx]["messages"] = [{"role": "user", "content": st.session_state['task_prompt'] + question}]
            call_ai = right_column.button("Generate next thought or action with AI", key="call ai")
            init_prompt = right_column.chat_input(placeholder="Or, enter your thought or action (e.g. search[query], lookup[text]):")
            with st.container():
                for msg in st.session_state[idx]["messages"][1:]:
                    if msg['content'].find("Observation") > -1:
                        right_column.chat_message(msg["role"], avatar="🌐").write(msg["content"])
                    else:
                        right_column.chat_message(msg["role"]).write(msg["content"])

                last_msg = st.session_state[idx]['messages'][-1]['content']
                # print("LAST MSG:", last_msg)
                if prompt := init_prompt:
                    if len(st.session_state[idx]['messages']) == 1 or last_msg.find("Thought") == -1: # user entering a thought
                        content = prompt # + f"\nAction {st.session_state[idx]['turn_id']}:"
                        st.session_state[idx]["messages"].append({"role": "user", "content": content})
                        right_column.chat_message("user").write(content)
                        
                    else: # user entering an action
                        action = prompt
                        content = f"Action {st.session_state[idx]['turn_id']}: {action}\n"
                        st.session_state[idx]["messages"].append({"role": "user", "content": content})
                        right_column.chat_message("user").write(content)
                        obs, r, done, info = step(env, action[0].lower() + action[1:])
                        
                        obs = obs.replace('\\n', '')

                        if not done:
                            content = f"Observation {st.session_state[idx]['turn_id']}: {obs}\n"
                            st.session_state[idx]["messages"].append({"role": "user", "content": content})
                            right_column.chat_message("user", avatar="🌐").write(content)
                            st.session_state[idx]["turn_id"] += 1
                            
                elif call_ai:
                    if len(st.session_state[idx]['messages']) == 1 or last_msg.find("Thought") == -1: # generate next thought
                        thought = llm(st.session_state[idx]["messages"], stop=["Action"])
                        content = f"{thought}\n"
                        st.session_state[idx]["messages"].append({"role": "assistant", "content": content})
                        right_column.chat_message("assistant").write(content)

                    elif last_msg.find("Action") == -1: # generate next action
                        action = llm(st.session_state[idx]["messages"], stop=["Observation"])

                        content = action
                        st.session_state[idx]["messages"].append({"role": "assistant", "content": content})
                        right_column.chat_message("assistant").write(content)

                        # pattern = r'Action\s\d+:'
                        # match = re.search(pattern, action)
                        # if match:
                        #     start_idx = match.end()
                        #     action = action[start_idx+1:].strip()
                        action = format_action_str(action)
                        obs, r, done, info = step(env, action)
                        obs = obs.replace('\\n', '')
                        
                        if not done:
                            content = content = f"Observation {st.session_state[idx]['turn_id']}: {obs}\n"
                            st.session_state[idx]["messages"].append({"role": "user", "content": content})
                            right_column.chat_message("user", avatar="🌐").write(content)
                            st.session_state[idx]["turn_id"] += 1
        elif condition.find("update") > -1:
            # all_steps_dict = {"thought": [], "action": [], "observation": [], "delete": []}
            # valid_steps = {}
            right_column.subheader("Edit AI's reasoning chain and get a new answer:")
            model_output =  st.session_state.model_outputs[idx][:-1]
            if 'curr_model_output' not in st.session_state[idx]:
                st.session_state[idx]['curr_model_output'] = model_output
            if 'curr_num_steps' not in st.session_state[idx]:
                st.session_state[idx]['curr_num_steps'] = len(model_output)

            new_model_output = []
            for i, step_dict in enumerate(model_output):
                # step_str = process_model_output(step_str, final=False) #(i == len(model_output) -1)
                obs_str = step_dict['observation'] #get_part_from_step(step_str, "Observation", "\n").strip()
                thought_str = step_dict['thought'] # get_part_from_step(step_str, "Thought", "Action").strip()
                action_str = step_dict['action'] # get_part_from_step(step_str, "Action", "Observation").strip()
                # if i not in valid_steps:
                #     valid_steps[i] = True
                # right_column.chat_message("assistant").write(before_obs_str) # , avatar="🧑‍💻"
                # right_column.header("🤖")
 
                step_container = right_column.chat_message("assistant") # right_column.container(border=False)
                if f"step {i} deleted" not in st.session_state or not st.session_state[idx][f"step {i} deleted"]:
                    thought_input = step_container.text_area("", thought_str, label_visibility="collapsed", key=f"thought {i}")
                    action_input = step_container.text_input("", action_str, label_visibility="collapsed", key=f"actiin {i}")
                    
                    if action := action_input and action_input != action_str:
                        action = format_action_str(action_input)
                        obs, r, done, info = step(env, action)
                        obs_str = obs.replace('\\n', '')   

                    if len(obs_str) > 0: # it's possible that the extraction on the original step str failed
                        # obs_container = right_column.chat_message("user", avatar="🌐")
                        right_column.chat_message("user", avatar="🌐").write(obs_str)
                        # step_container.text_area("🌐", obs_str, disabled=True, label_visibility="visible", key=f"observation {i}")

                    if f"step {i} deleted" not in st.session_state:
                        st.session_state[idx][f"step {i} deleted"] = False

                    def click_button(i):
                        st.session_state[idx][f"step {i} deleted"] = True

                    delete = right_column.button("Delete this step",  key=f"delete {i}", on_click=click_button, args=(i, )) # 
                    new_model_output.append(step_dict)

                else:
                    if f"delete {i}" not in st.session_state:
                        st.session_state[f"delete {i}"] = True
            
            step_num = st.session_state[idx]['curr_num_steps']
            if f"step_{step_num}_added" not in st.session_state:
                st.session_state[idx][f"step_{step_num}_added"] = False

            def click_button(step_num):
                st.session_state[idx][f"step_{step_num}_added"] = True
                st.session_state[idx]['curr_num_steps'] += 1

            # new_step_container = right_column.container(border=False) # right_column.empty()
            for j in range(len(model_output), step_num):
                new_step_container = right_column.chat_message("assistant")
                # print(j, st.session_state[idx][f"step_{j}_added"])
                if st.session_state[idx][f"step_{j}_added"]:

                    new_thought_input = new_step_container.text_area("🤖", "Thought:", label_visibility="collapsed", key=f"thought {j}")
                    new_action_input = new_step_container.text_input("", "Action:", label_visibility="collapsed", key=f"action {j}")

                    new_step = {"thought": new_thought_input, "action": new_action_input, "observation": ""}
                    # new_action = "Action:"
                    if new_action := new_action_input and new_action_input != "Action:":
                        new_action = format_action_str(new_action_input)
                        new_obs, r, done, info = step(env, new_action)
                        new_obs_str = new_obs.replace('\\n', '')  
                        new_obs = new_step_container.text_area("🌐", new_obs_str, disabled=True, label_visibility="collapsed", key=f"observation {j}")
                        # new_step["action"] = new_action_input
                        new_step["observation"] = new_obs_str
                    new_model_output.append(new_step)
            add = right_column.button("Add step", key=f"add {step_num}", on_click=click_button, args=(step_num, ))
            
            st.session_state['curr_model_output'] = new_model_output

            num_steps = len(st.session_state['curr_model_output'])
            call_ai = right_column.button("Get AI's suggested answer", key="call ai")
            curr_msgs = [{"role": "user", "content": st.session_state['task_prompt'] + st.session_state[idx]['question']}]
            curr_msgs += [{"role": "assistant", "content": "\n".join([step_dict['thought'], step_dict['action'], step_dict['observation']])} for step_dict in new_model_output]
            curr_msgs.append({"role": "user", "content": f"Thought {num_steps+1}: Conclude with the final answer\n"})
            if call_ai:
                final_thought_action = llm(curr_msgs, stop=["Observation"])
                step_container = right_column.container(border=False)
                
                final = step_container.text_area("🤖", final_thought_action, label_visibility="collapsed", key=f"final answer", disabled=True)
            
        elif condition.find("regenerate") > -1:
            COOLDOWN_TIME = 8 # ADJUST HERE
            # right_column.subheader("Edit any thought or action and update AI's output:")
            right_column.markdown("#### Edit any thought or action and update AI's output:")
            model_output =  st.session_state.model_outputs[idx][:-1]
            if 'curr_model_output' not in st.session_state[idx]:
                st.session_state[idx]['curr_model_output'] = model_output
            if 'curr_num_steps' not in st.session_state[idx]:
                st.session_state[idx]['curr_num_steps'] = len(model_output)
            if "generate_next_step" not in st.session_state[idx]:
                st.session_state[idx]["generate_next_step"] = False
            if "model_output_per_run" not in st.session_state[idx]:
                st.session_state[idx]["model_output_per_run"] = {0: st.session_state[idx]['curr_model_output']}
            if "ai_output_clicks" not in st.session_state[idx]:
                st.session_state[idx]["ai_output_clicks"] = 0
            if "last_ai_button_click_time" not in st.session_state[idx]:
                st.session_state[idx]["last_ai_button_click_time"] = 0
            if "changes" not in st.session_state[idx]:
                st.session_state[idx]["changes"] = 0
            if "thought_changed" not in st.session_state[idx]:
                st.session_state[idx]["thought_changed"] = {}
            if "action_changed" not in st.session_state[idx]:
                st.session_state[idx]["action_changed"] = {}

            new_model_output = []
            for i, step_dict in enumerate(st.session_state[idx]['curr_model_output']):
                obs_str = step_dict['observation'] 
                thought_str = step_dict['thought'] 
                # action_str = step_dict['action']
                action_dict = parse_action_into_parts(step_dict['action'])
                
                step_container = right_column.chat_message("assistant")
                
                thought_input = step_container.text_area("", thought_str, label_visibility="collapsed", key=f"thought {i}")
                thought_key = f"Changed thought {i + 1} to: {thought_input}"

                if thought := thought_input and thought_input != step_dict['thought'] and thought_key not in st.session_state[idx]["thought_changed"]:
                    st.session_state[idx]["thought_changed"][thought_key] = True
                    st.session_state[idx]["changes"] += 1
                    # st.session_state[idx]["actions"].append(thought_key)
                    # st.session_state[idx]["generate_next_step"] = False
                    curr_msgs = [{"role": "user", "content": st.session_state['task_prompt'] + st.session_state[idx]['question']}]
                    curr_msgs += [{"role": "assistant", "content": "\n".join([step_dict['thought'], step_dict['action'], step_dict['observation']])} for step_dict in model_output[:i]]
                    curr_msgs += [{"role": "user", "content": f"{thought_input}"}]
                    next_action = llm(curr_msgs, stop=["Observation"])
                    action_dict = parse_action_into_parts(next_action)
                    # break
                action_cols = step_container.columns([2, 2, 8])
                
                # action_label = action_cols[0].write('<div style="height: 30px; margin-left: 64px;">' + f"Action {i+1}:" + '</div>', unsafe_allow_html=True)

                # if i == len(st.session_state[idx]['curr_model_output']) - 1:
                all_action_options = ["Search", "Lookup", "Finish"]
                # else:
                #     all_action_options = ["Search", "Lookup"]
                try:
                    action_index = all_action_options.index(action_dict['option'][0].upper() + action_dict['option'][1:]) # 0 if action_dict['option'].lower() == "search" else 1
                except:
                    action_index = 0
                action_str = action_dict['input']
                
                action_dict['label'] = f"Action {i+1}: "
                print(action_dict)
                action_label = action_cols[0].text_input("", action_dict['label'], label_visibility="collapsed", disabled=True, key=f"action label {i}") #
                action_option = action_cols[1].selectbox("", all_action_options, label_visibility="collapsed", index=action_index, key=f"action choice {i}")
                action_input = action_cols[2].text_input("", action_str, label_visibility="collapsed", key=f"action input {i}")
                # action_input = step_container.text_input("", action_str, label_visibility="collapsed", key=f"action {i}")
                action_combined = f"{action_option[0].lower() + action_option[1:]}[{action_input}]"
                action_formatted = format_action_str(step_dict['action'])
                # print(step_dict['action'], action_formatted, action_combined)
                action_key = f"Changed action {i + 1} to: {action_option.lower()}: {action_input}"
                if action := action_input and action_combined != action_formatted and action_key not in st.session_state[idx]["action_changed"]: # action := action_input and  action := action_combined and 
                    st.session_state[idx]["changes"] += 1
                    st.session_state[idx]["action_changed"][action_key] = True
                    # st.session_state[idx]["actions"].append(action_key)
                    action = f"{action_option[0].lower() + action_option[1:]}[{action_input}]" # action_combined
                    obs, r, done, info = step(env, action)
                    obs_str = obs.replace('\\n', '')   
                    if done:
                        st.session_state[idx]["done"] = True
                        obs_str = f"Observation {i+1}: Done"
                    else:
                        st.session_state[idx]["done"] = False
                        obs_str = f"Observation {i+1}: {obs_str}"
                right_column.chat_message("user", avatar="🌐").write(obs_str)
                new_action_str = f"{action_label} {action_combined[0].upper() + action_combined[1:]}" # action_input
                new_model_output.append({"thought": thought_input, "action": new_action_str, "observation": f"{obs_str}"})

                if thought_input != step_dict['thought'] or action_combined != action_formatted: # action_input != step_dict['action']:
                    # st.session_state[idx]["generate_next_step"] = False
                    break

            st.session_state[idx]['curr_model_output'] = new_model_output
            print(f"model output: {model_output}")
            # print(f"thoughts in session state: {st.session_state[idx]['changed_thoughts'][st.session_state[idx]['ai_output_clicks']]}")
            num_steps = len(st.session_state[idx]['curr_model_output'])

            def click_button():
                current_time = time.time()
                if current_time - st.session_state[idx]["last_ai_button_click_time"] >= COOLDOWN_TIME:
                    st.session_state[idx][f"generate_next_step"] = True
                    st.session_state[idx]["ai_output_clicks"] += 1
                    st.session_state[idx]["last_ai_button_click_time"] = current_time
                else:
                    st.warning("Please do not spam this button.")
            
            current_time = time.time()
            disable_button = current_time - st.session_state[idx]["last_ai_button_click_time"] < COOLDOWN_TIME or st.session_state[idx]["submitted"]
            generate = right_column.button("Update AI's output", key=f"generate {num_steps+1}", on_click=click_button, disabled=disable_button)
            curr_msgs = format_model_output_into_msgs_for_idx(idx)
            if "curr_msgs" not in st.session_state[idx]:
                st.session_state[idx]['curr_msgs'] = curr_msgs
            
            print(st.session_state[idx]["generate_next_step"])
            print(curr_msgs != st.session_state[idx]['curr_msgs'])
            # print(curr_msgs[1:], '\n\n')
            # print(st.session_state[idx]['curr_msgs'][1:])
            if st.session_state[idx]["generate_next_step"] and curr_msgs != st.session_state[idx]['curr_msgs']: # generate (not st.session_state[idx]["done"]) 
                # container = right_column.container()
                # with container:
                with st.spinner('Wait for model to finish running...'):
                    for i in range(num_steps, 8):
                        new_thought_action = llm(curr_msgs, stop=["Observation"])
                        if len(new_thought_action.strip()) == 0:
                            print("try running with prefix..")
                            last_msg = curr_msgs[-1]['content']
                            print("last msg:", curr_msgs[-1])
                            action_exists = last_msg.find("Action") > -1
                            prefix_msg = [{"role": "user", "content": f"Thought {num_steps+1}:\n" if action_exists else f"Action {num_steps+1}:\n"}]
                            print("Prefix msg:", prefix_msg)
                            new_thought_action = llm(curr_msgs + prefix_msg, stop=["Observation"])

                        print("model output:", new_thought_action)
                        thought_str = get_part_from_step(new_thought_action, "Thought", "Action")
                        action_str = get_part_from_step(new_thought_action, "Action", None)
                        # new_thought = step_container.write(thought_str)
                        # new_action = step_container.write(action_str)
                        print("action str:", action_str)
                        action = format_action_str(action_str)
                        obs, r, done, info = step(env, action)
                        if not done:
                            obs_str = obs.replace('\\n', '')
                            obs_str = f"Observation {i+1}: {obs_str}"
                            new_step_dict = {"thought": thought_str, "action": action_str, "observation": obs_str}
                            curr_msgs.append({"role": "assistant", "content": turn_step_dict_into_msg(new_step_dict)})
                            st.session_state[idx]['curr_model_output'].append(new_step_dict)
                        else:
                            st.session_state[idx]["done"] = True
                            obs_str = f"Observation {i+1}: Done"
                            new_step_dict = {"thought": thought_str, "action": action_str, "observation": "Done"}
                            curr_msgs.append({"role": "assistant", "content": turn_step_dict_into_msg(new_step_dict)})
                            st.session_state[idx]['curr_model_output'].append(new_step_dict)
                            break
                    # turn off generate flag after a new output is generated
                    st.session_state[idx][f"generate_next_step"] = False
                st.session_state[idx]['model_output_per_run'][st.session_state[idx]["ai_output_clicks"]] = st.session_state[idx]['curr_model_output']
                st.session_state[idx]['curr_msgs'] = curr_msgs
                st.rerun()

        elif condition.find("control") > -1:
            right_column.subheader("Edit AI's thought/action and get a new answer:")
            model_output =  st.session_state.model_outputs[idx][:-1]
            if 'curr_model_output' not in st.session_state[idx]:
                st.session_state[idx]['curr_model_output'] = model_output
            if 'curr_num_steps' not in st.session_state[idx]:
                st.session_state[idx]['curr_num_steps'] = len(model_output)

            new_model_output = []
            for i, step_dict in enumerate(st.session_state[idx]['curr_model_output']):
                obs_str = step_dict['observation'] 
                thought_str = step_dict['thought'] 
                action_str = step_dict['action'] 
 
                step_container = right_column.chat_message("assistant") 
                thought_input = step_container.text_area("", thought_str, label_visibility="collapsed", key=f"thought {i}")
                update_action = step_container.button("Update action with AI", key=f"update_action_{i}")
                if thought := thought_input and thought_input != step_dict['thought'] and update_action: # thought_str
                    curr_msgs = [{"role": "user", "content": st.session_state['task_prompt'] + st.session_state[idx]['question']}]
                    curr_msgs += [{"role": "assistant", "content": "\n".join([step_dict['thought'], step_dict['action'], step_dict['observation']])} for step_dict in model_output[:i]]
                    curr_msgs += [{"role": "user", "content": f"{thought_input}"}]
                    next_action = llm(curr_msgs, stop=["Observation"])
                    action_str = next_action
                
                action_input = step_container.text_input("", action_str, label_visibility="collapsed", key=f"actiin {i}")
                update_obs = step_container.button("Update observation", key=f"update_obs_{i}")
                if action := action_input and action_input != step_dict['action'] and update_obs:
                    action = format_action_str(action_input)
                    obs, r, done, info = step(env, action)
                    obs_str = obs.replace('\\n', '')   
                    obs_str = f"Observation {i+1}: {obs_str}"
                
                # if len(obs_str) > 0: # it's possible that the extraction on the original step str failed
                right_column.chat_message("user", avatar="🌐").write(obs_str)
                new_model_output.append({"thought": thought_input, "action": action_input, "observation": f"{obs_str}"})

                if action_input != step_dict['action'] or thought_input != step_dict['thought']:
                    break
            st.session_state[idx]['curr_model_output'] = new_model_output
            num_steps = len(st.session_state[idx]['curr_model_output'])

            if "generate_next_step" not in st.session_state[idx]:
                st.session_state[idx]["generate_next_step"] = False
            def click_button():
                st.session_state[idx][f"generate_next_step"] = True
            
            generate = right_column.button("Generate the next step with AI", key=f"generate {num_steps+1}", on_click=click_button)
            curr_msgs = [{"role": "user", "content": st.session_state['task_prompt'] + st.session_state[idx]['question'] + "\n"}]
            
            curr_msgs += [{"role": "assistant", "content": "\n".join([step_dict['thought'], step_dict['action'], step_dict['observation']])} for step_dict in st.session_state[idx]['curr_model_output']]

            if st.session_state[idx]["generate_next_step"]: #generate:
                curr_msgs += [{"role": "user", "content": f"Thought {num_steps+1}:\n"}]
                # print("msgs before generate:", curr_msgs)
                step_container = right_column.chat_message("assistant") #right_column.container(border=False)
                new_thought_action = llm(curr_msgs, stop=["Observation"])
                print("model output:", new_thought_action)
                
                thought_str = get_part_from_step(new_thought_action, "Thought", "Action")
                action_str = get_part_from_step(new_thought_action, "Action", None)

                new_thought = step_container.write(thought_str)
                new_action = step_container.write(action_str)

                print("action str:", action_str)
                action = format_action_str(action_str)
                obs, r, done, info = step(env, action)
                if not done:
                    obs_str = obs.replace('\\n', '')   
                    right_column.chat_message("user", avatar="🌐").write(obs_str)
                    new_step_dict = {"thought": thought_str, "action": action_str, "observation": obs_str}
                else:
                    new_step_dict = {"thought": thought_str, "action": action_str, "observation": "Done"}
                st.session_state[idx]['curr_model_output'].append(new_step_dict)
                
                # new_step  = step_container.text_area("🤖", new_thought_action, label_visibility="collapsed", key=f"new step", disabled=True)
            
            call_ai = right_column.button("Get AI's final answer", key="call ai")
            if call_ai:
                
                num_steps = len(st.session_state[idx]['curr_model_output'])
                curr_msgs.append({"role": "user", "content": f"Thought {num_steps+1}: Conclude with the final answer\nAction {num_steps+1}:"})
                print("msgs before final answer:", curr_msgs[1:])
                final_thought_action = llm(curr_msgs, stop=["Observation"])
                print("final output:", final_thought_action)
                step_container = right_column.container(border=False)
                final = step_container.text_area("🤖", final_thought_action, label_visibility="collapsed", key=f"final answer", disabled=True)

        else:
            raise NotImplementedError
            
        form = right_column.form(key='user-form')
        answer = form.radio(
            "Select and submit your final answer (You can only submit once):",
            ["SUPPORTS", "REFUTES", "NOT ENOUGH INFO"],
            index=None,
            key=f'{st.session_state.condition}_answer_{idx}'
        )

        submit = form.form_submit_button('Submit', on_click=click_submit, args=(answer, ), disabled = st.session_state[idx]['disabled_submit'])
        if st.session_state[idx]['submitted']:
            end_time = datetime.now()
            elapsed_time = (end_time - st.session_state[idx][f"start_time_{idx}"]).total_seconds()
            st.session_state[idx]['actions'].append(f"finish[{answer}]")
            # log data
            if st.session_state.condition.find("regenerate") > -1:
                logger.write_to_user_sheet([st.session_state.username, idx, str(st.session_state[idx]['actions']), len(st.session_state[idx]['actions']), st.session_state[idx]["ai_output_clicks"], str(st.session_state[idx]['model_output_per_run']), answer, st.session_state.condition, elapsed_time])
            else:
                logger.write_data_to_sheet([st.session_state.username, idx, len(st.session_state[idx]['actions']), str(st.session_state[idx]['actions']), str(st.session_state[idx]['observations']), answer, st.session_state.condition, elapsed_time])
            obs, r, done, info = step(env, f"finish[{answer}]")
            st.session_state['answer'] = answer
            right_column.write(f'Submitted: {answer}')
            # right_column.write(f'{obs}')
            if idx in st.session_state['train_ids']:
                if r == 1:
                    output = "Your answer is right! :)"
                else:
                    output = f"Your answer is wrong :( The correct answer is {info['gt_answer']}.\n"
                if idx in st.session_state['train_id2explanation']:
                    expl = st.session_state['train_id2explanation'][idx]
                    output += expl
                right_column.write(f'{output}')
            st.session_state[idx]['submitted'] = False

    return right_column

@st.cache_data
def load_prompts():
    folder = './prompts/'
    prompt_file = 'fever.json'
    with open(folder + prompt_file, 'r') as f:
        prompt_dict = json.load(f)
    return prompt_dict

def display_progress_bar(curr_pos, st):
    progress = st.text(f"You are at {curr_pos} / 30 questions.")
    return st

@st.cache_data
def load_examples():
    examples_file = 'data/examples.json'
    with open(examples_file, 'r') as f:
        examples = json.load(f)
    return examples

def main_study():
    
    env = wikienv.WikiEnv()
    env = wrappers.FeverWrapper(env, split="dev")
    env = wrappers.LoggingWrapper(env)
    # if "env" not in st.session_state:
    #     st.session_state.env = env

    if 'count' not in st.session_state:
        st.session_state.count = 0

    model_outputs = load_model_outputs()
    if 'model outputs' not in st.session_state:
        st.session_state.model_outputs = model_outputs

    prompt_dict = load_prompts()
    webthink_prompt = prompt_dict['webthink_simple3']
    st.session_state['task_prompt'] = webthink_prompt
    human_prompt = ""
    st.session_state['human_task_prompt'] = human_prompt

    train_ids = [4050, 6996, 802, 4118, 1557, 5726,] # 3805
    test_ids = [4278, 2646, 468, 2208, 280, 1391, 217, 2544, 565, 4627, 2033, 2836, 4859, 1781, 1955, 2019, 2498, 2711, 3234, 4341, 5376, 5965, 7096, 3477, 7203, 6158, 2424, 4525, 3196] # 2226,
    if 'train_ids' not in st.session_state:
        st.session_state['train_ids'] = train_ids
    if 'test_ids' not in st.session_state:
        st.session_state['test_ids'] = test_ids
    all_ids = train_ids + test_ids

    all_conditions = ["C. hai-answer", "D. hai-static-chain", "I. hai-regenerate"] #  "E. hai-human-thought", "F. hai-human-action", "G. hai-mixed", "H. hai-update",
    condition = st.radio(
            "Condition",
            all_conditions, # "hai-interact-chain", "hai-interact-chain-delayed", 
            # captions=["A", "C", "D", "E", "F", "G"]
            index=all_conditions.index(st.session_state.condition),
    )
    # condition = "I. hai-regenerate" # random.choice(all_conditions) 
    st.session_state.condition = condition
    # print(st.session_state.condition)
    if 'last_question' not in st.session_state:
        st.session_state.last_question = -1
    
    if st.session_state.last_question != -1 and st.session_state.count == 0:
        st.session_state.count = st.session_state.last_question
        if (st.session_state.count > len(test_ids)):
            st.session_state.is_done = True
            st.session_state.page = "survey"

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

    with st.expander("**See task instruction**"):
        # st.write(st.session_state['task_prompt'])
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
        
        examples = load_examples()
        for k, ex in examples.items():
            st.markdown(f"#### {k}")
            model_output = ex['steps']
            for i, step_str in enumerate(model_output):
                step_container = st.chat_message("assistant")
                
                keywords = ['thought', 'action', 'observation']
                if i == len(model_output) - 1:
                    keywords = ['thought', 'action']


                for kw in keywords:
                    if st.session_state.condition == "C. hai-answer":
                        content_str = step_str[kw]
                    else:
                        content_str = f"{kw[0].upper()+kw[1:]} {i+1}: " + step_str[kw]

                    if kw == "observation":
                        st.chat_message("user", avatar="🌐").write(content_str)
                    elif kw == "action":
                        step_container.text_input("", content_str, label_visibility="collapsed", disabled=True)
                    else:
                        step_container.text_area("", content_str, label_visibility="collapsed", disabled=True)
            st.divider()

    all_cols = st.columns([2, 2, 2, 2, 2, 2])
    left_head = all_cols[0]
    right_head = all_cols[-1]
    # left_head, _, _, right_head = left_column.columns([3, 3, 3, 3])
    prev = left_head.button("Prev", use_container_width=True)

    if "next_clicked" not in st.session_state:
        st.session_state["next_clicked"] = False

    def click_next():
        st.session_state["next_clicked"] = True

    next = right_head.button("Next", use_container_width=True, on_click=click_next)

    st.text(f"You are at {curr_pos} / {total_num} questions.")

    idx = all_ids[st.session_state.count]
    
    question = env.reset(idx=idx)
    if idx not in st.session_state:
        st.session_state[idx] = {}
        st.session_state[idx]["done"] = False
        st.session_state[idx]["turn_id"] = 0
    
    if "submitted" not in st.session_state[idx]:
        st.session_state[idx]['submitted'] = False
    if "disabled_submit" not in st.session_state[idx]:
        st.session_state[idx]['disabled_submit'] = False
    if 'question' not in st.session_state[idx]:
        st.session_state[idx]['question'] = question

    st.subheader(question)
    warning = st.empty()
    st.divider()
    
    left_column, right_column = st.columns(2)
    left_column = display_left_column(env, idx, left_column, st.session_state.condition)
    right_column = display_right_column(env, idx, right_column, st.session_state.condition)

    if 'train_id2explanation' not in st.session_state:
        st.session_state['train_id2explanation'] = {
        4118: "The correct action is Search[Stephen Hillenburg], which yields the result below that supports the claim:\nStephen McDannell Hillenburg (August 21, 1961 – November 26, 2018) was an American animator, writer, producer, director, voice actor, marine science educator, and entrepreneur. He was best known for creating the animated television series SpongeBob SquarePants for Nickelodeon in 1999. Serving as the showrunner for its first three seasons, and again from season nine until his death, the show has become the fifth-longest-running American animated series. He also provided the original voice of Patchy's pet, Potty the Parrot.. Born in Lawton, Oklahoma and raised in Anaheim, California, Hillenburg became fascinated with the ocean as a child and developed an interest in art.",
        5726: "The correct action is Search[Emma Watson], which yields the result below that supports the claim: Emma Charlotte Duerre Watson (born 15 April 1990) is an English actress. Known for her roles in both blockbusters and independent films, she has received a selection of accolades, including a Young Artist Award and three MTV Movie Awards. Watson has been ranked among the world's highest-paid actresses by Forbes and Vanity Fair, and was named one of the 100 most influential people in the world by Time magazine in 2015.[1][2][3]. Watson attended the Dragon School and trained in acting at the Oxford branch of Stagecoach Theatre Arts. As a child, she rose to stardom after landing her first professional acting role as Hermione Granger in the Harry Potter film series, having previously acted only in school plays.",  
        1557: "The correct answer is NOT ENOUGH INFO, because the wiki page about folklore does not mention anything about pratfalls: \nFolklore is the body of expressive culture shared by a particular group of people, culture or subculture.[1] This includes oral traditions such as tales, myths, legends,[a] proverbs, poems, jokes, and other oral traditions.[3][4] This also includes material culture, such as traditional building styles common to the group. Folklore also encompasses customary lore, taking actions for folk beliefs, and the forms and rituals of celebrations such as Christmas, weddings, folk dances, and initiation rites.[3]. Each one of these, either singly or in combination, is considered a folklore artifact or traditional cultural expression. Just as essential as the form, folklore also encompasses the transmission of these artifacts from one region to another or from one generation to the next. Folklore is not something one can typically gain from a formal school curriculum or study in the fine arts."
    }
    if prev:
        if st.session_state.count == 0:
            warning.warning("You're at the start of all examples. There is no previous example.", icon="⚠️")
        else:
            st.session_state.count -= 1
        st.rerun()
    elif st.session_state["next_clicked"]:
        if not st.session_state[idx]['disabled_submit']:
            warning.warning("You need to submit your answer before going to the next question.", icon="⚠️")
            st.session_state["next_clicked"] = False
        else:
            total_num = len(st.session_state['train_ids']) + len(st.session_state['test_ids'])
            total_num = 5
            if st.session_state.count == total_num - 1:
                # st.warning("You're at the end of all examples. There is no next example.", icon="⚠️")
                st.session_state.page = "survey"
            else:
                st.session_state.count += 1
            st.session_state["next_clicked"] = False
            st.rerun()

