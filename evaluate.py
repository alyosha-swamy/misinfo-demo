import pandas as pd
import argparse
import random
from sklearn.metrics import f1_score, accuracy_score

parser = argparse.ArgumentParser()
parser.add_argument('--experiment_name', type=str, help='Name of the experiment', default='base_multichoice')
args = parser.parse_args()

experiment_name = args.experiment_name

gpt_model = "gpt-4-0613"
temperature = 0.5 

base_path = '.'
combined_df = pd.read_json(f'{base_path}/{experiment_name}_{gpt_model}_temp{temperature}.jsonl', lines=True)

pd.set_option('display.max_colwidth', None)
#print(combined_df['gpt-answer'])

def to_number(input_str):
    try:
        input_str = float(input_str)
        return int(input_str)
    except:
        return random.randint(0,100) #'notnumber' #random.randint(0,100)

def to_binary(label, threshold):
    label = to_number(label)
    return 1 if label >= threshold else 0
    
def split_answer(answer):
    return answer.split('|')[0].lower().replace('score','').replace(':','').strip()
    
print(combined_df['label'].value_counts())




combined_df['label'] = combined_df.label.apply(to_number).apply(lambda x: to_binary(x,3))
combined_df['gpt-score'] = combined_df["gpt-answer"].apply(split_answer)
print(combined_df['gpt-score'].value_counts()[:20])
combined_df['gpt-score'] = combined_df["gpt-score"].apply(to_number)
combined_df = combined_df[combined_df['gpt-score'] != 'notnumber']
combined_df['gpt-score'] = combined_df["gpt-score"].apply(lambda x: to_binary(x,50))

combined_df['correct'] = (combined_df['gpt-score'] == combined_df['label']).astype(int)

print(f1_score(combined_df['label'], combined_df['gpt-score'], average='micro'))
print('acc', accuracy_score(combined_df['label'], combined_df['gpt-score']))

# print(combined_df['correct'].value_counts())
# print(combined_df[['text','gpt-score']][combined_df.correct != 1])



# sample_df = combined_df[combined_df['correct'] == 1].sample(30)
# sample_df = sample_df.append(combined_df[combined_df['correct'] == 0].sample(10))
# sample_df.to_csv('explainability_sample_3.csv', sep='\t')