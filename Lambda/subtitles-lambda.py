import boto3
import time
import json

def lambda_handler(event, context):
    # Extract bucket name and object key from the event notification
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    source_file_key = event['Records'][0]['s3']['object']['key']
    
    # Initialize Transcribe client
    transcribe = boto3.client('transcribe')
    
    # Start transcription job
    job_name = f'TranscriptionJob_{int(time.time())}'
    job_uri = f's3://{bucket_name}/{source_file_key}'
    output_key = source_file_key.replace('RAW', 'Subtitles').replace('.mp4', '.json')
    
    response = transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': job_uri},
        MediaFormat='mp4',
        Settings={
            'ShowSpeakerLabels': True,
            'MaxSpeakerLabels': 2,
        },
        OutputBucketName=bucket_name,
        OutputKey=output_key,
        LanguageCode='ko-KR',
        Subtitles={
            'Formats': ['srt']
        }
    )
  
    return {
        'statusCode': 200,
        'body': 'Transcription job started.'
    }
