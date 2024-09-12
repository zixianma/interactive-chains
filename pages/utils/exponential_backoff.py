import time
import random
from googleapiclient.errors import HttpError

# TODO: See # number of times this is called - log to sheet? potential load time as well

def exponential_backoff(api_call_func, *args, max_retries=5, max_backoff=64, **kwargs):
    """
    Implements exponential backoff with random jitter for Google Sheets API calls.
    
    :param api_call_func: The API function to call.
    :param max_retries: Maximum number of retries.
    :param max_backoff: Maximum backoff time in seconds.
    :return: The result of the API call if successful, or raises the last exception.
    """
    backoff_time = 1  # Initial backoff time in seconds
    retries = 0  # Retry counter

    while retries < max_retries:
        try:
            # Call the API function with provided arguments
            return api_call_func(*args, **kwargs)
        
        except HttpError as e:
            # Check if it's a rate limit error or quota error
            if e.resp.status == 429 or e.resp.status == 403:
                # Generate a random jitter of up to 1,000 milliseconds (1 second)
                random_jitter = random.uniform(0, 1)

                # Calculate the wait time: min((2^n + jitter), max_backoff)
                wait_time = min((2 ** retries) + random_jitter, max_backoff)
                
                # Log the retry attempt
                print(f"Quota exceeded. Retrying in {wait_time:.2f} seconds...")

                # Wait for the calculated backoff time
                time.sleep(wait_time)
                
                # Increment the retry counter
                retries += 1
            else:
                # If it's not a rate limit or quota error, re-raise the error
                raise e

    # If all retries are exhausted, raise the last exception
    raise Exception("Max retries exceeded")
