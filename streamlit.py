import streamlit as st
import openai
from datetime import datetime
from typing import Dict
import json
import os
import re
from dotenv import load_dotenv

api_key = st.secrets["api_key"]


default_session_state = {
    'feedback_score': None,
    'form_feedback_questions': {},
    'user_feedback': ""
}

for key, value in default_session_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Function to evaluate misinformation
def evaluate_misinformation(statement: str, api_key: str) -> Dict[str, object]:
    prompt = f'Evaluate the following statement: "{statement}". \
Provide an analysis of the statement and rate its truthfulness on a scale from 0 to 30. \
Consider the following metrics: Verifiability, Sourcing, Logical Consistency, Relevance, Completeness, Bias, Clarity, Safety, User Understanding, Fluency. \
Do not begin your response with a number. First write your analysis, then write a vertical bar "|", \
then finally state your overall truthfulness score and another vertical bar "|", \
followed by your internal scores in the format Verifiability:1/3|Sourcing:2/3|...'
    openai.api_key = api_key

    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}],
        max_tokens=300
    )
    out_of = None
    output_text = response['choices'][0]['message']['content'].strip()
    analysis, score, internal_scores_str = output_text.split("|", 2)

    # Split the output to get the analysis, the score, and the internal_scores

    
    internal_scores = {}
    for item in internal_scores_str.split("|"):
        if ":" in item:
            metric, value = item.split(":")
            internal_scores[metric.strip()] = value.strip()

    return {
        'analysis': analysis.strip(),
        'score': score,
        'out_of': out_of,
        'internal_scores': internal_scores
    }


def save_feedback(feedback_data):
    # Load existing data
    existing_data = []
    if os.path.exists('feedback_data.json'):
        with open('feedback_data.json', 'r') as f:
            if os.stat('feedback_data.json').st_size != 0:  # Check if file is not empty
                existing_data = json.load(f)

    # Append new feedback
    existing_data.append(feedback_data)

    # Write back to file
    with open('feedback_data.json', 'w') as f:
        json.dump(existing_data, f, indent=4)

    st.write("Feedback successfully saved.")


# Initialize Streamlit
st.title('Misinformation Evaluator')
st.caption("Analyze the truthfulness of statements and provide your feedback.")

statement = st.text_input("Enter the statement you want to evaluate:")

if 'evaluate_statement' not in st.session_state:
    st.session_state.evaluate_statement = False

if st.button('Evaluate Statement', on_click=lambda: setattr(st.session_state, 'evaluate_statement', True)):
    pass

if st.session_state.evaluate_statement:
    if statement:
        result = evaluate_misinformation(statement, api_key)

        st.write(f"Analysis: {result['analysis']}")
        st.write(f"Internal Scores: {result['internal_scores']}")
        st.write(f"Truthfulness Score: {result['score']} out of {result['out_of']}")

    st.write("Do you agree with the analysis?")
    if 'agree' not in st.session_state:
        st.session_state.agree = False
    if 'disagree' not in st.session_state:
        st.session_state.disagree = False

    if st.button("👍", on_click=lambda: setattr(st.session_state, 'agree', True)):
        st.session_state.disagree = False
    if st.button("👎", on_click=lambda: setattr(st.session_state, 'disagree', True)):
        st.session_state.agree = False

    if st.session_state.agree:
        st.session_state.feedback_score = "Agree"
    if st.session_state.disagree:
        st.session_state.feedback_score = "Disagree"

    
    with st.form(key='feedback_form'):
        questions = [
            'Was the response clear and understandable?', 
            'Did the response answer your query?', 
            'Was the information provided accurate?', 
            'Was the response appropriate?'
        ]
        responses = {question: st.selectbox(question, ['Select an option', 'Yes', 'No']) for question in questions}
        additional_feedback = st.text_area("Please provide additional feedback:")
        submit_button = st.form_submit_button(label='Submit Feedback')

        if submit_button:
            if all(response != 'Select an option' for response in responses.values()):
                st.session_state['form_feedback_questions'] = responses
                st.session_state['user_feedback'] = additional_feedback
            else:
                st.warning('Please respond to all feedback questions.')

    # Check if all necessary data is loaded in
    if 'feedback_score' in st.session_state and 'form_feedback_questions' in st.session_state and 'user_feedback' in st.session_state:
        feedback_data = {
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_prompt": statement,
            "gpt_analysis": result['analysis'],
            "gpt_score": result['score'],
            "gpt_internal_scores": result['internal_scores'],
            "feedback_score": st.session_state.feedback_score,
            "form_feedback_questions": st.session_state.form_feedback_questions,
            "user_feedback": st.session_state.user_feedback
        }
        save_feedback(feedback_data)
    else:
        st.warning('Please enter a statement for evaluation.')
