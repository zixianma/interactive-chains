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
from datetime import datetime
# st.set_page_config(layout="wide")
float_init(theme=True, include_unstable_primary=False)

def get_user_ip():
    try:
        ip = requests.get('https://api64.ipify.org?format=json').json()["ip"]
        response = requests.get(f'https://ipinfo.io/{ip}/json')
        data = response.json()
        location = {
            'ip': data.get('ip'),
            'city': data.get('city'),
            'region': data.get('region'),
            'country': data.get('country'),
            'loc': data.get('loc'),  # Latitude and Longitude
            'org': data.get('org'),
            'timezone': data.get('timezone')
        }
        return location
    except Exception as e:
        return {"error": str(e)}

def submit_username():
    if st.session_state.username_input:
        st.session_state.username = st.session_state.username_input

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
    client = OpenAI()

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
    df = pd.read_json("data/fever_data_with_questions.jsonl", lines=True)
    q_id2output = {}
    for _, row in df.iterrows():
        q_id = row['question_idx']
        
        model_output = row['all_steps']
        new_steps = []
        for i, step_str in enumerate(model_output):
            step_str = process_model_output(step_str, final=False) # (i == len(model_output) -1)
            thought_str = get_part_from_step(step_str, "Thought", "Action").strip()
            action_str = get_part_from_step(step_str, "Action", "Observation").strip()
            obs_str = get_part_from_step(step_str, "Observation", "\n").strip()
            new_step = {"thought": thought_str, "action": action_str, "observation": obs_str}
            new_steps.append(new_step)

        q_id2output[q_id] = new_steps
    return q_id2output

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

def display_left_column(idx, left_column, condition):
    question = env.reset(idx=idx)
    left_column.text(f"You're at {st.session_state.count + 1} / 30 questions.")
    left_column.subheader(question)
    if 'question' not in st.session_state[idx]:
        st.session_state[idx]['question'] = question

    if condition == "C. hai-answer":
        # model_output = get_model_output(model_outputs, idx)
        model_output = st.session_state.model_outputs[idx]
        final_ans = extract_final_answer(model_output)
        
        left_column.divider()
        container = left_column.chat_message("assistant")
        container.write(f"AI answer: {final_ans}")

    elif condition != "A. human":
        # model_output = get_model_output(model_outputs, idx)
        model_output = st.session_state.model_outputs[idx]
        left_column.divider()
        
        for i, step_str in enumerate(model_output):
            step_container = left_column.chat_message("assistant")
            # step_str = process_model_output(step_str, final=(i == len(model_output) -1))
            keywords = ['thought', 'action', 'observation']
            if i == len(model_output) - 1:
                keywords = ['thought', 'action']
            for kw in keywords:
                if kw == "observation":
                    left_column.chat_message("user", avatar="🌐").write(step_str[kw])
                else:
                    step_container.write(step_str[kw])
            # left_column.button("Edit this step", key=f"update {i}")

            left_column.divider()
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
    return action[0].lower() + action[1:]

def display_right_column(idx, right_column, condition):
    question = env.reset(idx=idx)
    if condition == "A. human" or condition == "C. hai-answer" or condition == "D. hai-static-chain":
        # make session state dict per question
        if f"last_search_{idx}" not in st.session_state[idx]:
            st.session_state[idx][f"last_search_{idx}"] = None
        if f"last_lookup_{idx}" not in st.session_state[idx]:
            st.session_state[idx][f"last_lookup_{idx}"] = None
        if f"start_time_{idx}" not in st.session_state[idx]:
            st.session_state[idx][f"start_time_{idx}"] = datetime.now()
        if f"step_number_{idx}" not in st.session_state[idx]:
            st.session_state[idx][f"step_number_{idx}"] = 1

        right_column.write("Perform a Search or Lookup action to obtain additional information")
        search_query = right_column.text_input('Search', key=f"search {idx}")
        # may need to incoporate a flag when text input changes
        if search_query != st.session_state[idx][f"last_search_{idx}"] and search_query != "":
            st.session_state[idx][f"last_search_{idx}"] = search_query
            obs, r, done, info = step(env, f"search[{search_query}]")
            right_column.write(obs)
            st.session_state[idx][f"step_number_{idx}"] += 1

        lookup_query = right_column.text_input('Lookup', key=f"lookup {idx}")
        if lookup_query != st.session_state[idx][f"last_lookup_{idx}"] and lookup_query != "":
            st.session_state[idx][f"last_lookup_{idx}"] = lookup_query
            obs, r, done, info = step(env, f"lookup[{lookup_query}]")
            right_column.write(obs)
            st.session_state[idx][f"step_number_{idx}"] += 1

        form = right_column.form(key='user-form')
        answer = form.radio(
            "Select your final answer",
            ["SUPPORTS", "REFUTES", "NOT ENOUGH INFO"],
            index=None,
            key=f'answer_{idx}' # this is so the radio button clears it last saved answer because this is saved in session_state
        )

        submit = form.form_submit_button('Submit')
        if submit:
            end_time = datetime.now()
            elapsed_time = (end_time - st.session_state[idx][f"start_time_{idx}"]).total_seconds()
            obs, r, done, info = step(env, f"finish[{answer}]")
            st.session_state.user_data["last question idx done"] = idx
            # st.session_state['answer'] = answer
            right_column.write(f'Submitted: {answer}!')
            # right_column.write(f'{obs}')

        # right_column.write("Perform a Search or Lookup action to obtain additional information")
        # search_query = right_column.text_input('Search', key=f"search {idx}")
        # if search_query:
        #     obs, r, done, info = step(env, f"search[{search_query}]")
        #     right_column.write(obs)

        # lookup_query = right_column.text_input('Lookup', key=f"lookup {idx}")
        # if lookup_query:
        #     obs, r, done, info = step(env, f"lookup[{lookup_query}]")
        #     right_column.write(obs)
        # form = right_column.form(key='user-form')
        # answer = form.radio(
        #     "Select your final answer",
        #     ["SUPPORTS", "REFUTES", "NOT ENOUGH INFO"],
        #     index=None,
        # )
        # submit = form.form_submit_button('Submit')
        # if submit:
        #     obs, r, done, info = step(env, f"finish[{answer}]")
        #     st.session_state['answer'] = answer
        #     right_column.write(f'Submitted: {answer}!')
        #     right_column.write(f'{obs}')
    else:
        
        if condition.find("thought") > -1:
            right_column.write("Interact with the AI model by entering your thought (actions will be generated by AI and given to you):")
            # interact = right_column.button("Interact with AI to modify thoughts/actions", key="interact with thought")
            # if interact:
            if "turn_id" not in st.session_state[idx]:
                st.session_state[idx]["turn_id"] = 1
            if "messages" not in st.session_state[idx]:
                st.session_state[idx]["messages"] = [{"role": "assistant", "content": webthink_prompt + question + "\n"}]
                
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
            right_column.write("Interact with the AI model by entering your action (thoughts will be generated by AI and given to you):")
            # interact = right_column.button("Interact with AI to modify thoughts/actions", key="interact with action")
            # if interact:
            if "turn_id" not in st.session_state[idx]:
                st.session_state[idx]["turn_id"] = 0
            if "messages" not in st.session_state[idx]:
                st.session_state[idx]["messages"] = [{"role": "user", "content": webthink_prompt + question}]

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
            right_column.write("Interact with the AI model by entering your thought/action:")
            if "turn_id" not in st.session_state[idx]:
                st.session_state[idx]["turn_id"] = 1
            if "messages" not in st.session_state[idx]:
                st.session_state[idx]["messages"] = [{"role": "user", "content": webthink_prompt + question}]
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
            right_column.write("Edit AI's reasoning chain and get a new answer:")
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
            
            
            # for i in range(num_steps):
            #     print(i, st.session_state[f'delete {i}'])
            #     print(i, st.session_state[f'step {i} deleted'])
                # if delete:
                #     valid_steps[i] = False
            # print(st.session_state)
                # left_column.write(step_str)
                # right_column.divider()
        elif condition.find("regenerate") > -1:
            right_column.write("Edit AI's thought/action and get a new answer:")
            model_output =  st.session_state.model_outputs[idx][:-1]
            if 'curr_model_output' not in st.session_state[idx]:
                st.session_state[idx]['curr_model_output'] = model_output
            if 'curr_num_steps' not in st.session_state[idx]:
                st.session_state[idx]['curr_num_steps'] = len(model_output)

            new_model_output = []
            for i, step_dict in enumerate(st.session_state[idx]['curr_model_output']):
                # step_str = process_model_output(step_str, final=False) #(i == len(model_output) -1)
                obs_str = step_dict['observation'] #get_part_from_step(step_str, "Observation", "\n").strip()
                thought_str = step_dict['thought'] # get_part_from_step(step_str, "Thought", "Action").strip()
                action_str = step_dict['action'] # get_part_from_step(step_str, "Action", "Observation").strip()
                # if i not in valid_steps:
                #     valid_steps[i] = True
                # right_column.chat_message("assistant").write(before_obs_str) # , avatar="🧑‍💻"
                # right_column.header("🤖")
 
                step_container = right_column.chat_message("assistant") # right_column.container(border=False)
                # if f"step {i} deleted" not in st.session_state or not st.session_state[idx][f"step {i} deleted"]:
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
            print(generate)
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
            "Select your final answer",
            ["SUPPORTS", "REFUTES", "NOT ENOUGH INFO"],
            index=None,
        )

        submit = form.form_submit_button('Submit')
        if submit:
            obs, r, done, info = step(env, f"finish[{answer}]")
            st.session_state['answer'] = answer
            right_column.write(f'Submitted: {answer}!')
            right_column.write(f'{obs}')

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

def main_study():
    # if 'username' not in st.session_state:
    #     st.session_state.username = ''

    # if 'user_data' not in st.session_state:
    #     st.session_state.user_data = {
    #         "visits": 0,
    #         'last question idx done': -1,
    #         'location data': get_user_ip()
    #     }

    # # commented out for development, should uncomment at deployment
    # if not st.session_state.username:
    #     st.title("Welcome to the Application")
    #     st.subheader("Please enter your username from Prolific to continue")

    #     # Input field for the username
    #     st.text_input("Username", key="username_input")

    #     # Submit button
    #     st.button("Submit", on_click=submit_username)
    # else:
    #     toml_data = toml.load(".streamlit/secrets.toml")
    #     credentials_data = toml_data["connections"]["gsheets"]

    #     # st.write(st.session_state)

    #     # Define the scope for the Google Sheets API
    #     scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    #     # Authenticate using the credentials from the TOML file
    #     credentials = Credentials.from_service_account_info(credentials_data, scopes=scope)
    #     client = gspread.authorize(credentials)

    #     # Open the Google Sheet by name
    #     sheet = client.open('interactive chains')

    # this is to load it using TOML as well
    openai.api_key = os.environ["OPENAI_API_KEY"]
    openai_api_key = openai.api_key
    env = wikienv.WikiEnv()
    env = wrappers.FeverWrapper(env, split="dev")
    env = wrappers.LoggingWrapper(env)

    if 'count' not in st.session_state:
        st.session_state.count = 0

    model_outputs = load_model_outputs()
    if 'model outputs' not in st.session_state:
        st.session_state.model_outputs = model_outputs

    prompt_dict = load_prompts()
    webthink_prompt = prompt_dict['webthink_simple3']
    st.session_state['task_prompt'] = webthink_prompt

    st.title("🔥 Interactive chains ⛓️")
    # st.caption("🚀 A Streamlit app powered by OpenAI")

    # all_ids = list(model_outputs['question_idx'])
    all_ids = [4278, 2646, 468, 2208, 280, 1391, 5726, 217, 2544, 3805, 4118, 565, 1557, 2226, 4627, 2033, 2836, 4859, 1781, 802, 1955, 2019, 2498, 2711, 3234, 4341, 5376, 5965, 7096, 6996, 3477, 7203, 6158, 4050, 2424, 4525, 3196, 2674]
    # list(model_outputs.keys()) 

    # st.write(model_outputs.head())
    condition = st.radio(
            "Condition",
            ["A. human", "C. hai-answer", "D. hai-static-chain", "E. hai-human-thought", "F. hai-human-action", "G. hai-mixed", "H. hai-update"], # "hai-interact-chain", "hai-interact-chain-delayed", 
            # captions=["A", "C", "D", "E", "F", "G"]
            # index=None,
    )
    condition = "hai-regenerate"
    # if 'condition' not in st.session_state:
    st.session_state.condition = condition

    with st.expander("See task instruction and examples"):
        st.write(webthink_prompt)

    left_column, right_column = st.columns(2)
    left_head, _, _, right_head = left_column.columns([3, 3, 3, 3])
    prev = left_head.button("Prev", use_container_width=True)
    next = right_head.button("Next", use_container_width=True)
    # progress = left_column.empty()
    if prev:
        # progress = display_progress_bar(st.session_state.count + 1 - 1, progress)
        if st.session_state.count == 0:
            st.warning("You're at the start of all examples. There is no previous example.", icon="⚠️")
        else:
            st.session_state.count -= 1
        idx = all_ids[st.session_state.count]
        if idx not in st.session_state:
            st.session_state[idx] = {}
            st.session_state[idx]["turn_id"] = 0
        
        left_column = display_left_column(idx, left_column, st.session_state.condition)
        right_column = display_right_column(idx, right_column, st.session_state.condition)
        # print(st.session_state)
    elif next:
        # progress = display_progress_bar(st.session_state.count + 1 + 1, progress)
        if st.session_state.count == len(model_outputs):
            st.warning("You're at the end of all examples. There is no previous example.", icon="⚠️")
        else:
            st.session_state.count += 1
        idx = all_ids[st.session_state.count]
        if idx not in st.session_state:
            st.session_state[idx] = {}
            st.session_state[idx]["turn_id"] = 0
        
        left_column = display_left_column(idx, left_column, st.session_state.condition)
        right_column = display_right_column(idx, right_column, st.session_state.condition)
        # print(st.session_state)
    else:
        idx = all_ids[st.session_state.count]
        if idx not in st.session_state:
            st.session_state[idx] = {}
            st.session_state[idx]["turn_id"] = 0
        # progress = display_progress_bar(st.session_state.count + 1, progress)
        # print(st.session_state.condition)
        left_column = display_left_column(idx, left_column, st.session_state.condition)
        right_column = display_right_column(idx, right_column, st.session_state.condition)
        # print(st.session_state)



    





