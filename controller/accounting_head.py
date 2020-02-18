from __future__ import print_function
from flask import Flask, request, make_response, jsonify, session, Blueprint
import sys
import os
import json
import re
import dialogflow_v2
from dialogflow_v2 import types

from google.cloud import language_v1, language
from google.cloud.language_v1 import enums, types
from datetime import datetime
import concurrent

from google.oauth2.service_account import Credentials

[sys.path.append(i) for i in ['.', '..']]

account_head = Blueprint('account_head', __name__)


def sendResponse(JSONObject):
    if(JSONObject):
        credentials = Credentials.from_service_account_file("../intent.json")
        client = dialogflow_v2.SessionsClient(credentials=credentials)

        session = client.session_path(
            'classify-intents-ujpxuu', 'Testing values')

        content = JSONObject
        text_input = dialogflow_v2.types.TextInput(
            text=content['inputText'], language_code="en")
        query_input = dialogflow_v2.types.QueryInput(text=text_input)
        response = client.detect_intent(
            session=session, query_input=query_input)

        print('Query text: {}'.format(response.query_result.query_text))
        print('Detected intent: {} (confidence: {})\n'.format(
            response.query_result.intent.display_name,
            response.query_result.intent_detection_confidence))

        confidence = float("{0:.2f}".format(
            response.query_result.intent_detection_confidence * 100))

        if('Default Welcome Intent' in response.query_result.intent.display_name or 'Default Fallback Intent'in response.query_result.intent.display_name):
            intentName = 'Others'
        else:
            intentName = response.query_result.intent.display_name

        intentName = intentName.lower().replace(" ", "_")
        result = {'inputText': response.query_result.query_text, 'accountHead': intentName,
                  'confidence': confidence, 'outflow_tags': []}

        return result
    else:
        return "Request Failed."


def searchTags(inputString):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"../tags.json"
    client = dialogflow_v2.SessionsClient()
    session = client.session_path(
        'slotfilling1-hyalrc', '1234abcdd')
    text_input = dialogflow_v2.types.TextInput(
        text=inputString, language_code="en")
    query_input = dialogflow_v2.types.QueryInput(text=text_input)
    response = client.detect_intent(
        session=session, query_input=query_input)

    print('Query text: {}'.format(response.query_result.query_text))
    print('Detected intent: {} (confidence: {})\n'.format(
        response.query_result.intent.display_name,
        response.query_result.intent_detection_confidence))
    intentName = response.query_result.intent.display_name
    return intentName


def getTags(JSONObject):
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
            future_intent = {executor.submit(searchTags, entity.name): entity for entity in response.entities}
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
        print(listEntityname)
        listEntityname = list(set(listEntityname))
        return {'outflow_tags': listEntityname}
    else:
        return {}


@account_head.route('/accounthead/', methods=['GET', 'POST'])
def add_message():
    # Async Process for Accounting Head

    start = datetime.now()
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
        end = datetime.now()
        time_taken = end - start
        print('Time: ', time_taken)
        return jsonify(acHead)