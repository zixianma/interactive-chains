import streamlit as st
import pandas as pd
from streamlit_float import *
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from pages.utils.exponential_backoff import exponential_backoff
    
# def write_to_user_sheet(data, answer_text=None):
#     sheet = st.session_state['user_worksheet']
#     if st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
#         answer_text = st.session_state.get("Answer in text", "")
#         row_data = data + [answer_text]
#     else:
#         row_data = data

#     exponential_backoff(sheet.append_row, data)
    
#     user_data_sheet = st.session_state['sheet']
#     all_actions_sheet = exponential_backoff(user_data_sheet.worksheet, 'Main Study')  
#     exponential_backoff(all_actions_sheet.append_row, row_data)  

# def write_to_user_sheet(data, answer_text=None):
#     sheet = st.session_state['user_worksheet']

#     if st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
#         # The main code already passes answer_text, so use the provided argument.
#         # This prevents confusion with session state variables.
#         row_data = data + [answer_text] 
#     else:
#         row_data = data
    
#     # Append the full, correctly formatted row to the user's worksheet
#     exponential_backoff(sheet.append_row, row_data)
    
#     # And also to the main 'Main Study' worksheet
#     user_data_sheet = st.session_state['sheet']
#     all_actions_sheet = exponential_backoff(user_data_sheet.worksheet, 'Main Study')
#     exponential_backoff(all_actions_sheet.append_row, row_data)

# ...existing code...
def write_to_user_sheet(data, answer_text=None):
    sheet = st.session_state['user_worksheet']

    if st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
        # The main code already passes answer_text, so use the provided argument.
        # This prevents confusion with session state variables.
        row_data = data + [answer_text] 
    else:
        row_data = data
    
    # Append the full, correctly formatted row to the user's worksheet
    exponential_backoff(sheet.append_row, row_data)
    
    # And also update (upsert) the main 'Main Study' worksheet: find row by Username + Question idx
    try:
        main_ws = exponential_backoff(st.session_state['sheet'].worksheet, 'Main Study')
        # Ensure header exists
        header = exponential_backoff(main_ws.row_values, 1)
        # find username and question idx columns (fall back to common names)
        def find_col(names):
            for n in names:
                if n in header:
                    return header.index(n) + 1
            return None
        username_col = find_col(["Username"])
        qidx_col=find_col(["Question idx","Question Index","Question ID"])
        # safe col values
        username = str(row_data[0])
        qidx_val = str(row_data[2]) if len(row_data) > 2 else ""
        # get column values
        user_col_vals = exponential_backoff(main_ws.col_values, username_col) if username_col else []
        qidx_col_vals = exponential_backoff(main_ws.col_values, qidx_col) if qidx_col else []
        # find matching row where both username and qidx match
        row_idx = None
        max_rows = max(len(user_col_vals), len(qidx_col_vals))
        for r in range(1, max_rows+1):
            u = user_col_vals[r-1] if r-1 < len(user_col_vals) else ""
            qv = qidx_col_vals[r-1] if r-1 < len(qidx_col_vals) else ""
            if u == username and qv == qidx_val:
                row_idx = r
                break
        if row_idx is None:
            # append new row
            exponential_backoff(main_ws.append_row, row_data)
        else:
            # update existing row cells for the provided columns
            for ci, val in enumerate(row_data, start=1):
                exponential_backoff(main_ws.update_cell, row_idx, ci, val)
    except Exception as e:
        print(f"Warning: could not update Main Study worksheet in write_to_user_sheet: {e}")

def log_user_action(sheet, user_id: str, action: str, text: str, question_id: int):
    """
    Logs user actions on the SAME ROW (question_id row) in the user's worksheet and
    also upserts an Action_/Text_ pair into the 'Main Study' worksheet for the same user+question.
    """
    # Basic validation and sanitization
    if sheet is None:
        raise TypeError("log_user_action: 'sheet' is None")
    if not hasattr(sheet, "worksheet"):
        raise TypeError(f"log_user_action: 'sheet' does not have worksheet(); got {type(sheet)}")
    if user_id is None:
        raise TypeError("log_user_action: 'user_id' is None")

    user_id = str(user_id)
    action = str(action)
    text = str(text) if text is not None and text != "" else "(empty)"
    qid_str = str(question_id)

    # Get or create user's worksheet
    try:
        ws = exponential_backoff(sheet.worksheet, user_id)
    except Exception:
        # create with a reasonable size
        ws = exponential_backoff(sheet.add_worksheet, title=user_id, rows=200, cols=50)
        # ensure a minimal header
        exponential_backoff(ws.update_cell, 1, 1, "Question ID")

    # --- Find row for this question (col 1 values) ---
    try:
        col1_vals = exponential_backoff(ws.col_values, 1)
    except Exception:
        col1_vals = []

    # If header present but not actual data, col1_vals may contain only header.
    if qid_str in col1_vals:
        row_idx = col1_vals.index(qid_str) + 1  # gspread is 1-indexed
    else:
        # append new row at the end (next empty row)
        row_idx = len(col1_vals) + 1
        exponential_backoff(ws.update_cell, row_idx, 1, qid_str)

    # --- Determine next Action/Text index by scanning header row (user sheet) ---
    try:
        header = exponential_backoff(ws.row_values, 1)
    except Exception:
        header = []

    # Find existing Action_# headers
    max_action_n = 0
    for h in header:
        if isinstance(h, str) and h.startswith("Action_"):
            try:
                n = int(h.split("_", 1)[1])
                if n > max_action_n:
                    max_action_n = n
            except Exception:
                continue

    # get current row values 
    try:
        row_vals = exponential_backoff(ws.row_values, row_idx)
    except Exception:
        row_vals = []

    next_action_n = None
    for i in range(1, max_action_n + 1):
        act_name = f"Action_{i}"
        txt_name = f"Text_{i}"
        if act_name in header:
            # if Text_i header exists, check the cell for this row; otherwise treat as empty and reuse
            if txt_name in header:
                txt_col = header.index(txt_name) + 1
                val = row_vals[txt_col - 1] if len(row_vals) >= txt_col else ""
                if (val is None) or (str(val).strip() == "") or (str(val).strip() == "(empty)"):
                    next_action_n = i
                    break
            else:
                next_action_n = i
                break

    if next_action_n is None:
        next_action_n = max_action_n + 1

    # If we're going to reuse an existing Action_i, adjust the local header slice so that
    # subsequent code which uses len(header)+1 for the action column points to the existing column.
    if next_action_n <= max_action_n:
        try:
            existing_action_idx = header.index(f"Action_{next_action_n}") + 1
            # action_col = len(header) + 1 equals existing_action_idx
            header = header[: existing_action_idx - 1]
        except Exception:
            pass

    # Determine columns where to write new Action and Text headers/data (user sheet)
    action_col = len(header) + 1
    text_col = len(header) + 2

    # Write header names (Action_#, Text_#) and data (user sheet)
    exponential_backoff(ws.update_cell, 1, action_col, f"Action_{next_action_n}")
    exponential_backoff(ws.update_cell, 1, text_col, f"Text_{next_action_n}")
    exponential_backoff(ws.update_cell, row_idx, action_col, action)
    exponential_backoff(ws.update_cell, row_idx, text_col, text)

    # --- Also upsert same Action/Text into Main Study worksheet for this user+question ---
    try:
        main_ws = exponential_backoff(sheet.worksheet, 'Main Study')
        main_header = exponential_backoff(main_ws.row_values, 1)
        # find username and question idx columns in main sheet
        def find_col(names):
            for n in names:
                if n in main_header:
                    return main_header.index(n) + 1
            return None
        username_col = find_col(["Username"])
        qidx_col = find_col(["Question idx","Question Index","Question ID"])
        print(f"[DEBUG] Username col={username_col}, Qidx col={qidx_col}")

        username = user_id
        qidx_val = qid_str

        user_col_vals = exponential_backoff(main_ws.col_values, username_col) if username_col else []
        qidx_col_vals = exponential_backoff(main_ws.col_values, qidx_col) if qidx_col else []

        # find matching row where both username and qidx match
        row_idx_main = None
        max_rows = max(len(user_col_vals), len(qidx_col_vals))
        for r in range(1, max_rows+1):
            u = user_col_vals[r-1] if r-1 < len(user_col_vals) else ""
            qv = qidx_col_vals[r-1] if r-1 < len(qidx_col_vals) else ""
            if u == username and qv == qidx_val:
                row_idx_main = r
                break

        if row_idx_main is None:
            # create minimal row with username and question idx so actions have a row to update
            new_row = []
            # ensure we have enough columns up to username and qidx positions
            max_header_idx = max((username_col or 1), (qidx_col or 2))
            # fill placeholders for columns before username and question idx
            for _ in range(max_header_idx):
                new_row.append("")
            # place username and qidx in their correct header positions if known, else first two cols
            if username_col and qidx_col:
                # build row of length = len(main_header)
                new_row = [""] * len(main_header)
                new_row[username_col - 1] = username
                new_row[qidx_col - 1] = qidx_val
            else:
                new_row = [username, qidx_val]
            exponential_backoff(main_ws.append_row, new_row)
            # refresh columns and compute new row_idx_main
            user_col_vals = exponential_backoff(main_ws.col_values, username_col) if username_col else []
            qidx_col_vals = exponential_backoff(main_ws.col_values, qidx_col) if qidx_col else []
            for r in range(1, max(len(user_col_vals), len(qidx_col_vals)) + 1):
                u = user_col_vals[r-1] if r-1 < len(user_col_vals) else ""
                qv = qidx_col_vals[r-1] if r-1 < len(qidx_col_vals) else ""
                if u == username and qv == qidx_val:
                    row_idx_main = r
                    break

        # compute next action number on main sheet by scanning headers
        max_action_n_main = 0
        for h in main_header:
            if isinstance(h, str) and h.startswith("Action_"):
                try:
                    n = int(h.split("_", 1)[1])
                    if n > max_action_n_main:
                        max_action_n_main = n
                except Exception:
                    continue
        next_action_n_main = max_action_n_main + 1

        action_col_main = len(main_header) + 1
        text_col_main = len(main_header) + 2

        # write headers and data to main sheet
        exponential_backoff(main_ws.update_cell, 1, action_col_main, f"Action_{next_action_n_main}")
        exponential_backoff(main_ws.update_cell, 1, text_col_main, f"Text_{next_action_n_main}")
        exponential_backoff(main_ws.update_cell, row_idx_main, action_col_main, action)
        exponential_backoff(main_ws.update_cell, row_idx_main, text_col_main, text)

    except Exception as e:
        print(f"Warning: could not update Main Study worksheet in log_user_action: {e}")

    # Optional: small print for server logs
    print(f"Logged for {user_id}: {action} - {text} (Question {qid_str})")
#make it to only change the last row?
def write_survey_response(data, sheet, key_list):
    responses = []
    responses.append(st.session_state.username)
    for key in key_list:
        value = data[key]
        if value is not None:
            # print(f'response: {key} , {value}')
            responses.append(value)
    exponential_backoff(sheet.append_row, responses)

def create_user_worksheet():
    sheet = st.session_state['sheet']
    try:
        worksheet = exponential_backoff(sheet.worksheet, st.session_state.username)  
    except gspread.exceptions.WorksheetNotFound:
        # Create a new worksheet for the user if it doesn't exist
        worksheet = exponential_backoff(sheet.add_worksheet, title=st.session_state.username, rows=100, cols=20)  
        
        if st.session_state.condition.find("verifiasble") > -1:
            header_list = []  # Not implement yet
        elif st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
            header_list = ["Username", "Condition", "Question idx", "Model Answer", "Step 1", "Step 2", "Helpfulness", "Gt Answer", "Time Spent", "Question Answered", "Question ID", "Answer in text"]
        else:
             header_list = ["Username", "Condition", "Question idx", "Model Answer", "Step 1", "Step 2", "Helpfulness", "Gt Answer", "Time Spent", "Question Answered", "Question ID"]
        
        exponential_backoff(worksheet.append_row, header_list)  
    else:
        # Worksheet already exists: make sure header contains "Answer in text"
        try:
            existing_headers = exponential_backoff(worksheet.row_values, 1)
        except Exception:
            existing_headers = []

        if "Answer in text" not in existing_headers and st.session_state.condition in ["E. Editable Local Suggestion", "F. Editable Global Suggestion"]:
            # Append the missing header at the end of the header row
            col_to_write = len(existing_headers) + 1
            exponential_backoff(worksheet.update_cell, 1, col_to_write, "Answer in text")
    return worksheet


def ensure_demo_worksheet():
    sheet = st.session_state['sheet']
    try:
        # Try to get the "Demographics" worksheet
        demographics_sheet = exponential_backoff(sheet.worksheet, "Demographics")  
    except gspread.exceptions.WorksheetNotFound:
        # If it doesn't exist, create it
        demographics_sheet = exponential_backoff(sheet.add_worksheet, title="Demographics", rows=100, cols=20)  
        # Add a header row for the demographics sheet
        exponential_backoff(demographics_sheet.append_row, ["Username", "Gender", "Self-Described Gender", "Race/Ethnicity", "Other Race/Ethnicity", "Age", "Job Title"])  
    
    return demographics_sheet
        

def write_demo_response(data):
    print(st.session_state)
    demo_worksheet = st.session_state['demographics']
    
    responses = [tuple[1] for tuple in data]
    exponential_backoff(demo_worksheet.append_row, responses)
    

def ensure_eval_worksheet():
    sheet = st.session_state['sheet']
    try:
        # Try to get the "Evaluation" worksheet
        eval_sheet = exponential_backoff(sheet.worksheet, "Evaluation")
    except gspread.exceptions.WorksheetNotFound:
        # Create the eval sheet if not found
        eval_sheet = exponential_backoff(sheet.add_worksheet, title="Evaluation", rows=100, cols=20)
        # Add a header row for the eval sheet
        exponential_backoff(eval_sheet.append_row, ["Username", "Condition", "Question idx", "Question Answered", "Choices", "Chosen Answer", "gt Answer", "IsCorrect", "Time"])
    
    return eval_sheet


def write_eval_response(data):
    print(st.session_state)
    eval_worksheet = st.session_state['evaluation']
    
    # responses = [tuple[1] for tuple in data]
    exponential_backoff(eval_worksheet.append_row, data)


