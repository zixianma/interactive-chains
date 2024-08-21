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
st.set_page_config(layout="wide")
float_init(theme=True, include_unstable_primary=False)

openai.api_key = os.environ["OPENAI_API_KEY"]
openai_api_key = openai.api_key
env = wikienv.WikiEnv()
env = wrappers.FeverWrapper(env, split="dev")
env = wrappers.LoggingWrapper(env)

def step(env, action):
    attempts = 0
    while attempts < 10:
        try:
            return env.step(action)
        except requests.exceptions.Timeout:
            attempts += 1

# def llm(prompt, stop=["\n"]):
#     client = OpenAI()

#     response = client.chat.completions.create(
#       model="gpt-4o",
#       messages=[{"role": "user", "content": prompt}],
#       temperature=0,
#         max_tokens=100,
#         top_p=1,
#         frequency_penalty=0.0,
#         presence_penalty=0.0,
#         stop=stop
#     )
#     return response.choices[0].message.content

def llm(messages, stop=["\n"]):
    client = OpenAI()

    response = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=messages,
      temperature=0,
        max_tokens=100,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=stop
    )
    return response.choices[0].message.content
# with st.sidebar:
#     openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
#     "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
#     "[View the source code](https://github.com/streamlit/llm-examples/blob/main/Chatbot.py)"
#     "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"

@st.cache_data
def load_model_outputs():
    df = pd.read_json("data/fever_data_with_questions.jsonl", lines=True)
    return df

def get_model_output(output_df, idx):
    output = output_df[output_df['question_idx'] == idx].iloc[0]
    return output['all_steps']

def process_model_output(step_str, final=False):
    for kw in ['Action', 'Observation']:
        start_idx = step_str.find(kw)
        # if step_str[start_idx-1] != "\n":
        if final and kw == "Observation":
            step_str = step_str[:start_idx]
        else:
            step_str = step_str[:start_idx] + "\n" + step_str[start_idx:]
    return step_str


def display_left_column(idx, left_column, condition):
    question = env.reset(idx=idx)
    left_column.write(question)
    if condition == "C. hai-answer":
        model_output = get_model_output(model_outputs, idx)
        last_step_str = model_output[-1]
        last_step_str = process_model_output(last_step_str, final=True)
        start = max(last_step_str.find("["), 0)
        end = last_step_str.find("]")
        final_ans = last_step_str[start+1:end if end > 0 else len(last_step_str)]
        left_column.write(f"AI answer: {final_ans}")

    elif condition != "A. human":
        model_output = get_model_output(model_outputs, idx)
        for i, step_str in enumerate(model_output):
            step_str = process_model_output(step_str, final=(i == len(model_output) -1))
            left_column.write(step_str)
            left_column.divider()
    return left_column

def validate_action_str_format(action_str):
    pattern = r"(search|lookup)\[.+\]"
    match = re.fullmatch(pattern, action_str)
    return match is not None


def add_thought_step(i, prompt, right_column): 
    right_column.write(f"Step {i}")
    thought = ""

    thought = right_column.text_area("Enter your thought:", key=f"thought {i}")
    
    finish_t = right_column.button("Finish", key=f"finish thought {i}")
    # right_column.write("PROMPT:\n" + prompt + thought + f"\nAction {i}:")
    if finish_t:
        action = llm(prompt + thought + f"\nAction {i}:", stop=[f"\nObservation {i}:"])
        obs, r, done, info = step(env, action[0].lower() + action[1:])

        obs = obs.replace('\\n', '')
        step_str = f"Thought {i}: {thought}\nAction {i}: {action}\nObservation {i}: {obs}\n"
        right_column.write(f"STEP:\n{step_str}")
        prompt += step_str

    return prompt, right_column

def display_right_column(idx, right_column, condition):
    question = env.reset(idx=idx)
    if condition == "A. human" or condition == "C. hai-answer" or condition == "D. hai-static-chain":
        right_column.write("Perform a Search or Lookup action to obtain additional information")
        search_query = right_column.text_input('Search', key=f"search {idx}")
        if search_query:
            obs, r, done, info = step(env, f"search[{search_query}]")
            right_column.write(obs)

        lookup_query = right_column.text_input('Lookup', key=f"lookup {idx}")
        if lookup_query:
            obs, r, done, info = step(env, f"lookup[{lookup_query}]")
            right_column.write(obs)
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
    # elif condition.find("interact") > -1:
        
    #     right_column.write("Modify AI's thoughts/actions:")
    #     model_output = get_model_output(model_outputs, idx)
    #     new_chain = []
    #     for i, step_str in enumerate(model_output[:-1]):
    #         step_str = process_model_output(step_str, final=(i == len(model_output) -1))
    #         all_strs = step_str.split('\n')
    #         new_step_str = ""
    #         for j, str in enumerate(all_strs):
    #             if str.find("Observation") > -1: continue
    #             if len(str) < 3: continue
    #             label, content = str.split(":")
    #             content = content.strip()
    #             new_content = right_column.text_area(label, content, key=f"{i}-{j}")
    #             new_step_str += label + " " + new_content + "\n"
    #             if str.find("Action") > -1: # create run action button for all actions except for the last one
    #                 run = right_column.button("Run action", key=f"action-{i} submit")
    #                 if run:
    #                     action_str = f"{new_content[0].lower()+new_content[1:]}"
    #                     obs, r, done, info = step(env, action_str)
    #                     new_step_str += f"Observation {i+1}: {obs}"
    #                     right_column.write(obs)
    #         new_chain.append(new_step_str)
        
    #     get_answer = right_column.button("Get AI answer", key=f"get ai answer")
    #     if get_answer:
    #         new_chain_str = "".join(new_chain)
    #         prompt = webthink_prompt + question + "\n" + new_chain_str
    #         num_steps = len(model_output)
    #         right_column.write(prompt)
    #         new_model_answer = llm(prompt + f"Thought {num_steps}:", stop=[f"\nObservation {num_steps}:"])
    #         right_column.write(new_model_answer)
    #     # left_column.write("=" * 20)
    #     # name = form.text_input('Enter your name')

    #     # chain = form.text_area("Update the chain-of-thoughts/actions:")
    #     form = right_column.form(key='user-form')
    #     answer = form.radio(
    #         "Select your final answer",
    #         ["SUPPORTS", "REFUTES", "NOT ENOUGH INFO"],
    #         index=None,
    #     )

    #     submit = form.form_submit_button('Submit')
    #     # st.write('Press submit to have your final answer printed below')
    #     if submit:
    #         right_column.write(f'Submitted: {answer}!')
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
                    # pattern = r'Action\s\d+'
                    # match = re.search(pattern, content)
                    # if match:
                    #     start_idx = match.start()
                    #     content = content[:start_idx]
                    right_column.chat_message(msg["role"]).write(content)
                
                if prompt := init_prompt:
                    # button_b_pos = "0rem"
                    # button_css = float_css_helper(width="2.2rem", bottom=button_b_pos, transition=0)
                    # float_parent(css=button_css)
                    content = f"Thought {st.session_state[idx]['turn_id']}: " + prompt # + f"\nAction {st.session_state[idx]['turn_id']}:"
                    st.session_state[idx]["messages"].append({"role": "user", "content": content})
                    right_column.chat_message("user").write(content)
                    print(st.session_state[idx]["messages"][-1])
                    action = llm(st.session_state[idx]["messages"], stop=["Observation"])

                    content = action
                    st.session_state[idx]["messages"].append({"role": "assistant", "content": content})
                    right_column.chat_message("assistant").write(content)

                    pattern = r'Action\s\d+:'
                    match = re.search(pattern, action)
                    if match:
                        start_idx = match.end()
                        action = action[start_idx+1:].strip()
                    obs, r, done, info = step(env, action[0].lower() + action[1:])
                    obs = obs.replace('\\n', '')
                    
                    if not done:
                        content = content = f"Observation {st.session_state[idx]['turn_id']}: {obs}\n"
                        st.session_state[idx]["messages"].append({"role": "user", "content": content})
                        right_column.chat_message("user").write(content)
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
                        wrong_format = right_column.warning("There's some issue with the entered action. Please make sure it is either search[query] or lookup[text] and try again.", icon="⚠️")
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
                            right_column.chat_message("user").write(content)
                            st.session_state[idx]["turn_id"] += 1
                            
                            # last_msg = st.session_state[idx]["messages"][-1]
                            # last_msg['content'] += f"\nThought {st.session_state[idx]['turn_id']}:"
                            print(st.session_state[idx]["messages"][1:])
                            # thought = llm(st.session_state[idx]["messages"][:-1] + [last_msg], stop=["Action"])
                            thought = llm(st.session_state[idx]["messages"], stop=["Action"])
                            print(thought)
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
                    right_column.chat_message(msg["role"]).write(msg["content"])

                last_msg = st.session_state[idx]['messages'][-1]['content']
                # print("LAST MSG:", last_msg)
                if prompt := init_prompt:
                    if len(st.session_state[idx]['messages']) == 1 or last_msg.find("Thought") == -1: # user entering a thought
                        content = prompt # + f"\nAction {st.session_state[idx]['turn_id']}:"
                        st.session_state[idx]["messages"].append({"role": "user", "content": content})
                        right_column.chat_message("user").write(content)
                        print(st.session_state[idx]["messages"][-1])
                        
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
                            right_column.chat_message("user").write(content)
                            st.session_state[idx]["turn_id"] += 1
                            
                elif call_ai:
                    if len(st.session_state[idx]['messages']) == 1 or last_msg.find("Thought") == -1: # generate next thought
                        thought = llm(st.session_state[idx]["messages"], stop=["Action"])
                        print(thought)
                        content = f"{thought}\n"
                        st.session_state[idx]["messages"].append({"role": "assistant", "content": content})
                        right_column.chat_message("assistant").write(content)

                    elif last_msg.find("Action") == -1: # generate next action
                        action = llm(st.session_state[idx]["messages"], stop=["Observation"])

                        content = action
                        st.session_state[idx]["messages"].append({"role": "assistant", "content": content})
                        right_column.chat_message("assistant").write(content)

                        pattern = r'Action\s\d+:'
                        match = re.search(pattern, action)
                        if match:
                            start_idx = match.end()
                            action = action[start_idx+1:].strip()
                        obs, r, done, info = step(env, action[0].lower() + action[1:])
                        obs = obs.replace('\\n', '')
                        
                        if not done:
                            content = content = f"Observation {st.session_state[idx]['turn_id']}: {obs}\n"
                            st.session_state[idx]["messages"].append({"role": "user", "content": content})
                            right_column.chat_message("user").write(content)
                            st.session_state[idx]["turn_id"] += 1

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

st.title("🔥 Interactive chains ⛓️")
# st.caption("🚀 A Streamlit app powered by OpenAI")
model_outputs = load_model_outputs()
prompt_dict = load_prompts()
webthink_prompt = prompt_dict['webthink_simple3']

all_ids = list(model_outputs['question_idx'])

# st.write(model_outputs.head())
condition = st.radio(
        "Condition",
        ["A. human", "C. hai-answer", "D. hai-static-chain", "E. hai-human-thought", "F. hai-human-action", "G. hai-mixed"], # "hai-interact-chain", "hai-interact-chain-delayed", 
        # captions=["A", "C", "D", "E", "F", "G"]
        # index=None,
)
# condition = "hai-human-action"
# if 'condition' not in st.session_state:
st.session_state.condition = condition
with st.expander("See task instruction and examples"):
    st.write(webthink_prompt)
left_column, right_column = st.columns(2)
left_head, _, _, right_head = left_column.columns([3, 3, 3, 3])
prev = left_head.button("Prev", use_container_width=True)
next = right_head.button("Next", use_container_width=True)
if 'count' not in st.session_state:
	st.session_state.count = 0

if prev:
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
    # print(st.session_state.condition)
    left_column = display_left_column(idx, left_column, st.session_state.condition)
    right_column = display_right_column(idx, right_column, st.session_state.condition)
    # print(st.session_state)
    





