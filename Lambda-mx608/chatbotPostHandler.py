import json
import boto3
import datetime

def construct_response(id, message):
    response =  [
                    {
                      "type": "unstructured",
                      "unstructured": {
                          "id": id,
                          "text": message,
                          "timestamp": str(datetime.datetime.now())
                      }
                    }
                ]
    
    return response

def lambda_handler(event, context):
    message = event['messages'][0]['unstructured']['text']
    userid = '123' #hard code user id
    
    client = boto3.client("lex-runtime")
    response = client.post_text(
        botName = 'RecommendRestaurant',
        botAlias ='dev',
        userId = userid, # to be changed
        # sessionAttributes={
        #     'string': 'string'
        # },
        # requestAttributes={
        #     'string': 'string'
        # },
        inputText = message,
        # activeContexts=[
        #     {
        #         'name': 'string',
        #         'timeToLive': {
        #             'timeToLiveInSeconds': 123,
        #             'turnsToLive': 123
        #         },
        #         'parameters': {
        #             'string': 'string'
        #         }
        #     },
        # ]
    )

    return {
            'statusCode': response["ResponseMetadata"]["HTTPStatusCode"],
            'messages': construct_response(userid, response['message'])
            }


