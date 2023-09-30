import streamlit as st
import subprocess
import json
import pandas as pd
import os
import sys
from contextlib import contextmanager
from threading import current_thread
from io import StringIO


REPORT_CONTEXT_ATTR_NAME = "_report_ctx"

def initialize_session_state():
    session_state_keys = ['feedback_responses', 'user_input', 'analysis', 'score', 'upvotes', 'downvotes', 'form_submitted']
    default_values = [[], '', '', '', 0, 0, False]

    for key, default in zip(session_state_keys, default_values):
        if key not in st.session_state:
            st.session_state[key] = default

initialize_session_state()


if 'feedback_responses' not in st.session_state:
    st.session_state.feedback_responses = []
if 'user_input' not in st.session_state:
    st.session_state.user_input = ''
if 'analysis' not in st.session_state:
    st.session_state.analysis = ''
if 'score' not in st.session_state:
    st.session_state.score = ''
if 'upvotes' not in st.session_state:
    st.session_state.upvotes = 0
if 'downvotes' not in st.session_state:
    st.session_state.downvotes = 0
if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False


@contextmanager
def st_redirect(src, dst):
    placeholder = st.empty()
    output_func = getattr(placeholder, dst)

    with StringIO() as buffer:
        old_write = src.write

        def new_write(b):
            if getattr(current_thread(), REPORT_CONTEXT_ATTR_NAME, None):
                buffer.write(b)
                output_func(buffer.getvalue())
            else:
                old_write(b)

        try:
            src.write = new_write
            yield
        finally:
            src.write = old_write

@contextmanager
def st_stdout(dst):
    with st_redirect(sys.stdout, dst):
        yield

@contextmanager
def st_stderr(dst):
    with st_redirect(sys.stderr, dst):
        yield

def run_script(user_inputs):

    input_df = pd.DataFrame([{"text": text} for text in user_inputs])
    input_file = 'input_temp.jsonl'
    with open(input_file, 'w') as f:
        f.write(input_df.to_json(orient='records', lines=True))

    result = subprocess.run(['python', 'openai_example_parallel.py', '--input_file', input_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = result.stdout.decode('utf-8'), result.stderr.decode('utf-8')
    
    if os.path.exists(input_file):  # Cleanup
        os.remove(input_file)

    return stdout.splitlines(), stderr

from openai_example_parallel import process_requests

def get_analysis_and_score(user_input):
    # Create a DataFrame from the user inputs
    input_df = pd.DataFrame([{"text": text} for text in [user_input]])
    input_file = 'input_temp.jsonl'
    with open(input_file, 'w') as f:
        f.write(input_df.to_json(orient='records', lines=True))

    combined_df = process_requests(input_file)
    
    if os.path.exists(input_file):  # Cleanup
        os.remove(input_file)

    # Extract 'gpt-answer' from the DataFrame
    gpt_answer = combined_df['gpt-answer'].values[0]

    if " | " in gpt_answer:
        analysis, score = gpt_answer.split(" | ")
        return analysis, score

    return "No analysis found.", "No score provided."


@st.cache(suppress_st_warning=True)
def collect_feedback():
    feedback_questions = [
        "Was the response unclear or too vague?",
        "Did the response not address your query?",
        "Was the information incorrect?",
        "Was the response inappropriate?",
        "Any other reason?"
    ]

    # Initialize feedback questions in session state
    for question in feedback_questions:
        if question not in st.session_state:
            st.session_state[question] = "Select an option"

    try:
        with st.form(key='feedback_form'):
            for idx, question in enumerate(feedback_questions):
                options = ["Select an option", "Yes", "No"]
                response = st.selectbox(question, options, index=options.index(st.session_state[question]), key=f'question_{idx}')
                if response != "Select an option":
                    st.session_state.feedback_responses.append({question: response})

            if st.form_submit_button('Submit Feedback'):
                if len(st.session_state.feedback_responses) == len(feedback_questions):
                    with open("feedback.jsonl", "a") as f:
                        for feedback in st.session_state.feedback_responses:
                            f.write(json.dumps(feedback) + "\n")
                    st.write("Thank you for your feedback!")
                    st.session_state.form_submitted = True
                    st.experimental_rerun()

    except Exception as e:
        pass 

    return st.session_state.feedback_responses

def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True

@st.cache(allow_output_mutation=True)
def get_votes():
    return {"upvotes": 0, "downvotes": 0}


def app_chatbox():
    st.title('Veracity Checker - Chatbox')

    if 'user_input' not in st.session_state:
        st.session_state.user_input = ''

    user_input = st.text_area("Enter your text here", value=st.session_state.user_input)

    if 'analysis' not in st.session_state:
        st.session_state.analysis = ''
    if 'score' not in st.session_state:
        st.session_state.score = ''

    if st.button('Run Script') and user_input:
        st.session_state.analysis, st.session_state.score = get_analysis_and_score(user_input)

    # Displaying the analysis and score in separate boxes
    st.write(f"Analysis:")
    st.info(st.session_state.analysis)
    st.write(f"Score:")
    st.info(st.session_state.score)

    if 'upvotes' not in st.session_state:
        st.session_state.upvotes = 0
    if 'downvotes' not in st.session_state:
        st.session_state.downvotes = 0

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f'👍 Upvote'):
            st.session_state.upvotes += 1
            st.write("Thanks for your feedback!")
    with col2:
        if st.button(f'👎 Downvote'):
            st.session_state.downvotes += 1
            st.write("Thanks for your feedback!")
            collect_feedback()

app_chatbox()