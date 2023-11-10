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

def evaluate_misinformation(statement: str, api_key: str) -> Dict[str, object]:
    prompt = f'Evaluate the following statement: "{statement}". \
Provide an analysis of the statement and rate its truthfulness on a scale from 0 to 30. \
Consider the following metrics: Verifiability, Sourcing, Logical Consistency, Relevance, Completeness, Bias, Clarity, Safety, User Understanding, Fluency. \
Do not begin your response with a number. First write your analysis, then write a vertical bar "|", \
then finally state your overall truthfulness score and another vertical bar "|", \
followed by your internal scores in the format Verifiability:1/3|Sourcing:2/3|...Provide you explanation first without considering the metrics, use them only for your score'

    openai.api_key = api_key

    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}],
        max_tokens=300,
        n=2  # Get top 2 responses
    )

    # Extract the top 2 responses
    analysis_1 = response['choices'][0]['message']['content'].strip()
    analysis_2 = response['choices'][1]['message']['content'].strip()

    # Split the first response to get the analysis, the score, and the internal_scores
    parts = analysis_1.split("|", 2)
    if len(parts) == 3:
        analysis_1, score, internal_scores_str = parts
    else:
        st.error("The analysis doesn't contain enough information.")

    internal_scores = {}
    for item in internal_scores_str.split("|"):
        if ":" in item:
            metric, value = item.split(":", 1)
            internal_scores[metric.strip()] = value.strip()

    return {
        'analysis_1': analysis_1.strip(),
        'analysis_2': analysis_2.strip(),
        'score': score,
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

        # Create two columns
        col1, col2 = st.columns(2)

        # Write the analyses in each column
        col1.write(f"Analysis 1: {result['analysis_1']}")
        col2.write(f"Analysis 2: {result['analysis_2']}")

        # Radio button group for user to select one of the analyses
        selected_analysis = st.radio(
            "Select the analysis you agree with:",
            ('Analysis 1', 'Analysis 2')
        )

        st.write(f"Internal Scores: {result['internal_scores']}")
        st.write(f"Truthfulness Score: {result['score']}")

        # Rest of your code...

        # Add selected_analysis to feedback_data
        feedback_data = {
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_prompt": statement,
            "selected_analysis": selected_analysis,
            "gpt_analysis": result['analysis_1'] if selected_analysis == 'Analysis 1' else result['analysis_2'],
            "gpt_score": result['score'],
            "gpt_internal_scores": result['internal_scores'],
            "feedback_score": st.session_state.feedback_score,
            "form_feedback_questions": st.session_state.form_feedback_questions,
            "user_feedback": st.session_state.user_feedback
        }
        save_feedback(feedback_data)
    else:
        st.warning('Please enter a statement for evaluation.')
