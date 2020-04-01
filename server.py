from __future__ import print_function
from controller.whatsapp import whatsapp_call
from controller.slot_filling import slot_fill
from controller.amount import amount
from controller.date import date_object
from controller.accounting_head import account_head
from controller.refresh_agents import callRefresh
from flask import Flask, request, make_response, jsonify, session
import sys

sys.path.append('../controller')

app = Flask(__name__)

# refreshing all the agents to reduce timeout delays
callRefresh()

# Registering blueprints for each file to be marked with routes
app.register_blueprint(account_head, url_prefix='/api/')
app.register_blueprint(slot_fill, url_prefix='/api/')
app.register_blueprint(amount, url_prefix='/api/')
app.register_blueprint(date_object, url_prefix='/api/')
app.register_blueprint(whatsapp_call, url_prefix='/wa/')

# Used to test the API on browser
@app.route('/')
def hello():
    return "API Endpoint for Toppeq"


# start the app with given IP(if 0.0.0.0, takes IP of the machine/server) and Port.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
