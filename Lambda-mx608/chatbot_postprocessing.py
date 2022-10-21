import json
import boto3
import datetime
import pprint
import requests
import random
import argparse
import time
import sys
from botocore.exceptions import ClientError
# import amazondax
from boto3.dynamodb.conditions import Key
# from requests_aws4auth import AWS4Auth

NUM_RECOMEND = 3

def poll_sqs():
    client = boto3.client("sqs")    
    response = client.receive_message(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/578480262707/chatBotTaskQueue",
        MaxNumberOfMessages=1,
        VisibilityTimeout=10,
        WaitTimeSeconds=10,
        MessageAttributeNames=[
            'All'
        ]
    )
    
    return response['Messages']

def delete_sqs(receipt_handle):
    client = boto3.client("sqs")
    response = client.delete_message(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/578480262707/chatBotTaskQueue",
        ReceiptHandle=receipt_handle,
    )

    return response

def query_es(cuisine):
    
    region = 'us-east-1'
    service = 'es'
#     credentials = boto3.Session().get_credentials()
#     awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    host = 'https://search-cloudcomputing-o4clej3mxqwimr4cg7yjgpxpzu.us-east-1.es.amazonaws.com' 
    index = 'restaurants'
    url = host + '/' + index + '/_search'
    
    # Put the user query into the query DSL for more accurate search results.
    # Note that certain fields are boosted (^).
    query = {
        "size": 1000,
        "query": {
            "multi_match": {
                "query": cuisine,
                "fields": ["cuisineType"]
            }
        }
    }

    # Elasticsearch 6.x requires an explicit Content-Type header
    headers = { "Content-Type": "application/json" }

    # Make the signed HTTP request. Hide user info on purpose!!!
    response = requests.get(url, auth=('xx', 'xx'), data=json.dumps(query), headers=headers)
    
    return json.loads(response.text)

def pick_id(data_es):
    
    id_list=[]
    res_list = data_es['hits']['hits']
    
    while len(id_list) < NUM_RECOMEND:
        rid = int(random.random()*len(res_list))
        bid = res_list[rid]['_source']['businessID']
        if res_list[rid]['_source']['businessID'] not in id_list:
            id_list.append(res_list[rid]['_source']['businessID'])
        
    return id_list

def retrieve_detail(businessID_list):
    
    dyn_resource = boto3.resource('dynamodb')
    table = dyn_resource.Table('yelp-restaurants')
    
    result_list=[]
    for bid in businessID_list:
        item = table.get_item(Key={
                            'businessID': bid
                            })
        result_list.append(item)
        
    return result_list

def construct_response(client_info, restaurant_list):
    
    cuisine = client_info['cuisine'] #pass in 'body'
    num_of_ppl = client_info['numberOfPeople']
    date = client_info['date']
    time = client_info['time']
    restaurant1 = '1. ' + restaurant_list[0]['Item']['name'] + ', '+ restaurant_list[0]['Item']['address'] + '; '
    restaurant2 = '2. ' + restaurant_list[1]['Item']['name'] + ', '+ restaurant_list[1]['Item']['address'] + '; '
    restaurant3 = '3. ' + restaurant_list[2]['Item']['name'] + ', '+ restaurant_list[2]['Item']['address'] + '. '
    
    message = "Hello! Here are my {0} restaurant suggestions for {1} people,"\
              " for {2} at {3}: {4}{5}{6} Enjoy your meal!"\
              .format(cuisine,num_of_ppl,date,time,restaurant1,restaurant2,restaurant3)
    
    return message

def send_email(recipient, message):
    
    SENDER = "alicespring2022@gmail.com"
    AWS_REGION = "us-east-1"
    SUBJECT = "Your Restaurant Recommendation from Chatbot"
    
    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = (message)
    
    CHARSET = "UTF-8"
    
    client = boto3.client('ses',region_name=AWS_REGION)
    
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )

    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        return "Email sent!"


def lambda_handler(event, context):
    
    #get user's request
    sqs_response = poll_sqs()
    sqs_msg = json.loads(sqs_response[0]['Body'])
    
    #delete from sqs
    sqs_del_response = delete_sqs(sqs_response[0]['ReceiptHandle'])
    
    #query elasticsearch to get restaurant list
    res = query_es(sqs_msg['cuisine'])
    
    #pick restaurants
    id_list = pick_id(res)
    
    #query dynamoDB to retrieve details
    restaurant_detail = retrieve_detail(id_list)
    
    #construct message
    message = construct_response(sqs_msg, restaurant_detail)
    
    #send recomendation to user
    response = send_email(sqs_msg['emailAddress'], message)
    
    return response