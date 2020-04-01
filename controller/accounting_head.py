from __future__ import print_function
from flask import Flask, request, make_response, jsonify, session, Blueprint
import sys
import os
import json
import re
import time
import dialogflow_v2
from dialogflow_v2 import types
import random
import string
from google.cloud import language_v1, language
from google.cloud.language_v1 import enums, types
from datetime import datetime
import concurrent

from google.oauth2.service_account import Credentials

[sys.path.append(i) for i in ['.', '..']]

account_head = Blueprint('account_head', __name__)

letters = string.ascii_letters
sessionID = ''.join(random.choice(letters) for i in range(10))


def sendResponse(JSONObject):
    start = time.time()
    if(JSONObject):
        credentials = Credentials.from_service_account_file(
            os.getenv('SLOT_DIALOGFLOW_LOCATION'))
        client = dialogflow_v2.SessionsClient(credentials=credentials)
        session = client.session_path(
            os.getenv('SLOT_DIALOGFLOW_PROJECT_ID'), sessionID)

        content = JSONObject
        text_input = dialogflow_v2.types.TextInput(
            text=content['inputText'], language_code="en")
        query_input = dialogflow_v2.types.QueryInput(text=text_input)
        response = client.detect_intent(
            session=session, query_input=query_input)

        confidence = float("{0:.2f}".format(
            response.query_result.intent_detection_confidence * 100))

        if('Default Welcome Intent' in response.query_result.intent.display_name or 'Default Fallback Intent'in response.query_result.intent.display_name):
            intentName = 'Others'
        else:
            intentName = response.query_result.intent.display_name

        #intentName = intentName.lower().replace(" ", "_")
        result = {'inputText': response.query_result.query_text, 'accountHead': intentName,
                  'confidence': confidence, 'outflow_tags': []}

        print('\033[1m END OF ACCOUNTHEAD FUNCTION:' +
              "{0:.5f}".format(time.time() - start) + '\033[0m')
        return result
    else:
        return "Request Failed."


def searchTags(inputString):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"../tags.json"
    client = dialogflow_v2.SessionsClient()

    session = client.session_path(
        'slotfilling1-hyalrc', sessionID)
    text_input = dialogflow_v2.types.TextInput(
        text=inputString, language_code="en")
    query_input = dialogflow_v2.types.QueryInput(text=text_input)
    response = client.detect_intent(
        session=session, query_input=query_input)

    intentName = response.query_result.intent.display_name
    return intentName


def getTags(JSONObject):
    start = time.time()
    if(JSONObject):
        content = JSONObject
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"../tags.json"
        # Call NLP API
        client1 = language_v1.LanguageServiceClient()
        document = language.types.Document(
            content=content['inputText'],
            type=language.enums.Document.Type.PLAIN_TEXT
        )
        features = language.types.AnnotateTextRequest.Features(
            extract_syntax=True,
            extract_entities=True,
            extract_document_sentiment=False,
            extract_entity_sentiment=False,
            classify_text=False)

        response = client1.annotate_text(document, features)
        listEntityname = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_intent = {executor.submit(
                searchTags, entity.name): entity for entity in response.entities}
            for future in concurrent.futures.as_completed(future_intent):
                output = future_intent[future]
                try:
                    intentName = future.result()
                except Exception as exc:
                    print('%r generated an exception: %s' % (output, exc))
                else:
                    if(intentName != 'Default Fallback Intent'):
                        listEntityname.append(intentName)

        if(not listEntityname):
            listEntityname.append('miscellaneous')
        # remove duplicates
        listEntityname = list(set(listEntityname))
        print('\033[1m END OF TAGS:' +
              "{0:.5f}".format(time.time() - start) + '\033[0m')
        return {'outflow_tags': listEntityname}
    else:
        return {}


@account_head.route('/accounthead/', methods=['GET', 'POST'])
def add_message():
    # Async Process for Accounting Head
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(sendResponse, request.json)
        future1 = executor.submit(getTags, request.json)
        acHead = future.result()
        tags = future1.result()
        acHead.update(tags)
        newList = list(acHead["outflow_tags"])
        newList.append(acHead["accountHead"])
        acHead["outflow_tags"] = newList
        print(str(acHead))
        print('\033[1m END OF API CALL:' +
              "{0:.5f}".format(time.time() - start) + '\033[0m')
        return jsonify(acHead)


def trainData(intentName, trainingPhrases):

    credentials = Credentials.from_service_account_file(
        os.getenv('SLOT_DIALOGFLOW_LOCATION'))
    client = dialogflow_v2.IntentsClient(credentials=credentials)

    parent = client.project_agent_path(os.getenv('SLOT_DIALOGFLOW_PROJECT_ID'))
    intents = client.list_intents(parent)
    intent_path = [
        intent.name for intent in intents if intent.display_name == intentName]

    client = dialogflow_v2.IntentsClient(credentials=credentials)

    name = intent_path[0]

    response = client.get_intent(name, intent_view='INTENT_VIEW_FULL')
    intent = response
    # create new instance of training phrase

    training_phrases_parts = trainingPhrases
    training_phrases = []
    for training_phrases_part in training_phrases_parts:
        part = dialogflow_v2.types.Intent.TrainingPhrase.Part(
            text=training_phrases_part)
        # Here we create a new training phrase for each provided part.
        training_phrase = dialogflow_v2.types.Intent.TrainingPhrase(parts=[
                                                                    part])
        training_phrases.append(training_phrase)

    intent.training_phrases.extend(training_phrases)
    response1 = client.update_intent(intent, language_code='en')
    return 'Success, ' + str(intentName) + ' is trained'


@account_head.route('/ACHeadTraining/', methods=['POST'])
def trainDataset():
    JSONObject = request.json 
    if(JSONObject):
        content = JSONObject
        return trainData(content['intentName'], content['trainingPhrases'])
    else:
        return 'Failed'
