import boto3
import json
# from decimal import *
import logging
import urllib
import ast
from boto3.dynamodb.conditions import Key, Attr

slack_token = 'xoxp-200614362405-201329483398-200462581635-f58f47a4b0d42a91fb8df72589885873'
# don't trap decimal errors
# setcontext(Context(traps=[]))
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    #get bitcoin price
    f = urllib.urlopen("https://api.bitfinex.com/v2/ticker/tBTCUSD")
    data = f.read()
    data_arr = ast.literal_eval(data)
    arr_len = len(data_arr)
    bitcoin_high = int(float(data_arr[arr_len-2])*100)
    bitcoin_low = int(float(data_arr[arr_len-1])*100)
    logger.debug("btc high: {} btc low: {}".format(bitcoin_high,bitcoin_low))

    dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = dynamodb.Table('bitbot-price-alerts')

    response = table.scan(
        FilterExpression=Attr('price').lt(bitcoin_high) & Attr('price').gt(bitcoin_low)
    )

    for i in response['Items']:
        price = i['price']
        logger.debug(price)
        # send alert to slack
        alert = "Bitcoin price reached {}!".format(round(float(price)/100,2))
        if (i['slack_user_id'] != 'N/A'):
            urllib.urlopen("https://slack.com/api/chat.postMessage?token={}&channel={}&text={}&username=bitbot&pretty=1"
            .format(slack_token,i['slack_user_id'],alert))
