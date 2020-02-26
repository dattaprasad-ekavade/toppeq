from __future__ import print_function
from flask import Flask, request, redirect, Blueprint
from twilio.twiml.messaging_response import MessagingResponse
import time
import os
import json
import dialogflow_v2
from dialogflow_v2 import types
from twilio.rest import Client
from controller.messages import *
from google.cloud import language_v1, language
from google.cloud.language_v1 import enums, types
from google.oauth2.service_account import Credentials
from datetime import date
from sqlalchemy import create_engine, MetaData, Table, Column, select, insert, and_, update
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

engine = create_engine(os.getenv('SQLALCHEMY_SERVER_URL'))
connection = engine.connect()
metadata = MetaData()
twilioKey = Table('whatsapp_company_twilio_accounts', metadata,
                  autoload=True, autoload_with=engine)

sessionVariable = Table('whatsapp_user_active_sessions', metadata,
                        autoload=True, autoload_with=engine)


whatsapp_call = Blueprint('whatsapp', __name__)


def help_text(account_sid, auth_token):
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        from_=request.values.get('To', None),
        body=getBotReplyText('help'),
        to=request.values.get('From', None)
    )
    time.sleep(1)


def new_text(account_sid, auth_token):
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        from_=request.values.get('To', None),
        body=getBotReplyText('welcome_1'),
        to=request.values.get('From', None)
    )
    time.sleep(1)

    message = client.messages.create(
        from_=request.values.get('To', None),
        body=getBotReplyText('welcome_2'),
        to=request.values.get('From', None)
    )
    time.sleep(1)

    message = client.messages.create(
        from_=request.values.get('To', None),
        body=getBotReplyText('tip'),
        to=request.values.get('From', None)
    )


@whatsapp_call.route("/sms", methods=['GET', 'POST'])
def incoming_sms():

    account_sid = request.values.get('AccountSid', None)

    query = select([twilioKey.columns.auth_token, twilioKey.columns.external_company_id]).where(twilioKey.columns.account_sid ==
                                                                                                account_sid)
    ResultProxy = connection.execute(query)

    ResultSet = ResultProxy.fetchone()
    auth_token = ResultSet[0]

    print(vars(request.values))
    body = request.values.get('Body', None)
    incoming_text = body
    if(body.lower() == "new" or body.lower() == "reset" or body.lower() == "help"):
        body = 'reset vars'

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
        'WA_DIALOGFLOW_LOCATION')
    client = dialogflow_v2.SessionsClient()
    contact = str(request.values.get('From', None))
    contact = contact.replace('whatsapp:+', '')
    query = select([sessionVariable.columns.session_id]).where(and_(
        sessionVariable.columns.external_company_id == str(ResultSet[1]), sessionVariable.columns.contact_number == contact))

    ResultProxy1 = connection.execute(query)
    ResultSet1 = ResultProxy1.fetchone()

    if(ResultSet1):
        session = ResultSet1[0]
        query = update(sessionVariable).values(last_updated=date.today().strftime(r"%m-%d-%Y")).where(and_(
            sessionVariable.columns.external_company_id == str(ResultSet[1]), sessionVariable.columns.contact_number == contact))
        ResultProxy = connection.execute(query)

    else:
        session_generation = str(int(time.time())) + str(contact)
        session = client.session_path(
            os.getenv('WA_DIALOGFLOW_PROJECT_ID'), session_generation)

        query = insert(sessionVariable).values(
            external_company_id=ResultSet[1], contact_number=contact, session_id=str(session), last_updated=date.today().strftime(r"%m-%d-%Y"))
        ResultProxy = connection.execute(query)

    text_input = dialogflow_v2.types.TextInput(
        text=body.title(), language_code="en")

    query_input = dialogflow_v2.types.QueryInput(text=text_input)
    response = client.detect_intent(
        session=session, query_input=query_input)

    print('Query text: {}'.format(response.query_result.fulfillment_text))

    resp = MessagingResponse()

    resp.message(response.query_result.fulfillment_text)
    outputIntent = response.query_result.intent.display_name
    print(str(resp))
    if(response.query_result.fulfillment_text == 'Cleared'):
        resp = ''
        if(outputIntent == 'Default Welcome Intent'):
            new_text(account_sid, auth_token)
        else:
            help_text(account_sid, auth_token)
    return str(resp)


@whatsapp_call.route("/status", methods=['GET', 'POST'])
def incoming_status():

    print(str(request))
    return ''
