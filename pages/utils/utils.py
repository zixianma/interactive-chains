import streamlit as st
import json
import random
from streamlit_float import *
import re
from datetime import datetime
import time
import pages.utils.logger as logger
import time
import os

@st.cache_data
def load_data(path="./data/training_questions.json"):
    """Loads the training and main-study questions from JSON or JSONL files."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    # Handle JSONL files
    if path.endswith(".jsonl"):
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                data.append(json.loads(line.strip()))
        return data

    # Handle standard JSON files
    elif path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {int(k): v for k, v in data.items()}

    else:
        raise ValueError("Unsupported file format. Please use .json or .jsonl")
    


def show_transition(stage_key, stage_title, instructions, button_label):
    """
    Displays a transition page for a given stage if not already done.

    Parameters:
      - stage_key: The key in session state that indicates if the transition is done.
      - stage_title: The large title to display.
      - instructions: A short text of instructions for the stage.
      - button_label: The label for the button to continue.
      
    Returns True if the transition screen was shown (and therefore the rest of the stage should be skipped).
    """
    if not st.session_state.get(stage_key, False):
        # Center the title in an h1 tag
        st.markdown(
            f"<h1 style='text-align: center;'>Hi, welcome to {stage_title}!</h1>",
            unsafe_allow_html=True
        )
        # Center the instructions with a larger font in an h2 tag
        st.markdown(
            f"<h2 style='text-align: center;'>{instructions}</h2>",
            unsafe_allow_html=True
        )
        # Use columns to center the button
        col1, col2, col3 = st.columns([1, 1, 2])
        with col3:
            if st.button(button_label):
                st.session_state[stage_key] = True
                st.rerun()
        return True
    return False