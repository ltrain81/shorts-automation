import boto3
from io import BytesIO
from datetime import timedelta, datetime
import json
import time

s3 = boto3.client('s3')
mediaconvert = boto3.client('mediaconvert', endpoint_url='https://lxlxpswfb.mediaconvert.us-east-1.amazonaws.com')

def create_new_video(video_name, section_index, duration):
    
    bucket_name = 'aws-shorts-source-file'
    input_file = f'FHD-Output/{video_name}/{video_name}-{section_index}.mp4'
    output_location = f'FinalOutput/{video_name}'
    
    duration = int(duration)
    
    background_file = f's3://aws-shorts-source-file/Background/Headers/{video_name}-{section_index}.png'
    
    # Create MediaConvert job
    
    #need to add Cropping Selection Dynamically
    response = mediaconvert.create_job(
        Role='arn:aws:iam::939021814303:role/service-role/MediaConvert_Default_Role',
        JobTemplate='AWSShorts',  # Replace 'Template' with your MediaConvert job template ARN
        Settings={
            'Inputs': [
                {
                    'FileInput': f's3://aws-shorts-source-file/{input_file}'
                },
                {
                    'FileInput': f's3://aws-shorts-source-file/Ending/Ending.mov',
                    'InputClippings': [
                        {
                            'StartTimecode': '00:00:00:00',
                            'EndTimecode': '00:00:03:00'
                        }
                    ]
                }
            ],
            'OutputGroups': [
                {
                    'OutputGroupSettings': {
                        'FileGroupSettings': {
                            'Destination': f's3://aws-shorts-source-file/{output_location}/{video_name}-{section_index}'
                        }
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
                                                'Duration': duration
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
    
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    source_file_key = event['Records'][0]['s3']['object']['key']
    
    split_key= source_file_key.split('/')
    file_name = split_key[-1]
    
    dashIndex = file_name.rfind('-')
    video_name = file_name[:dashIndex]
    index = file_name[dashIndex+1:-4]
    
    dynamodb = boto3.resource('dynamodb')
    shorts_table = dynamodb.Table('AWS-Shorts')

    response = shorts_table.get_item(
        Key={
            'VideoName': video_name,
            'Index': index
        }
    )
    
    item = response['Item']
    highlight_script = item["Text"]
    higlight_hook = item["Question"]
    duration = item["duration"]
    
    create_new_video(video_name, index, duration)
    
    return {
        'statusCode': 200,
        'body': 'Processing complete'
    }
