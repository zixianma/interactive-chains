import streamlit as st
import json
from streamlit_float import *
from datetime import datetime
from pages.utils.utils import *
import pages.utils.logger as logger
import time
import os


def evaluation():
    # Transition at the very beginning
    if show_transition(
        stage_key="eval_transition_done",
        stage_title="the Evaluation Stage",
        instructions=(
            "In this stage, you'll answer 4 math questions to help us understand your math abilities. "
            "Please do your best and do NOT rely on external sources like Google or ChatGPT, as they may lead you to incorrect answers. Good luck!"
        ),
        button_label="Proceed to Evaluation"
    ):
        return

    st.title("Evaluation Stage")
    st.write(
        "Please answer the following math questions carefully. Remember to rely on your own knowledge and do not use external tools like ChatGPT or Google."
        "We really appreciate your honesty!"
    )

    # Ensure evaluation worksheet
    if 'evaluation' not in st.session_state:
        st.session_state['evaluation'] = logger.ensure_eval_worksheet()
    eval_sheet = st.session_state['evaluation']

    # Load questions
    evaluation_questions = load_data(path="data/evaluation_with_choices.jsonl")
    total_eval_questions = len(evaluation_questions)

    # Resume progress on first entry
    if "evaluation_index" not in st.session_state:
        records = eval_sheet.get_all_records()
        user_records = [r for r in records if r.get("Username") == st.session_state.username]
        st.session_state.evaluation_index = len(user_records)
        st.session_state.evaluation_results = [r.get("IsCorrect") in (True, "True", "true") for r in user_records]
        st.session_state.evaluation_submitted = False
        if st.session_state.evaluation_index >= total_eval_questions:
            st.session_state.evaluation_completed = True

    # Completed? show summary
    if st.session_state.get("evaluation_completed", False):
        correct_count = sum(st.session_state.evaluation_results)
        accuracy = correct_count / total_eval_questions if total_eval_questions else 0
        st.success("Thank you for completing the evaluation!")
        st.write(f"You answered {correct_count} out of {total_eval_questions} correctly. Accuracy: {accuracy*100:.1f}%")
        if accuracy < 0.75:
            st.error("Sorry, unfortunately your accuracy did not meet the required threshold to continue the study. Thank you very much for your participation—we really appreciate your effort!")
            st.write("Please close this window to exit the study.")
            st.stop()
        else:
            st.write("We appreciate your effort. Click below to continue to the main study.")
            if st.button("Continue to Study"):
                st.session_state.page = "instruction"
                st.rerun()
        return

    # Present current question
    current_idx = st.session_state.evaluation_index

    # Whenever we move to a new question, reset its start time
    if st.session_state.get("eval_prev_idx") != current_idx:
        st.session_state.eval_prev_idx = current_idx
        st.session_state.eval_question_start_time = datetime.now()
        # Also reset submission flag
        st.session_state.evaluation_submitted = False
        st.session_state.pop("submitted_answer", None)

    if current_idx < total_eval_questions:
        q = evaluation_questions[current_idx]
        st.subheader(f"Evaluation Question {current_idx+1} of {total_eval_questions}")
        st.write(q["question"])

        # Hide placeholder
        st.markdown(
            """
            <style>
                div[role=radiogroup] label:first-of-type {
                    visibility: hidden;
                    height: 0px;
                }
            </style>
            """, unsafe_allow_html=True
        )
        placeholder = "Select an answer"

        # Show radio or submitted answer
        if not st.session_state.evaluation_submitted:
            answer = st.radio(
                "Your answer",
                options=[placeholder] + q["Choices"],
                key=f"eval_{current_idx}",
                label_visibility="collapsed"
            )
        else:
            answer = st.session_state.submitted_answer
            st.write(f"Your answer: **{answer}**")

        # Submit button
        if not st.session_state.evaluation_submitted:
            if st.button("Submit", key=f"submit_eval_{current_idx}"):
                if answer is not None and answer != placeholder:
                    # Compute correctness
                    is_correct = (answer == q["correct_answer"])
                    st.session_state.evaluation_results.append(is_correct)
                    st.session_state.evaluation_submitted = True
                    st.session_state.submitted_answer = answer

                    # Compute elapsed time
                    time = (datetime.now() - st.session_state.eval_question_start_time).total_seconds()

                    # Log row: add elapsed as last column
                    row = [
                        st.session_state.username,
                        st.session_state.condition,
                        current_idx,
                        q["question"],
                        json.dumps(q["Choices"]),
                        answer,
                        q["correct_answer"],
                        is_correct,
                        time
                    ]
                    logger.write_eval_response(row)

                    # Immediate feedback
                    if is_correct:
                        st.success("Correct!")
                    else:
                        st.error("Incorrect!")
                    st.info(f"Correct Answer: {q['correct_answer']}")
                    st.markdown(f"**Explanation:** {q['gt_solution']}")
                else:
                    st.warning("Please select an answer before submitting.")
        else:
            st.button("Submit", key=f"submit_eval_{current_idx}", disabled=True)

        # Next button
        if st.session_state.evaluation_submitted:
            if st.button("Next", key=f"next_eval_{current_idx}"):
                st.session_state.evaluation_index += 1
                st.rerun()
        else:
            st.button(
                "Next",
                key=f"next_eval_disabled_{current_idx}",
                disabled=True,
                help="Please submit your answer first."
            )

    else:
        # All done: show final results
        correct_count = sum(st.session_state.evaluation_results)
        accuracy = correct_count / total_eval_questions if total_eval_questions else 0
        st.success("Thank you for completing the evaluation!")
        st.write(f"You answered {correct_count} out of {total_eval_questions} correctly. Accuracy: {accuracy*100:.1f}%")
        if accuracy < 0.75:
            st.error("Sorry, unfortunately your accuracy did not meet the required threshold to continue the study. Thank you very much for your participation—we really appreciate your effort!")
            st.write("Please close this window to exit the study.")
            st.stop()
        else:
            st.write("We appreciate your effort. Click below to continue to the main study.")
            if st.button("Continue to Study"):
                st.session_state.page = "instruction"
                st.rerun()
        return
