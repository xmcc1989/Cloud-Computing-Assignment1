
import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3
import json

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

def push_to_sqs(location, cuisine, date, time, numberOfPeople, emailAddress):
    msg = {'location': location,
            'cuisine': cuisine,
            'date': date,
            'time': time,
            'numberOfPeople': numberOfPeople,
            'emailAddress': emailAddress}

    client = boto3.client("sqs")
    response = client.send_message(
        QueueUrl = "https://sqs.us-east-1.amazonaws.com/578480262707/chatBotTaskQueue",
        MessageBody = json.dumps(msg))
    return {
            'statusCode': response["ResponseMetadata"]["HTTPStatusCode"],
            'body': json.dumps(response["ResponseMetadata"])
            }

def validate_dining_suggestion(location, cuisine, date, time, numberOfPeople, emailAddress):
    location_list = ['manhattan']
    cuisine_list = ['chinese', 'japanese', 'korean', 'american', 'french', 'italian']
    if location is not None and location.lower() not in location_list:
        return build_validation_result(False,
                                       'location',
                                       'We do not service in {}.'
                                       'We currently only provide service in Manhattan. Would you try again?'.format(location))

    if cuisine is not None and cuisine.lower() not in cuisine_list:
        return build_validation_result(False,
                                       'cuisine',
                                       'We do not have any {} restaurants in the list.'
                                       'You may want to select from the following list: '.format(cuisine) + ', '.join(cuisine_list))   

    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'date', 'I did not understand that, what date would you like to go to the restaurant?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'date', 'You can only select a day from today onwards. What day would you like to go to the restaurant?')

    if time is not None:
        if len(time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'time', None)

        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'time', None)

        # if hour < 10 or hour > 16:
        #     # Outside of business hours
        #     return build_validation_result(False, 'PickupTime', 'Our business hours are from ten a m. to five p m. Can you specify a time during this range?')

    if numberOfPeople is not None:
        if int(numberOfPeople) <= 0:
            return build_validation_result(False, 
                                          'numberOfPeople', 
                                          'You party group must be greater than 0. Please try again.'
                                          'How many people are there in your party?')

           
    return build_validation_result(True, None, None)




""" --- Functions that control the bot's behavior --- """


def greeting(intent_request):
   
    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Hi there, how can I help you?'})

def thankyou(intent_request):
   
    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'You are welcome!'})

def dining_suggestion(intent_request):
    """
    Performs dialog management and fulfillment for ordering flowers.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    location = get_slots(intent_request)["location"]
    cuisine = get_slots(intent_request)["cuisine"]
    date = get_slots(intent_request)["date"]
    time = get_slots(intent_request)["time"]
    numberOfPeople = get_slots(intent_request)["numberOfPeople"]
    emailAddress = get_slots(intent_request)["emailAddress"]
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_dining_suggestion(location, cuisine, date, time, numberOfPeople, emailAddress)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                              intent_request['currentIntent']['name'],
                              slots,
                              validation_result['violatedSlot'],
                              validation_result['message'])

        # Pass the price of the flowers back through session attributes to be used in various prompts defined
        # on the bot model.
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        # if flower_type is not None:
        #     output_session_attributes['Price'] = len(flower_type) * 5  # Elegant pricing model

        return delegate(output_session_attributes, get_slots(intent_request))
   
    # Push message to SQS
    push_to_sqs(location, cuisine, date, time, numberOfPeople, emailAddress)
    
    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': "You're all set. Expect my suggestions shortly! Have a good day."})




""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'GreetingIntent':
        return greeting(intent_request)
    if intent_name == 'DiningSuggestionIntent':
        return dining_suggestion(intent_request)
    if intent_name == 'ThankYouIntent':
        return thankyou(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
