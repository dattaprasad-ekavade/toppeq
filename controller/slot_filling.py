from __future__ import print_function
import sys
import os
import json
import dialogflow_v2
import requests
import time
import re
import dateparser
import dateutil.relativedelta
import jsonpickle
import random
import string
import controller.constants

from flask import Flask, request, make_response, jsonify, session, Blueprint
from dialogflow_v2 import types
from google.cloud import language_v1, language
from google.cloud.language_v1 import enums, types
from text2digits import text2digits
from datetime import datetime, date, time, timedelta
from controller.accounting_head import sendResponse, getTags
from controller.messages import *
from datetime import datetime
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

slot_fill = Blueprint('slot_fill', __name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
    'SLOT_DIALOGFLOW_LOCATION')

client = dialogflow_v2.SessionsClient()
letters = string.ascii_letters
sessionID = ''.join(random.choice(letters) for i in range(10))
session = client.session_path(
    os.getenv('SLOT_DIALOGFLOW_PROJECT_ID'), sessionID)

client = language_v1.LanguageServiceClient()
defaultCurrency = 'USD'

# Defines a class to store variables


class lastEntry():
    Amount = '0'
    entitySend = ''
    ExpenseType = ""
    recurrence = "No"
    frequency = ""
    paymentDate = ''
    paymentStatus = 'Unpaid'
    Description = ''
    currency = defaultCurrency
    fullEntity = 0
    askFor = 'None'
    category = ''
    tags = []

    def isEmpty(self):
        if self.Amount == '0' and self.Description == '' and self.ExpenseType == '' and self.entitySend == '':
            return True
        else:
            return False

    def isFull(self):
        if self.Amount == '0' or self.Description == '' or self.ExpenseType == '' or self.entitySend == '':
            return False
        else:
            return True

    def clearIt(self):
        self.Amount = '0'
        self.entitySend = ''
        self.ExpenseType = ""
        self.recurrence = "No"
        self.frequency = ""
        self.paymentDate = ''
        self.paymentStatus = 'Unpaid'
        self.Description = ''
        self.currency = defaultCurrency
        self.fullEntity = 0
        self.askFor = 'None'
        self.category = ''
        self.tags = []

    def emptyList(self):
        if self.Amount == '0':
            return 'Amount'
        if self.paymentDate == '':
            return 'Date'
        if self.entitySend == '':
            return 'Entity'
        if self.frequency == '' and self.recurrence == 'Yes':
            return 'Frequency'

        return 'None'

# removes stopwords from the text


def removeStopwords(text):

    stopWords = ["and "]
    big_regex = re.compile(r'\b%s\b' %
                           r'\b|\b'.join(map(re.escape, stopWords)))
    return big_regex.sub("", text)

# converts words to numbers and convert lakh to numbers


def convertWordstoNum(text):

    t2d = text2digits.Text2Digits()
    convertedText = t2d.convert(text)

    secondConvertedText = re.sub(
        r'(?P<money>[0-9]+)( |)l ', r'\g<money>00000 ', convertedText.lower())
    thirdConvertedText = re.sub(
        r'(?P<money>[0-9]+)( |)la(kh|c)(|s) ', r'\g<money>00000 ', secondConvertedText)
    return re.sub(r'(?P<money>[0-9]+)( |)cr ', r'\g<money>0000000 ', thirdConvertedText)


# Removes consecutive spaces in between two numbers
def removeConsecutiveSpaces(text):

    value = re.sub(
        r'(?P<number1>[0-9]+) (?P<number2>[0-9]+) ', r'\g<number1>+\g<number2> ', text+' ')

    List = re.findall(r'([0-9]+)\+([0-9]+)', value)
    for items in List:
        value = value.replace(
            str(items[0])+r'+'+str(items[1]), str(int(items[0]) + int(items[1])))

    return value

# Returns text in lowercase and transforms rs to rupees


def lowerCaps(text):
    if(not 'Rs.' in text.title()):
        text = re.sub(
            r'( )(rs(| |\.))', r' Rs. ', text+' ')
    return re.sub(
        r'(\d+(?P<ordinal>[A-z])+)', lambda m: m.group(0).lower(), text+' ')

# uses all functions above to filter text for input


def filterResults(text):
    op = removeConsecutiveSpaces(convertWordstoNum(removeStopwords(text)))
    return lowerCaps(op)

# maps accounting head to the number to be sent to db


def mapAChead(acHead):
    acHead = acHead.replace(' ', '_').lower()
    AcHeadMap =controller.constants.AcHeadMap
    if (AcHeadMap[acHead]):
        return AcHeadMap[acHead]
    else:
        return AcHeadMap["others"]

# gets accounting head from the  accountingHead page


def getACHead(text):
    output = json.loads(json.dumps(sendResponse(
        json.loads(json.dumps(text)))))['accountHead']
    return output.replace('_', " ").title()

# gets tags from accountingHead page


def receiveTags(text):
    tempList = []
    if(oldValue.tags == []):
        tempList = json.loads(json.dumps(getTags(
            json.loads(json.dumps(text)))))['outflow_tags']
        oldValue.tags.append(oldValue.category.title())
        for string in tempList:
            oldValue.tags.append(string.title())
    return ''

# Generates whatsapp output in a specified format to be sent


def buildResultText(outputJSON):
    resultString = languageText['outputSummaryMessage1'] + \
        outputJSON['data']['createExpense']['title']
    resultString += languageText['outputSummaryMessage2'] + \
        outputJSON['data']['createExpense']['currency'] + \
        ' ' + str(outputJSON['data']['createExpense']['amount'])
    resultString += languageText['outputSummaryMessage3'] + \
        outputJSON['data']['createExpense']['paymentStatus']

    if(outputJSON['data']['createExpense']['finalPaymentDate']):
        displayDate = dateparser.parse(
            str(outputJSON['data']['createExpense']['finalPaymentDate']))
        resultString += languageText['outputSummaryMessage4'] + \
            displayDate.strftime(r"%d %B %Y")

    if(outputJSON['data']['createExpense']['expenseDueDate']):
        displayDate = dateparser.parse(
            str(outputJSON['data']['createExpense']['expenseDueDate']))
        resultString += (languageText['outputSummaryMessage5'] +
                         displayDate.strftime(r"%d %B %Y"))

    recurringString = 'Yes' if(
        str(outputJSON['data']['createExpense']['recurring']).lower() == 'true') else 'No'
    resultString += languageText['outputSummaryMessage6'] + recurringString

    if(outputJSON['data']['createExpense']['expenseRecurrence']['frequency'] != ''):
        resultString += languageText['outputSummaryMessage7'] + \
            outputJSON['data']['createExpense']['expenseRecurrence']['frequency']

    resultString += languageText['outputSummaryMessage8'] + \
        outputJSON['data']['createExpense']['accountingHead']['displayName']
    tagString = ','.join(
        map(str, outputJSON['data']['createExpense']['expenseTags']))
    resultString += languageText['outputSummaryMessage9'] + \
        tagString.replace(',', ', #')

    outputUsers = ''
    userList = (outputJSON['data']['createExpense']['notifyUsers'])
    for userMeta in userList:
        names = userMeta['userMeta']
        for name in names:
            outputUsers += (' '+names[name] + ',')

    resultString += (languageText['outputSummaryMessage10'] + outputUsers[:-1])

    return resultString

# Webhook function to return response  to Twilio webhook
@slot_fill.route('/slotfill/', methods=['GET', 'POST'])
def send_nlp_response():
    oldValue = lastEntry()
    req = request.get_json(force=True)
    query = select([sessionVariable.columns.session_data]).where(
        sessionVariable.columns.session_id == str(req.get('session')))

    ResultProxy = connection.execute(query)
    ResultSet = ResultProxy.fetchone()

    if(ResultSet[0]):
        oldValue = jsonpickle.decode(ResultSet[0])

    inputText = str(req.get('queryResult').get('queryText'))
    if(inputText.lower() == 'reset vars'):
        oldValue.clearIt()
        return {'fulfillmentText':  'Cleared'}

    oldValue.Description = inputText if oldValue.Description == '' else oldValue.Description

    inputIntent = str(req.get('queryResult').get('intent').get('displayName'))

    filteredText = filterResults(inputText+' ')

    listTosend = {'inputText':  str(filteredText)}

    document = language.types.Document(
        content=filteredText.title(),
        type=language.enums.Document.Type.PLAIN_TEXT
    )
    features = language.types.AnnotateTextRequest.Features(
        extract_syntax=True,
        extract_entities=True,
        extract_document_sentiment=False,
        extract_entity_sentiment=False,
        classify_text=False)

    response = client.annotate_text(document, features)
    print('Checking for : '+oldValue.askFor)

    changeVar = 0
    for entity in response.entities:
        entityDetectList = controller.constants.entityDetectList 
        # For List of entities
        if any(x in enums.Entity.Type(entity.type).name for x in entityDetectList):
            if((entity.name.title() != 'Subscription' or entity.name.title() != 'Rent' or entity.name.title() != 'Purchase')):
                if(oldValue.askFor == 'None' or oldValue.askFor == 'Entity'):
                    oldValue.entitySend += (entity.name + ', ')
                    changeVar = 1
        # For date
        if(oldValue.askFor == 'Date' or oldValue.askFor == 'None'):
            if ("DATE" in enums.Entity.Type(entity.type).name):
                oldValue.paymentDate = dateparser.parse(entity.name)

    oldValue.fullEntity = changeVar

    # Step 3.1: if price is detected by NLP, mark it with currency
    if(oldValue.askFor == 'Amount' or oldValue.askFor == 'None'):
        flag = 0 if(oldValue.Amount == '0') else 1

        if(oldValue.Amount == '0'):
            for entity in response.entities:
                if(enums.Entity.Type(entity.type).name == "PRICE" and flag == 0):
                    oldValue.Amount = float(entity.metadata[u"value"])
                    oldValue.currency = entity.metadata[u"currency"]
                    flag = 1

            # Step 3.3 Check from Dialogflow
            if(flag == 0):
                if(req.get('queryResult').get('parameters').get('PRICE')):
                    oldValue.Amount = float(
                        req.get('queryResult').get('parameters').get('PRICE'))
                    flag = 1

            # Step 3.4 In case nothing is found, pick a number from the list
            if(flag == 0):
                maxValue = 0
                for entity in response.entities:
                    if(enums.Entity.Type(entity.type).name == "NUMBER"):
                        maxValue = float(entity.metadata[u"value"]) if(
                            int(float(entity.metadata[u"value"])) > int(float(maxValue))) else maxValue

                if(int(maxValue) > 0):
                    oldValue.Amount = maxValue

    # Step 3.5 Detect Recurrence

    if(oldValue.ExpenseType == ''):
        if(req.get('queryResult').get('intent').get('displayName') == "checkRentExpense"):
            oldValue.recurrence = "Yes"
            oldValue.ExpenseType = "Rent/Subscription"

            textString = filteredText.lower()
            if("weekly" in textString or "per week" in textString):
                oldValue.frequency = "Weekly"
            elif("yearly" in textString or "per year" in textString or "annual" in textString):
                oldValue.frequency = "Yearly"
            elif("monthly" in textString or "per month" in textString or "every month" in textString):
                oldValue.frequency = "Monthly"
        else:
            oldValue.ExpenseType = "Buy/Purchase"

    elif(oldValue.askFor == 'Frequency'):
        textString = filteredText.lower()
        if("weekly" in textString or "per week" in textString):
            oldValue.frequency = "Weekly"
        elif("yearly" in textString or "per year" in textString or "annual" in textString):
            oldValue.frequency = "Yearly"
        elif("monthly" in textString or "per month" in textString or "every month" in textString):
            oldValue.frequency = "Monthly"

    # Check if Dialogflow had picked up a date (18th, last wednesday)
    if(oldValue.askFor == 'Date' or oldValue.askFor == 'None'):

        if(oldValue.paymentDate == ''):
            if(req.get('queryResult').get('parameters').get('date')):
                oldValue.paymentDate = dateparser.parse(
                    str(req.get('queryResult').get('parameters').get('date')))

                if(str(int(float(oldValue.Amount))) in str(req.get('queryResult').get('parameters').get('date')) and oldValue.askFor == 'None'):
                    oldValue.Amount = '0'

            # Check if Dialogflow had picked up a date (this month, next june, last year)
            try:
                if(req.get('queryResult').get('parameters').get('date-period') != ''):
                    if(req.get('queryResult').get('parameters').get('date-period').get('endDate')):
                        oldValue.paymentDate = dateparser.parse(
                            req.get('queryResult').get('parameters').get('date-period').get('endDate'))

                    # If the number caught by amount is in date, negate that.
                    if(str(int(float(oldValue.Amount))) in str(req.get('queryResult').get('parameters').get('date')) and oldValue.askFor == 'None'):
                        oldValue.Amount = '0'

            except:
                print('Date Error')

    # Detect Tense for Paid/Unpaid
    for token in response.tokens:
        # 3 = enum for Past
        if(token.part_of_speech.tense == 3):
            oldValue.paymentStatus = "Paid"

    print('Missing Value = ' + oldValue.emptyList())
    oldValue.askFor = oldValue.emptyList()
    if 'None' in oldValue.emptyList():
        url = "https://ajency-qa.api.toppeq.com/graphql"

        dateKey = "finalPaymentDate" if oldValue.paymentStatus == "Paid" else "expenseDueDate"
        dateValue = oldValue.paymentDate.strftime(r"%Y-%m-%d %H:%M:%S")
        payload = {
            "operationName": "CreateExpense",
            "variables": {
                "input": {
                    "company": "2",
                    "title": oldValue.Description,
                    "description": oldValue.Description,
                    "amount": str(oldValue.Amount),
                    "currency": oldValue.currency,
                    "recurring": "true" if('Yes' in oldValue.recurrence) else "false",
                    "paymentStatus": oldValue.paymentStatus,
                    "sourceDriver": "chatbot",
                    "status": "draft",
                    "expenseRecurrence": {
                        "frequency": oldValue.frequency
                    },
                    dateKey: dateValue if(dateValue) else ''
                }
            },
            "query": "mutation CreateExpense($input: ExpenseInput) {\n createExpense(input: $input) {\n id \n title \n referenceId \n description \n amount \n currency \n expenseDueDate \n finalPaymentDate \n recurring \n referenceId \n paymentStatus \n accountingHead \n{ \n displayName \n} \n notifyUsers \n{ \n userMeta \n{ \n name \n} \n} \n expenseRecurrence \n{ \n frequency \n} \n expenseTags}\n}\n"
        }

        headers = {'Content-Type': 'application/json'}
        result = getBotReplyText('server_error')

        try:
            response = requests.request(
                "POST", url, headers=headers, data=json.dumps(payload))
            OutputURL = languageText['successWhatsappMessage']
            outputJSON = response.json()
            if(outputJSON['data']['createExpense']['id']):
                OutputURL = OutputURL + \
                    str(outputJSON['data']['createExpense']['id'])

                result = OutputURL + buildResultText(outputJSON)

        except Exception as e:
            print('API Failed', e)
            result = getBotReplyText('server_error')
        oldValue.clearIt()

    elif 'Amount' in oldValue.emptyList():
        result = getBotReplyText(
            'missing_amount_question', oldValue.paymentStatus)
    elif 'Date' in oldValue.emptyList():
        result = getBotReplyText(
            'missing_date_question', oldValue.paymentStatus)
    elif 'Entity' in oldValue.emptyList():
        result = getBotReplyText(
            'missing_entity_question', oldValue.paymentStatus)
    elif 'Frequency' in oldValue.emptyList():
        result = getBotReplyText('missing_frequency_question')

    sessionData = '{}' if('None' in oldValue.emptyList()
                          ) else jsonpickle.encode(oldValue)
    query = update(sessionVariable).values(session_data=sessionData).where(
        sessionVariable.columns.session_id == str(req.get('session')))
    ResultProxy = connection.execute(query)
    return {'fulfillmentText':  result}
