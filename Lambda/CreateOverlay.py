import json
import boto3
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from io import BytesIO
import os

s3 = boto3.client('s3')

def wrap_text(text, width, font):
    text_lines = []
    text_line = []
    text = text.replace('\n', ' [br] ')
    words = text.split()
    font_size = font.getsize(text)

    for word in words:
        if word == '[br]':
            text_lines.append(' '.join(text_line))
            text_line = []
            continue
        text_line.append(word)
        w, h = font.getsize(' '.join(text_line))
        if w > width:
            text_line.pop()
            text_lines.append(' '.join(text_line))
            text_line = [word]

    if len(text_line) > 0:
        text_lines.append(' '.join(text_line))

    return text_lines


def lambda_handler(event, context):
    # TODO implement
    
    bucket_name = 'aws-shorts-source-file'
    source_key = 'Background/shorts-background.png'
    destination_dir = 'Background/Headers'
    
    #get details of video and question
    video_name = event['Records'][0]['dynamodb']['Keys']['VideoName']['S']
    question = event['Records'][0]['dynamodb']['NewImage']['Question']['S']
    index = event['Records'][0]['dynamodb']['Keys']['Index']['S']
    
    #get base image

    response_image = s3.get_object(Bucket=bucket_name,Key=source_key)['Body'].read()
    
    base_image = Image.open(BytesIO(response_image))

    draw = ImageDraw.Draw(base_image)
    font_mono= './fonts/NanumGothic.ttf'
    font = ImageFont.truetype(font_mono, 70)
    
    multiline = wrap_text(question, 900, font)
    
    W = 1080
    H = 1920
    white = (255,255,255)
    
    text_y = (H - len(multiline) * 80)/2 - 500

    for line in multiline:
        w, h = draw.textsize(line, font=font)
        text_x = (W-w)/2
        draw.text((text_x, text_y), text=line, font=font)
        text_y = text_y + 80

    buffer = BytesIO()
    base_image.save(buffer, format='png')
    buffer.seek(0)
    
    destination_key = f'{destination_dir}/{video_name}-{index}'
    s3.put_object(Bucket=bucket_name, Key=destination_key+'.png', Body=buffer, ContentType='image/png')
    
    
    return {
        'statusCode': 200,
        'body': json.dumps('Created Background Image')
    }
