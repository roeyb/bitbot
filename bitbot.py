import json
import datetime
import time
import os
import dateutil.parser
import logging
import boto3
import re

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# --- Helpers that build all of the responses ---

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

# --- Helper Functions ---

def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n

def try_ex(func):
    try:
        return func()
    except KeyError:
        return None

""" --- Functions that control the bot's behavior --- """

def set_currency_alert(intent_request):
    logger.debug(intent_request);
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    price = try_ex(lambda: intent_request['currentIntent']['slots']['price'])

    if intent_request['invocationSource'] == 'DialogCodeHook' and price == None:
        return delegate(session_attributes, intent_request['currentIntent']['slots'])

    try:
        price = re.search(r"[-+]?\d*\.\d+|\d+",price).group()
    except Exception, e:
        return elicit_slot(
            session_attributes,
            intent_request['currentIntent']['name'],
            intent_request['currentIntent']['slots'],
            'price',
            {'contentType': 'PlainText', 'content': 'This is not a valid value, please try again.'}
        )

    user_id = intent_request['userId']
    user_id_arr = user_id.split(':')
    slack_user_id = user_id_arr[2] if len(user_id_arr) == 3 else 'N/A'
    logger.debug('user_id: {}, price: {}'.format(user_id,price))

    # add to dynamodb
    client = boto3.client('dynamodb')
    try:
        client.put_item(TableName='bitbot-price-alerts',
            Item={'alert_id':{'S':"{}_{}".format(user_id, time.time())},
                'pair':{'S':'BTCUSD'},
                'price':{'N':str(round(float(price)*100))},
                'slack_user_id':{'S':slack_user_id}
            })
    except Exception, e:
        return close(
            session_attributes,
            'Failed',
            {
                'contentType': 'PlainText',
                'content': 'I was unable to complete your request, please try again later.'
            }
        )

    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Thanks, I have set a new alert for you.'
        }
    )
# --- Intents ---


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'bitbotSetNewAlert':
        return set_currency_alert(intent_request)
    # elif intent_name == 'Temp':
    #     return set_currency_alert(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


# --- Main handler ---


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
