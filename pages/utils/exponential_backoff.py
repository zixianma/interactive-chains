import time
import random
from googleapiclient.errors import HttpError
import inspect
import streamlit as st

def exponential_backoff(api_call_func, *args, max_retries=5, max_backoff=64, **kwargs):
    """
    Implements exponential backoff with random jitter for Google Sheets API calls.
    Logs details like function name, arguments, retries, total time spent, and backoff time.
    
    :param api_call_func: The API function to call.
    :param max_retries: Maximum number of retries.
    :param max_backoff: Maximum backoff time in seconds.
    :return: The result of the API call if successful, or raises the last exception.
    """
    retries = 0  # Retry counter
    total_backoff_time = 0  # Track the total time spent on backoff
    total_time_spent = 0  # Track the total time spent (including execution and backoff)

    start_time = time.time()  # Start time of the overall operation

    # Get the function name for logging
    func_name = api_call_func.__name__ if hasattr(api_call_func, '__name__') else 'Unknown function'

    # Get the arguments passed to the function
    func_args = args
    func_kwargs = kwargs

    data = [func_name, func_args, func_kwargs]

    while retries < max_retries:
        try:
            # Call the API function with provided arguments
            result = api_call_func(*args, **kwargs)

            # Calculate total time spent on the entire operation
            total_time_spent = time.time() - start_time

            # Log the details of the API call
            print(f"API Call Function: {func_name}")
            print(f"Arguments: {func_args}, {func_kwargs}")
            print(f"Number of retries: {retries}")
            print(f"Total time spent (including retries): {total_time_spent:.2f} seconds")
            print(f"Total backoff time: {total_backoff_time:.2f} seconds")

            data.append(retries)
            data.append(total_time_spent)
            data.append(total_backoff_time)

            return result  # Return the API result

        except HttpError as e:
            # Check if it's a rate limit error or quota error (429 or 403)
            if e.resp.status == 429 or e.resp.status == 403:
                # Generate a random jitter of up to 1,000 milliseconds (1 second)
                random_jitter = random.uniform(0, 1)

                # Calculate the wait time: min((2^n + jitter), max_backoff)
                wait_time = min((2 ** retries) + random_jitter, max_backoff)
                
                # Log the retry attempt and wait time
                print(f"Quota exceeded. Retrying in {wait_time:.2f} seconds... (Retry {retries + 1}/{max_retries})")
                # data.append(f"Quota exceeded. Retrying in {wait_time:.2f} seconds... (Retry {retries + 1}/{max_retries})")

                # Wait for the calculated backoff time
                time.sleep(wait_time)

                # Add the wait time to the total backoff time
                total_backoff_time += wait_time

                # Increment the retry counter
                retries += 1
            else:
                # If it's not a rate limit or quota error, re-raise the error
                raise e

    # If all retries are exhausted, raise an exception
    total_time_spent = time.time() - start_time
    print(f"Max retries exceeded after {retries} retries and {total_time_spent:.2f} seconds.")
    print(f"Total backoff time: {total_backoff_time:.2f} seconds")
    # data.append(f"Max retries exceeded after {retries} retries and {total_time_spent:.2f} seconds. Total backoff time: {total_backoff_time:.2f} seconds.")
    # st.session_state.condition_counts_sheet.worksheet("Exponential Backoff Log").append_row(data)
    raise Exception("Max retries exceeded")
