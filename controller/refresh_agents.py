from __future__ import print_function

import time, random
import os
import json
import dialogflow_v2
import string
from dialogflow_v2 import types

from controller.messages import *
from google.cloud import language_v1, language
from google.cloud.language_v1 import enums, types
from datetime import date, datetime
from sqlalchemy import create_engine, MetaData, Table, Column, select, insert, and_, update
from dotenv import load_dotenv, find_dotenv
from language import importlanguage

languageText = importlanguage.getLanguage()
languageText = json.loads(json.dumps(languageText))


load_dotenv(find_dotenv())


def callRefresh():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
        'WA_DIALOGFLOW_LOCATION')
    client = dialogflow_v2.SessionsClient()
    session = client.session_path(
        os.getenv('WA_DIALOGFLOW_PROJECT_ID'), str(time.time()))
    text_input = dialogflow_v2.types.TextInput(
        text='hi', language_code="en")

    query_input = dialogflow_v2.types.QueryInput(text=text_input)
    response = client.detect_intent(
        session=session, query_input=query_input)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
        'SLOT_DIALOGFLOW_LOCATION')

    client = dialogflow_v2.SessionsClient()
    letters = string.ascii_letters
    sessionID = ''.join(random.choice(letters) for i in range(10))
    session = client.session_path(
        os.getenv('SLOT_DIALOGFLOW_PROJECT_ID'), sessionID)

    client = language_v1.LanguageServiceClient()
    document = language.types.Document(
        content='filteredText.title()',
        type=language.enums.Document.Type.PLAIN_TEXT
    )
    features = language.types.AnnotateTextRequest.Features(
        extract_syntax=True,
        extract_entities=True,
        extract_document_sentiment=False,
        extract_entity_sentiment=False,
        classify_text=False)
    response = client.annotate_text(document, features)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"../tags.json"
    client1 = language_v1.LanguageServiceClient()
    document = language.types.Document(
        content='inputText',
        type=language.enums.Document.Type.PLAIN_TEXT
    )
    features = language.types.AnnotateTextRequest.Features(
        extract_syntax=True,
        extract_entities=True,
        extract_document_sentiment=False,
        extract_entity_sentiment=False,
        classify_text=False)

    response = client1.annotate_text(document, features)
