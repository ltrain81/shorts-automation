import json
import boto3
import csv
import botocore
import datetime

s3 = boto3.client('s3')
    
my_config = botocore.config.Config(
    connect_timeout=1000,
    read_timeout=1000,
)

bedrock = boto3.client(service_name='bedrock-runtime', config=my_config)
dynamodb = boto3.resource('dynamodb')
shorts = dynamodb.Table('AWS-Shorts')

def lambda_handler(event, context):
    # TODO implement
    
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    source_file_key = event['Records'][0]['s3']['object']['key']
    split_key = source_file_key.split('/')
    file_name = split_key[-1]
    file_name = file_name.split('.')[0]
    
    today = str(datetime.date.today())
    
    if source_file_key.endswith('.json'):
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=bucket_name, Key=source_file_key)
        transcript_json = json.load(response['Body'])
        script = transcript_json['results']['transcripts'][0]['transcript']
        
    else:
        return {
            'statusCode': 400,
            'body': 'File format not JSON'
        }
        
    body = json.dumps({"prompt": f"""\n\nHuman: 
- Below is a transcript of a video. 
- Pick out the highlights that depict the most important parts of this script.
    
{script}
    
- Need 5 highlights.
- Don't summarize and just give the response in the original script.
- Pick out the highlights that depict the most important parts of this script. 

- Give it to me in well-formatted JSON as below
{{
    "highlight1":{{
    "text":"",
    "question":""
    }}
}}
    
- Add a rhetorical question for each highlight in Korean. Less than 7 words.
- One Highlight should have more than 200 words.
- Never change a single letter or order of words from the orginal script
\n\nAssistant:""", "max_tokens_to_sample": 3000,
        "temperature": 0, "top_p": 0, "top_k": 250, "stop_sequences":  ["\n\nHuman:"],
        }, ensure_ascii=False )

    response = bedrock.invoke_model(
        accept='*/*',
        body=body,
        contentType='application/json',
        modelId='anthropic.claude-v2:1'
    )
    
    response_body = json.loads(response.get('body').read())
    highlights = response_body['completion']
    
    startIndex = highlights.find('{')
    endIndex = highlights.rfind('}')

    
    full_json = json.loads(highlights[startIndex:endIndex+1])
    
    parsed_jsons = []
    for key, value in full_json.items():
        temp_json = {key: value}
        parsed_jsons.append(temp_json)
    
    i = 1
    for parsed_json in parsed_jsons:
        highlight = dict()
        entryname = "highlight" + str(i)
        highlight["Text"] = parsed_json[entryname]["text"]
        highlight["Question"] = parsed_json[entryname]["question"]
        highlight["Index"] = str(i)
        highlight["VideoName"] = file_name
        shorts.put_item(Item=highlight)
        i = i + 1 
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }