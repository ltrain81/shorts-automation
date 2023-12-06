import boto3
from io import BytesIO
from datetime import timedelta
from pysrt import SubRipFile
import json
import time

s3 = boto3.client('s3')
mediaconvert = boto3.client('mediaconvert', endpoint_url='https://lxlxpswfb.mediaconvert.us-east-1.amazonaws.com')

def find_timeframes_for_script(highlight_script, words_with_timestamp):

    initial_script = highlight_script
    highlight = highlight_script
    short_start = -1
    short_end = -1
    started = False
    full_highlight_found = False

    for item in words_with_timestamp:
        word = item["alternatives"][0]["content"]
        if not full_highlight_found and highlight.strip().startswith(word):
            # Ensure the word is found at the beginning of the current highlight script after stripping spaces
            started = True
            
            word = word.lstrip()
            highlight = highlight[len(word):].lstrip()  # Remove the found word and strip leading spaces
        
            if item["type"] == "pronunciation":
                if short_start == -1:
                    short_start = item["start_time"]
                short_end = item["end_time"]
                
            if not highlight.strip():
                # Full highlight script found
                full_highlight_found = True
        
        else:
            highlight = initial_script
            started = False
            short_start = -1
            short_end = -1
        
        if full_highlight_found:
            break
        
    return [short_start, short_end]


def extract_scripts_with_timestamps(video_name):
    json_object = s3.get_object(Bucket='aws-shorts-source-file', Key=f'mukbang/Subtitles/{video_name}.json')
    json_content = json.load(json_object['Body'])
    words_with_timestamp = json_content["results"]["items"]
    
    return words_with_timestamp

# Remaining code for video creation...

def convert_seconds_to_timecode(seconds):
    seconds = float(seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining_seconds = int(seconds % 60)
    frames = int((seconds - int(seconds)) * 25)  # Assuming 25 frames per second, adjust if needed

    return "{:02d}:{:02d}:{:02d}:{:02d}".format(hours, minutes, remaining_seconds, frames)


def create_new_video(video_name, section_index, timeframes):
    
    if len(timeframes) != 2:
        raise ValueError("Invalid timeframes format. Expected [start_time, end_time].")
    
    start_time_sec, end_time_sec = timeframes
    start_time_convert = convert_seconds_to_timecode(start_time_sec)
    end_time_convert = convert_seconds_to_timecode(end_time_sec)

    input_file = f'mukbang/RAW/{video_name}.mp4'
    output_location = 'mukbang/Output/'
    
    background_file = f's3://aws-shorts-source-file/Background/Headers/{video_name}-{section_index}.png'

    # Create MediaConvert job
    response = mediaconvert.create_job(
        Role='arn:aws:iam::939021814303:role/service-role/MediaConvert_Default_Role',
        JobTemplate='AWSShorts',  # Replace 'Template' with your MediaConvert job template ARN
        Settings={
            'Inputs': [
                {
                    'FileInput': f's3://aws-shorts-source-file/{input_file}',
                    'InputClippings': [
                        {
                            'StartTimecode': start_time_convert,
                            'EndTimecode': end_time_convert
                        }
                    ]
                }
            ],
            'OutputGroups': [
                {
                    'OutputGroupSettings': {
                        'FileGroupSettings': {
                            'Destination': f's3://aws-shorts-source-file/{output_location}/{video_name}/{video_name}-{section_index}'
                        },
                    },
                    'Outputs':[
                        {
                            'VideoDescription':{
                                'VideoPreprocessors': {
                                    'ImageInserter': {
                                        'InsertableImages': [
                                            {
                                                'Width': 1080,
                                                'Height': 1920,
                                                'Opacity': 100,
                                                'ImageInserterInput': background_file,
                                                'ImageX': 0,
                                                'ImageY': 0,
                                                'Layer': 1,
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    ]
                }
            ]
        }
    )

    return response



# Lambda handler function
def lambda_handler(event, context):
    
    time.sleep(3)
    
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    source_file_key = event['Records'][0]['s3']['object']['key']
    split_key= source_file_key.split('/')
    file_name = split_key[-1]
    dashIndex = file_name.rfind('-')
    video_name = file_name[:dashIndex]
    index = file_name[dashIndex+1:-4]
    
    dynamodb = boto3.resource('dynamodb')
    shorts_table = dynamodb.Table('AWS-Shorts')
    
    print(video_name)
    print(index)

    response = shorts_table.get_item(
        Key={
            'VideoName': video_name,
            'Index': index
        }
    )

    item = response['Item']
    highlight_script = item["Text"]
    higlight_hook = item["Question"]
    
    
    words_with_timestamp = extract_scripts_with_timestamps(video_name)
    timeframe = find_timeframes_for_script(highlight_script, words_with_timestamp)
    
    print(timeframe)
    
    create_new_video(video_name, index, timeframe)
    
    return {
        'statusCode': 200,
        'body': 'Processing complete'
    }
