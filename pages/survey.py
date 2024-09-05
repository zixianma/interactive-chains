import streamlit as st
from streamlit_float import *
from datetime import datetime
import pages.utils.logger as logger
from hotjar import load_hotjar

def record_data_clear_state(keys_list = [], header=False, survey_type = ""):
    # convert the data from dict to tuple
    responses = []
    keys = keys_list
    for key in keys:
        if key in st.session_state:
            # will change this later, doing as sanity checker for now
            responses.append((key, st.session_state[key]))
    logger.write_survey_response(responses, header, survey_type)
    # Delete all keys in the list
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]

def finished():
    st.title("Thank you for your time!")
    st.subheader("Click below to complete the study.")
    st.write("Insert link here.")

def free_form_questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()

    st.title("Final Questions & Feedback")
    st.subheader("Note: You cannot go back, please take your time answering these.")

    # Use st.session_state.get to avoid overwriting existing text when rerunning
    st.session_state.strategy = st.text_area(
        "What was your strategy when it came to resolving the questions?",
        value=st.session_state.get('strategy', ''), key='strategy_frq'
    )

    st.session_state.error_finding = st.text_area(
        "Did you find any errors within the AI model’s reasoning, if so, how did you find the errors?",
        value=st.session_state.get('error_finding', ''), key='error_finding_frq'
    )

    st.session_state.ai_model_usage = st.text_area(
        "How did you use the AI model to help you answer the question? Did you use the answer? Chains? Interactions?",
        value=st.session_state.get('ai_model_usage', ''), key='ai_model_usage_frq'
    )

    st.session_state.ai_model_interaction_usage = st.text_area(
        "In the interactive case: How did you interact with the model/thought/action? What was confusing? Were any parts of the interaction were demanding? Please also provide a why.",
        value=st.session_state.get('ai_model_interaction_usage', ''), key='ai_model_interaction_usage_frq'
    )

    st.session_state.misc_comments = st.text_area(
        "Any other comments or remarks regarding the study?",
        value=st.session_state.get('misc_comments', ''), key='misc_comments_frq'
    )

    if st.button("Submit", key="submit_answers"):
        if any([
                st.session_state.strategy.strip() == '',
                st.session_state.error_finding.strip() == '',
                st.session_state.ai_model_usage.strip() == '',
                st.session_state.ai_model_interaction_usage.strip() == '',
                st.session_state.misc_comments.strip() == ''
            ]):
            st.error("Please fill in all the text boxes before submitting.")
        else:
            end_time = datetime.now()
            st.session_state.time_spent = str((end_time - st.session_state.time_spent).total_seconds())
            # submit data
            record_data_clear_state(['strategy', 'error_finding', 'ai_model_usage', 'ai_model_interaction_usage', 'misc_comments', 'time_spent'])
            # create clickable link so worker can be paid
            st.session_state.qa_page = 'complete'
            st.rerun()

def interaction_questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()

    st.title("Interaction Reflection Questions")
    st.subheader("Note: You cannot go back, please take your time answering these.")

    options = ['Select an Option', 'Strongly Disagree', 'Disagree', 'Somewhat Disagree', 'Neutral', 'Somewhat Agree', 'Agree', 'Strongly Agree'] 
    st.subheader("Rate the following statements regarding the interactions")
    st.session_state.code_completion_helpful = st.radio("I found the AI’s code completions helpful as a starting point.", options, horizontal=True, key='code_completion_helpful_radio')
    # condition based
    st.write("I found the AI’s highlights helpful in determining what to edit")
    st.session_state.highlights_helpful = st.radio("I found the AI’s highlights helpful in determining what to edit", options, horizontal=True, key='highlights_helpful_radio')
    st.session_state.willing_to_pay = st.radio("I would be willing to pay to access the AI’s code completions.", options, horizontal=True, key='willing_to_pay_radio')
    # condition based
    st.session_state.willing_to_pay_highlights = st.radio("I would be willing to pay to access the AI’s highlights.", options, horizontal=True, key='willing_to_pay_highlights_radio')
    st.session_state.code_completion_distracting = st.radio("I found the AI’s code completions distracting.", options, horizontal=True, key='code_completion_distracting_radio')
    # condition based
    st.session_state.highlights_distracting = st.radio("I found the AI’s highlights distracting.", options, horizontal=True, key='highlights_distracting_radio')

    if st.button("Next", key="interaction_questions_next"):
        if (
            st.session_state.code_completion_helpful == 'Select an Option' or
            st.session_state.highlights_helpful == 'Select an Option' or
            st.session_state.willing_to_pay == 'Select an Option' or
            st.session_state.willing_to_pay_highlights == 'Select an Option' or
            st.session_state.code_completion_distracting == 'Select an Option' or
            st.session_state.highlights_distracting == 'Select an Option'
        ):
            st.error("Please make sure to select an option for all questions before submitting.")
        else:
            end_time = datetime.now()
            st.session_state.time_spent = str((end_time - st.session_state.time_spent).total_seconds())
            # log data
            record_data_clear_state(['code_completion_helpful', 'highlights_helpful', 'willing_to_pay', 'willing_to_pay_highlights', 'code_completion_distracting', 'highlights_distracting', 'time_spent'])
            st.session_state.qa_page = 'frq'
            st.rerun()

def ai_usage_questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()

    st.title("AI Usage Reflection Questions")
    st.subheader("Note: You cannot go back, please take your time answering these.")
    options_frequency = ['Select an Option', 'Never', 'Rarely', 'Occasionally', 'Sometimes', 'Frequently', 'Usually', 'Always']
    options_helpful = ['Select an Option', 'Very Unhelpful', 'Not Helpful', 'Sometimes', 'Neutral', 'Helpful', 'Very helpful']

    st.session_state.ai_frequency = st.radio("How often do you use AI models (e.g. ChatGPT, DaLLE, CoPilot)?", ['Select an Option', 'Never', 'Rarely (once a year)', 'Occasionally (once a few months)', 'Sometimes (once a month)', 'Frequently (once a week)', 'Usually (once a few days)', 'Always (at least once a day)'], horizontal=True, key='ai_frequency_radio')
    st.session_state.ai_answer_usage = st.radio("How often did you use the AI model’s answer to help answer the question?", options_frequency, horizontal=True, key='ai_answer_usage_radio')
    st.session_state.ai_answer_helpful = st.radio("How helpful did you find the AI model's answer chain when trying to come to an answer?", options_helpful, horizontal=True, key='ai_answer_helpful_radio')
    st.session_state.ai_reasoning_chain_usage = st.radio("How often did you use the AI model’s reasoning chain to help answer the question?", options_frequency, horizontal=True, key='ai_reasoning_chain_usage_radio')
    st.session_state.ai_reasoning_chain_helpful = st.radio("How helpful did you find the AI model's reasoning chain when trying to come to an answer?", options_helpful, horizontal=True, key='ai_reasoning_chain_helpful_radio')
    st.session_state.interaction_usage = st.radio("How often did you use the interactions with the model  to help answer the question?", options_frequency, horizontal=True, key='interaction_usage_radio')
    st.session_state.interaction_helpfulness = st.radio("How helpful did you find the interactions with the model when trying to come to an answer?", options_helpful, horizontal=True, key='interaction_helpfulness_radio')
    st.session_state.explanation_usage = st.radio("How often did you use the AI model’s explanations to come to an answer?", options_frequency, horizontal=True, key='explanation_usage_radio')
    st.session_state.explanation_helpfulness = st.radio("How helpful did you find the AI model's explanations when trying to come to an answer?", options_helpful, horizontal=True, key='explanation_helpfulness_radio')

    if st.button("Next", key="ai_usage_questions_next"):
        if (
            st.session_state.ai_frequency == 'Select an Option' or
            st.session_state.ai_answer_usage == 'Select an Option' or
            st.session_state.ai_answer_helpful == 'Select an Option' or
            st.session_state.ai_reasoning_chain_usage == 'Select an Option' or
            st.session_state.ai_reasoning_chain_helpful == 'Select an Option' or
            st.session_state.interaction_usage == 'Select an Option' or
            st.session_state.interaction_helpfulness == 'Select an Option' or
            st.session_state.explanation_usage == 'Select an Option' or
            st.session_state.explanation_helpfulness == 'Select an Option'
        ):
            st.error("Please make sure to select an option for all questions before submitting.")
        else:
            end_time = datetime.now()
            st.session_state.time_spent = str((end_time - st.session_state.time_spent).total_seconds())
            # log data
            record_data_clear_state(['ai_frequency', 'ai_answer_usage', 'ai_answer_helpful', 'ai_reasoning_chain_usage', 'ai_reasoning_chain_helpful', 'interaction_usage', 'interaction_helpfulness', 'explanation_usage', 'explanation_helpfulness', 'time_spent'])
            st.session_state.qa_page = 'interactions'
            st.rerun()

def tasks_demand_questions():
    if 'time_spent' not in st.session_state:
        st.session_state.time_spent = datetime.now()

    st.title("Task Reflection Questions")
    st.subheader("Note: You must answer all of the questions here before clicking submit to be paid.  You cannot go back, please take your time answering these.")

    st.subheader("Reflect on how you feel after answering all of the questions")

    st.session_state.mental_demand = st.slider("How mentally demanding were the tasks?", 0, 100, step=5, key="mental_slider")
    st.session_state.success = st.slider("How successful were you in accomplishing what you were asked to do?", 0, 100, step=5, key='success_slider')
    st.session_state.effort = st.slider("How hard did you have to work to accomplish your level of performance?", 0, 100, step=5,key="effort_slider")
    st.session_state.pace = st.slider("How hurried or rushed were the pace of the tasks?", 0, 100, step=5, key="pace_slider")
    st.session_state.stress = st.slider("How insecure, discouraged, irritated, stressed, and annoyed were you?", 0, 100, step=5, key="stress_slider")

    st.subheader("Answer the following in terms of your preferences (not related to the main study)")  
    options = ['Select an Option', 'Strongly Disagree', 'Disagree', 'Somewhat Disagree', 'Neutral', 'Somewhat Agree', 'Agree', 'Strongly Agree'] 
    st.session_state.complex_to_simple = st.radio("I would prefer complex to simple problems.", options, horizontal=True, key="complex_to_simple_slider")
    st.session_state.thinking = st.radio("I like to have the responsibility of handling a situation that requires a lot of thinking.", options, horizontal=True, key="thinking_slider")
    st.session_state.thinking_fun = st.radio("Thinking is not my idea of fun.", options, horizontal=True, key="thinking_fun_slider")
    st.session_state.thought = st.radio("I would rather do something that requires little thought than something that is sure to challenge my thinking abilities.", options, horizontal=True, key="thought_slider")
    st.session_state.new_solutions = st.radio("I really enjoy a task that involves coming up with new solutions to problems.", options, horizontal=True, key="new_solutions_slider")
    st.session_state.difficulty = st.radio("I would prefer a task that is intellectual, difficult, and important to one that is somewhat important but does not require much thought.", options, horizontal=True, key="difficulty_slider")

    if st.button("Next", key="tasks_demand_questions_next"):
        if (
            st.session_state.complex_to_simple == 'Select an Option' or
            st.session_state.thinking == 'Select an Option' or
            st.session_state.thinking_fun == 'Select an Option' or
            st.session_state.thought == 'Select an Option' or
            st.session_state.new_solutions == 'Select an Option' or
            st.session_state.difficulty == 'Select an Option'
            ):
            st.error("Please make sure to select an option for all questions before submitting.")
        else:
            end_time = datetime.now()
            st.session_state.time_spent = str((end_time - st.session_state.time_spent).total_seconds())
            # log data
            record_data_clear_state( ['mental_demand', 'success', 'effort', 'pace', 'stress', 'complex_to_simple', 'thinking', 'thinking_fun', 'thought', 'new_solutions', 'difficulty', 'time_spent'], header=True, survey_type="FEEDBACK")
            st.session_state.qa_page = 'ai_usage'
            st.rerun()

def survey():
    load_hotjar()
    st.title("Reflection Questions & Feedback")

    # Initialize the page in session state if not already set
    if 'qa_page' not in st.session_state:
        st.session_state.qa_page = 'tasks_demand'

    # Create a placeholder for dynamic content
    placeholder = st.empty()

    # Control which set of questions to display
    with placeholder.container():
        if 'is_done' in st.session_state and st.session_state.is_done:
            finished()
        elif st.session_state.qa_page == 'tasks_demand':
            tasks_demand_questions()
        elif st.session_state.qa_page == 'ai_usage':
            ai_usage_questions()
        elif st.session_state.qa_page == 'interactions':
            interaction_questions()
        elif st.session_state.qa_page == 'frq':
            free_form_questions()
        elif st.session_state.qa_page =='complete':
            finished()
