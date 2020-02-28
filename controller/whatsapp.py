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
from datetime import date, datetime
from sqlalchemy import create_engine, MetaData, Table, Column, select, insert, and_, update
from dotenv import load_dotenv, find_dotenv
from language import importlanguage

languageText = importlanguage.getLanguage()
languageText = json.loads(json.dumps(languageText))


load_dotenv(find_dotenv())

engine = create_engine(os.getenv('SQLALCHEMY_SERVER_URL'))
connection = engine.connect()
metadata = MetaData()
twilioKey = Table('whatsapp_company_twilio_accounts', metadata,
                  autoload=True, autoload_with=engine)

sessionVariable = Table('whatsapp_user_active_sessions', metadata,
                        autoload=True, autoload_with=engine)

phoneUsers = Table('whatsapp_company_phone_users', metadata,
                   autoload=True, autoload_with=engine)

whatsapp_call = Blueprint('whatsapp', __name__)

# Writes a Help Text Message to Whatsapp


def help_text(account_sid, auth_token):
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        from_=request.values.get('To', None),
        body=getBotReplyText('help'),
        to=request.values.get('From', None)
    )
    time.sleep(1)

# Writes a Welcome Text Message to Whatsapp


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

# Reads Input from Whatsapp and Sends it through Dialogflow and returns the response
@whatsapp_call.route("/sms", methods=['GET', 'POST'])
def incoming_sms():

    account_sid = request.values.get('AccountSid', None)
    contact = str(request.values.get('From', None))
    contact = contact.replace('whatsapp:+', '')
    sidMode = os.getenv('WHATSAPP_ACCOUNT_MODE')
    if(sidMode == 'GLOBAL'):

        # get ext company id from phno in
        query = select([phoneUsers.columns.external_company_id]).where(
            phoneUsers.columns.contact_number == contact)
        ResultProxy = connection.execute(query)

        ResultSet = ResultProxy.fetchone()
        if(not ResultSet[0]):
            # Error message, not of the company
            resp = MessagingResponse()
            # add templated message
            resp.message(languageText['failedCompanyMessage'])
            return str(resp)

        externalCompanyId = ResultSet[0]
        # get auth token where company id and sid
        query = select([twilioKey.columns.auth_token]).where(and_(
            twilioKey.columns.account_sid == account_sid, twilioKey.columns.external_company_id == externalCompanyId))
        ResultProxy = connection.execute(query)

        ResultSet = ResultProxy.fetchone()
        if(not ResultSet[0]):
            # Error message, not of the company
            resp = MessagingResponse()
            resp.message()  # add templated message
        auth_token = ResultSet[0]

    else:
        query = select([twilioKey.columns.auth_token, twilioKey.columns.external_company_id]).where(twilioKey.columns.account_sid ==
                                                                                                    account_sid)
        ResultProxy = connection.execute(query)

        ResultSet = ResultProxy.fetchone()
        if(not ResultSet[0]):
            # Error message, not of the company
            resp = MessagingResponse()
            resp.message()  # add templated message
        auth_token = ResultSet[0]
        externalCompanyId = ResultSet[1]

    print(vars(request.values))
    body = request.values.get('Body', None)
    incoming_text = body
    if(body.lower() == "new" or body.lower() == "help"):
        body = 'reset vars'

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
        'WA_DIALOGFLOW_LOCATION')
    client = dialogflow_v2.SessionsClient()

    query = select([sessionVariable.columns.session_id]).where(and_(
        sessionVariable.columns.external_company_id == str(externalCompanyId), sessionVariable.columns.contact_number == contact))

    ResultProxy = connection.execute(query)
    ResultSet = ResultProxy.fetchone()

    if(ResultSet):
        session = ResultSet[0]
        query = update(sessionVariable).values(last_updated=datetime.now()).where(and_(
            sessionVariable.columns.external_company_id == str(externalCompanyId), sessionVariable.columns.contact_number == contact))
        ResultProxy = connection.execute(query)

    else:
        session_generation = str(int(time.time())) + str(contact)
        session = client.session_path(
            os.getenv('WA_DIALOGFLOW_PROJECT_ID'), session_generation)

        query = insert(sessionVariable).values(
            external_company_id=externalCompanyId, contact_number=contact, session_id=str(session), last_updated=datetime.now())
        ResultProxy = connection.execute(query)

    text_input = dialogflow_v2.types.TextInput(
        text=body.title(), language_code="en")

    query_input = dialogflow_v2.types.QueryInput(text=text_input)
    response = client.detect_intent(
        session=session, query_input=query_input)

    resp = MessagingResponse()

    resp.message(response.query_result.fulfillment_text)
    outputIntent = response.query_result.intent.display_name
    print(str(resp))
    if(response.query_result.fulfillment_text == 'Cleared'):
        resp = ''
        if(outputIntent == languageText['welcomeIntentText']):
            new_text(account_sid, auth_token)
        else:
            help_text(account_sid, auth_token)
    return str(resp)

# Prints Status of the Webhook when it receives the whatsapp message
@whatsapp_call.route("/status", methods=['GET', 'POST'])
def incoming_status():
    return ''
