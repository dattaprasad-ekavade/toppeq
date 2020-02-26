def amountMessage(status):
    if(status == "Paid"):
        return 'What was the amount spent?'
    else:
        return 'What will be the amount spent?'


def dateMessage(status):
    if(status == "Paid"):
        return 'Can you tell me the date when this expense was done?'
    else:
        return 'Can you tell me the due date of this expense?'


def entityMessage(status):
    if(status == "Paid"):
        return 'For what was this expense made?'
    else:
        return 'For what is this expense made?'
    return


def frequencyMessage():
    return 'How frequently would this expense repeat?  \n(Yearly, Monthly, Weekly, Daily)'


def getBotReplyText(textType, options='none'):
    switcher = {
        'welcome_1': "Hi there 👋\nMy name's Expense buddy and I'm here to assist you with recording expenses. ",
        'welcome_2': "To *record an expense*, simply try typing \n \n_\"Bought office stationery for $20K.\"_  \n\nI will automatically categorize and notify the respective users once you have added your expense.",
        'help': "To *record an expense*, simply try typing \n \n_\"Bought office stationery for $20K.\"_ ",
        'tip': "💡 Type _\"new\"_ , anytime if you want to start adding a fresh expense. \nType _\"help\"_ , if you need help in adding an expense. ",
        'server_error': 'Sorry, we could not record this expense on our end. Could you try sending it again?',
        'missing_frequency_question': frequencyMessage(),
        'missing_amount_question': amountMessage(options),
        'missing_entity_question': entityMessage(options),
        'missing_date_question': dateMessage(options)
    }
    return switcher.get(textType, "")
