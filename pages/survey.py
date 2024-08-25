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

def free_form_questions():
    st.title("Final Questions & Feedback")

    st.subheader("You must answer all of the questions here before clicking submit to be paid.")

    st.write("What was your strategy when it came to resolving the questions?")
    strategy = st.text_area("Enter your response here.")

    st.write("Did you find any errors within the AI model’s reasoning, if so, how did you find the errors?")
    error_finding = st.text_area("Enter your response here.")

    st.write("How did you use the AI model to help you answer the question? Did you use the answer? Chains? Interactions?")
    ai_model_usage = st.text_area("Enter your response here.")

    # condition based
    st.write("In the interactive case: How did you interact with the model/thought/action? What was confusing? Were any parts of the interaction were demanding? Please also provide a why.")
    ai_model_interaction_usage = st.text_area("Enter your response here.")

    st.write("Any other comments or remarks regarding the study?")
    misc_comments = st.text_area("Enter your response here.")

    if st.button("Submit", key="submit_answers"):
        if not strategy or not error_finding or not ai_model_interaction_usage or ai_model_usage:
            st.error("Please fill in one of the text boxes.")
        # submit data
        # create clickable link so worker can be paid

def interaction_questions():
    st.title("Reflection Questions")

    # TODO: rewrite these to go into session_state

    st.subheader("Rate the following statements regarding the interactions")

    st.write("I found the AI’s code completions helpful as a starting point.")
    code_completion_helpful = st.radio("Options", ["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"])

    # condition based
    st.write("I found the AI’s highlights helpful in determining what to edit")
    highlights_helpful = st.radio("Options", ["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"])

    st.write("I would be willing to pay to access the AI’s code completions.")
    willing_to_pay = st.radio("Options", ["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"])

    # condition based
    st.write("I would be willing to pay to access the AI’s highlights.")
    willing_to_pay_highlights = st.radio("Options", ["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"])

    st.write("I found the AI’s code completions distracting.")
    code_completion_distracting = st.radio("Options", ["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"])

    # condition based
    st.write("I found the AI’s highlights distracting.")
    highlights_distracting = st.radio("Options", ["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"])

    if st.button("Next", key="interaction_questions_next"):
        # log data
        free_form_questions()

def ai_usage_questions():
    st.write("HELLO!!!")
    st.title("Reflection Questions")

    # TODO: rewrite these to go into session_state

    st.write("How often do you use AI models (e.g. ChatGPT, DaLLE, CoPilot)?")
    ai_frequency = st.radio("Options", ['Never', 'Rarely (once a year)', 'Occasionally (once a few months)', 'Sometimes (once a month)', 'Frequently (once a week)', 'Usually (once a few days)', 'Always (at least once a day)'])

    st.write("How often did you use the AI model’s answer to help answer the question?")
    ai_answer_usage = st.radio("Options", ['Never', 'Rarely', 'Occasionally', 'Sometimes', 'Frequently', 'Usually', 'Always'])

    st.write("How helpful did you find the AI model's answer chain when trying to come to an answer?")
    ai_answer_helpful = st.radio("Options", ['Very Unhelpful', 'Not Helpful', 'Sometimes', 'Neutral', 'Helpful', 'Very helpful'])

    st.write("How often did you use the AI model’s reasoning chain to help answer the question?")
    ai_reasoning_chain_usage= st.radio("Options", ['Never', 'Rarely', 'Occasionally', 'Sometimes', 'Frequently', 'Usually', 'Always'])

    st.write("How helpful did you find the AI model's reasoning chain when trying to come to an answer?")
    ai_reasoning_chain_helpful = st.radio("Options", ['Very Unhelpful', 'Not Helpful', 'Sometimes', 'Neutral', 'Helpful', 'Very helpful'])

    st.write("How often did you use the interactions with the model  to help answer the question?")
    interaction_usage = st.radio("Options", ['Never', 'Rarely', 'Occasionally', 'Sometimes', 'Frequently', 'Usually', 'Always'])

    st.write("How helpful did you find the interactions with the model when trying to come to an answer?")
    interaction_helpfulness = st.radio("Options", ['Very Unhelpful', 'Not Helpful', 'Sometimes', 'Neutral', 'Helpful', 'Very helpful'])

    st.write("How often did you use the AI model’s explanations to come to an answer?")
    explanation_usage = st.radio("Options", ['Never', 'Rarely', 'Occasionally', 'Sometimes', 'Frequently', 'Usually', 'Always'])

    st.write("How helpful did you find the AI model's explanations when trying to come to an answer?")
    explanation_helpfulness = st.radio("Options", ['Very Unhelpful', 'Not Helpful', 'Sometimes', 'Neutral', 'Helpful', 'Very helpful'])

    if st.button("Next", key="ai_usage_questions_next"):
        # log data
        interaction_questions()

def tasks_demand_questions():
    st.title("Reflection Questions")
    st.session_state.task_demand = {
        'mental_demand': '',
        'success': '',
        'effort': '',
        'pace': '',
        'stress': '',
        'complex_to_simple': '',
        'thinking': '',
        'thinking_fun': '',
        'thought': '',
        'new_solutions': '',
        'difficulty': '',
    }

    st.session_state.task_demand['mental_demand'] = st.slider("How mentally demanding were the tasks", 0, 100, step=5, key="mental")
    st.session_state.task_demand['success'] = st.slider("How successful were you in accomplishing what you were asked to do?", 0, 100, step=5, key='success')
    st.session_state.task_demand['effort'] = st.slider("How hard did you have to work to accomplish your level of performance?", 0, 100, step=5,key="effort")
    st.session_state.task_demand['pace'] = st.slider("How hurried or rushed were the pace of the tasks?", 0, 100, step=5, key="pace")
    st.session_state.task_demand['stress'] = st.slider("How insecure, discouraged, irritated, stressed, and annoyed were you?", 0, 100, step=5, key="stress")

    st.write("I would prefer complex to simple problems.")
    st.session_state.task_demand['complex_to_simple'] = st.slider("1 = Strongly Disagree, 5 = Strongly Agree", 1, 5, step=1, key="complex_to_simple")
    st.write("I like to have the responsibility of handling a situation that requires a lot of thinking.")
    st.session_state.task_demand['thinking'] = st.slider("1 = Strongly Disagree, 5 = Strongly Agree", 1, 5, step=1,key="thinking")
    st.write("Thinking is not my idea of fun.")
    st.session_state.task_demand['thinking_fun'] = st.slider("5 = Strongly Disagree, 1 = Strongly Agree", 1, 5, step=1, key="thinking_fun")
    st.write("I would rather do something that requires little thought than something that is sure to challenge my thinking abilities.")
    st.session_state.task_demand['thought'] = st.slider("5 = Strongly Disagree, 1 = Strongly Agree", 1, 5, step=1, key="thought")
    st.write("I really enjoy a task that involves coming up with new solutions to problems.")
    st.session_state.task_demand['new_solutions'] = st.slider("1 = Strongly Disagree, 5 = Strongly Agree", 1, 5, step=1, key="new_solutions")
    st.write("I would prefer a task that is intellectual, difficult, and important to one that is somewhat important but does not require much thought.")
    st.session_state.task_demand['difficulty'] = st.slider("1 = Strongly Disagree, 5 = Strongly Agree", 1, 5, step=1, key="difficulty")

    if st.button("Next questions", key="tasks_demand_questions_next"):
        # log data
        ai_usage_questions()

def survey():
    st.title("Reflection Questions & Feedback")