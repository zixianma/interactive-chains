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
st.set_page_config(layout="wide")
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

def submit_consent():
    if not consent_input or not username_input:
        st.warning("Please fill in all required fields.")
    elif consent_input.lower() != 'yes':
        st.warning("You cannot proceed unless you agree to the terms.") 
    else:
        st.session_state.consent = st.session_state.consent_input
        st.session_state.username = st.session_state.username_input

def step(env, action):
    attempts = 0
    while attempts < 10:
        try:
            return env.step(action)
        except requests.exceptions.Timeout:
            attempts += 1

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

    # make session state dict per question
    if f"question_idx_{idx}" not in st.session_state:
        st.session_state[f"question_idx_{idx}"] = {
            f"last_search_{idx}":  None,
            f"last_lookup_{idx}": None,
            f"start_time_{idx}": datetime.now(),  # Record the start time
            f"step_number_{idx}": 0,
            "actions": []
        }

    if condition == "A. human" or condition == "C. hai-answer" or condition == "D. hai-static-chain":
        right_column.write("Perform a Search or Lookup action to obtain additional information")
        search_query = right_column.text_input('Search', key=f"search {idx}")
        if search_query != st.session_state[f"question_idx_{idx}"][f"last_search_{idx}"] and search_query != "":
            st.session_state[f"question_idx_{idx}"][f"step_number_{idx}"] += 1
            st.session_state[f"question_idx_{idx}"][f"last_search_{idx}"] = search_query
            st.session_state[f"question_idx_{idx}"]["actions"].append(f"search[{search_query}]")
            obs, r, done, info = step(env, f"search[{search_query}]")
            right_column.write(obs)

        lookup_query = right_column.text_input('Lookup', key=f"lookup {idx}")
        if lookup_query != st.session_state[f"question_idx_{idx}"][f"last_lookup_{idx}"] and lookup_query != "":
            st.session_state[f"question_idx_{idx}"][f"step_number_{idx}"] += 1
            st.session_state[f"question_idx_{idx}"][f"last_lookup_{idx}"] = lookup_query
            st.session_state[f"question_idx_{idx}"]["actions"].append(f"lookup[{lookup_query}]")
            obs, r, done, info = step(env, f"lookup[{lookup_query}]")
            right_column.write(obs)
        form = right_column.form(key='user-form')
        answer = form.radio(
            "Select your final answer",
            ["SUPPORTS", "REFUTES", "NOT ENOUGH INFO"],
            index=None,
            key=f'answer_{idx}' # this is so the radio button clears it last saved answer because this is saved in session_state
        )
        submit = form.form_submit_button('Submit')
        if submit:
            st.session_state[f"question_idx_{idx}"]["actions"].append(f"finish[{answer}]")
            end_time = datetime.now()
            elapsed_time = (end_time - st.session_state[f"question_idx_{idx}"][f"start_time_{idx}"]).total_seconds()
            # log response into spreadsheet here.
            write_to_sheet([st.session_state.username, idx, st.session_state[f"question_idx_{idx}"][f"step_number_{idx}"], str(st.session_state[f"question_idx_{idx}"]["actions"]), answer, condition, elapsed_time])
            obs, r, done, info = step(env, f"finish[{answer}]")
            st.session_state.user_data["last question idx done"] = idx
            st.session_state['answer'] = answer
            right_column.write(f'Submitted: {answer}!')
            right_column.write(f'{obs}')
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
                    st.session_state[f"question_idx_{idx}"][f"step_number_{idx}"] += 1
                    st.session_state[f"question_idx_{idx}"]["actions"].append(content) # or juse use prompt
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
                        st.session_state[f"question_idx_{idx}"][f"step_number_{idx}"] += 1
                        st.session_state[f"question_idx_{idx}"]["actions"].append(content) # or juse use prompt
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
                        st.session_state[f"question_idx_{idx}"][f"step_number_{idx}"] += 1
                        st.session_state[f"question_idx_{idx}"]["actions"].append(content) # or juse use prompt
                        right_column.chat_message("user").write(content)
                        print(st.session_state[idx]["messages"][-1])
                        
                    else: # user entering an action
                        action = prompt
                        content = f"Action {st.session_state[idx]['turn_id']}: {action}\n"
                        st.session_state[idx]["messages"].append({"role": "user", "content": content})
                        st.session_state[f"question_idx_{idx}"][f"step_number_{idx}"] += 1
                        st.session_state[f"question_idx_{idx}"]["actions"].append(content) # or juse use prompt
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
                        st.session_state[f"question_idx_{idx}"][f"step_number_{idx}"] += 1
                        st.session_state[f"question_idx_{idx}"]["actions"].append("Generated next thought with AI")
                        thought = llm(st.session_state[idx]["messages"], stop=["Action"])
                        print(thought)
                        content = f"{thought}\n"
                        st.session_state[idx]["messages"].append({"role": "assistant", "content": content})
                        right_column.chat_message("assistant").write(content)

                    elif last_msg.find("Action") == -1: # generate next action
                        st.session_state[f"question_idx_{idx}"][f"step_number_{idx}"] += 1
                        st.session_state[f"question_idx_{idx}"]["actions"].append("Generated next action with AI")
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
            key=f'answer_{idx}_condition{st.session_state.condition}' # this is so the radio button clears it last saved answer because this is saved in session_state
        )

        submit = form.form_submit_button('Submit')
        if submit:
            end_time = datetime.now()
            elapsed_time = (end_time - st.session_state[f"question_idx_{idx}"][f"start_time_{idx}"]).total_seconds()
            st.session_state[f"question_idx_{idx}"]["actions"].append(f"finish[{answer}]")
            # log response into spreadsheet here.
            write_to_sheet([st.session_state.username, idx, st.session_state[f"question_idx_{idx}"][f"step_number_{idx}"], str(st.session_state[f"question_idx_{idx}"]["actions"]), answer, condition, elapsed_time])
            st.session_state.user_data["last question idx done"] = idx
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

if 'username' not in st.session_state:
    st.session_state.username = ''

if 'consent' not in st.session_state:
    st.session_state.consent = ''

if 'user_data' not in st.session_state:
    st.session_state.user_data = {
        "visits": 0,
        'last question idx done': -1,
        'location data': get_user_ip()
    }

if not st.session_state.username and not st.session_state.consent:
    st.title("Welcome to the Application")
    st.subheader("Please enter your username from Prolific to continue")
    # Input field for the username
    username_input = st.text_input("Username", key="username_input").strip()

    st.subheader("Please carefully read below before proceeding.")
    st.write("""You are invited to participate in a research study on user understanding of algorithms and models. You will be asked to answer multiple choice and free response questions about different provided algorithms and their expected behavior. You will not be recorded via audio or video.\n
TIME INVOLVEMENT: Your participation will take approximately 30 minutes.\n
PAYMENTS: You will receive \$7.50 via the survey platform upon completion of the study, and you will receive additional compensation of \$0.10 per correct answer afterwards, as payment for your participation. A total of up to $1.50 in bonuses is available.\n
RISKS AND BENEFITS: The risks associated with this study are minimal. A potential data breach or breach of confidentiality should not adversely affect employment or reputation. Study data will be stored securely, in compliance with University of Washington standards, minimizing the risk of confidentiality breach. You may be exposed to content that is upsetting, as this study involves a wide array of statements to validate, some of which contain harmful text (e.g., profanity, slurs, expressions of bigotry like racism/sexism/homophobia/religious intolerance, discussion of violence, jokes about tragedies). The benefits which may reasonably be expected to result from this study are none. We cannot and do not guarantee or promise that you will receive any benefits from this study.\n
PARTICIPANT’S RIGHTS: If you have read this form and have decided to participate in this project, please understand your participation is voluntary and you have the right to withdraw your consent or discontinue participation at any time without penalty or loss of benefits to which you are otherwise entitled. The alternative is not to participate. You have the right to refuse to answer particular questions. The results of this research study may be presented at scientific or professional meetings or published in scientific journals. Your individual privacy will be maintained in all published and written data resulting from the study.\n
CONTACT INFORMATION: If you have any questions, concerns or complaints about this research, its procedures, risks and benefits, contact the Protocol Director, Zixian Ma, at zixianma@uw.edu.\n
Independent Contact: If you are not satisfied with how this study is being conducted, or if you have any concerns, complaints, or general questions about the research or your rights as a participant, please contact the University of Washington Institutional Review Board (IRB) to speak to someone independent of the research team at 206-543-0098, or email at hsdreprt@uw.edu. You can also write to the University of Washington IRB at Human Subjects Division, University of Washington, Box 359470, 4333 Brooklyn Ave NE, Seattle, WA 98195-9470.""")
    # Input field for the consent
    consent_input = st.text_input("Do you consent? (Input 'Yes' or 'No')", key="consent_input").strip()

    # Submit button
    st.button("Submit", on_click=submit_consent)

else:
    def write_to_sheet(data):
        # write the data in the format of: user, quetion idx, step #, action, time?
        sheet.worksheet('actions').append_row(data)
        user_worksheet.append_row(data)
    
    def write_to_user_sheet(data):
        sheet.worksheet('users').append_row(data)

    def create_user_worksheet():
        # Check if a worksheet for this user already exists
        try:
            worksheet = sheet.worksheet(st.session_state.username)
        except gspread.exceptions.WorksheetNotFound:
            # Create a new worksheet for the user if it doesn't exist
            worksheet = sheet.add_worksheet(title=st.session_state.username, rows=100, cols=20)
            worksheet.append_row(['user','question idx', 'total steps', 'action space', 'answer', 'condition', 'time'])
        
        return worksheet

    toml_data = toml.load(".streamlit/secrets.toml")
    credentials_data = toml_data["connections"]["gsheets"]

    # st.write(st.session_state) # debugging purposes

    # Define the scope for the Google Sheets API
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    # Authenticate using the credentials from the TOML file
    credentials = Credentials.from_service_account_info(credentials_data, scopes=scope)
    client = gspread.authorize(credentials)

    # Open the Google Sheet by name
    sheet = client.open('interactive chains') # should add condition here so it goes to correct Sheet

    # make sheet per user
    user_worksheet = create_user_worksheet()

    # this is to load it using TOML as well
    openai.api_key = os.environ["OPENAI_API_KEY"]
    openai_api_key = openai.api_key
    env = wikienv.WikiEnv()
    env = wrappers.FeverWrapper(env, split="dev")
    env = wrappers.LoggingWrapper(env)

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
