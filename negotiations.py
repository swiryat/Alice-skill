# encoding: utf-8

from __future__ import unicode_literals
import json
import logging
import pandas as pd
import dateparser
import datetime

from flask import Flask, request

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

sessionStorage = {}


def find_all_users(text, user_name):
    res = []
    for user in user_name:
        inv_user = ' '.join([user.split(' ')[1], user.split(' ')[0]])
        if text.lower().find(user.lower()) != -1 or text.lower().find(inv_user.lower()) != -1:
            res.append(user)
    return res


def parse_data(text):
    for t in text.split(' '):
        data = dateparser.parse(t)
        if data:
            return data
    return None


def check_negotiations(data_text, index):
    if negotiations.loc[negotiations['id'] == index, 'busy'].values[0].find(data_text) == -1:
        return True
    return False


def check_user(data_text, user):
    if user_data.loc[user_data['full_name'] == user, 'busy'].values[0].find(data_text) == -1:
        return True
    return False


def is_good_data(data, session_id):
    data_text = data.strftime('%d.%m.%Y')

    for user in booking[session_id]['who']:
        if not check_user(data_text, user):
            return False

    for index in negotiations['id']:
        if check_negotiations(data_text, index):
            booking[session_id]['when'] = data
            booking[session_id]['when_text'] = data_text
            booking[session_id]['negotiations'] = index
            return True

    return False


def find_date(text, session_id):
    data = dateparser.parse(text)
    if is_good_data(data, session_id):
        return
    else:
        data = data + datetime.timedelta(days=1)
        find_date(data.strftime('%d.%m.%Y'), session_id)


booking = {}

user_data = pd.read_csv('user.csv').fillna('')
user_data['full_name'] = user_data['first_name'] + ' ' + user_data['last_name']
negotiations = pd.read_csv('negotiations.csv').fillna('')


@app.route("/", methods=['POST'])
def main():
    logging.info('Request: %r', request.json)

    response = {
        "version": request.json['version'],
        "session": request.json['session'],
        "response": {
            "end_session": False
        }
    }

    session_id = request.json['session']['session_id']

    if session_id not in booking.keys():
        booking[session_id] = {'who': [],
                               'when': None,
                               'when_text': None,
                               'negotiations': None}

    handle_dialog(request.json, response)

    logging.info('Response: %r', response)

    return json.dumps(
        response,
        ensure_ascii=False,
        indent=2
    )


def handle_dialog(req, res):
    session_id = req['session']['session_id']
    user_id = req['session']['user_id']

    if req['session']['new']:
        sessionStorage[user_id] = {
            'suggests': user_data['full_name'].values[:3]
        }

        res['response']['text'] = 'Привет, я помогу тебе заказать переговорку, скажи мне кого ты хочешь позвать.'
        return

    if not booking[session_id]['who']:
        find = find_all_users(req['request']['original_utterance'], user_data['full_name'])

        if find:
            res['response']['text'] = 'Я приглашу '
            for u in find:
                res['response']['text'] += u + ', '
            res['response']['text'] = res['response']['text'][:-2]
            booking[session_id]['who'] = find

            res['response']['text'] += '. Когда заказать переговорку.'
            return

        res['response']['text'] = 'Таких пользователей не было найдено. Скажи мне кого ты хочешь позвать.'
        return

    if not booking[session_id]['when']:
        data = parse_data(req['request']['original_utterance'])
        if data:
            booking[session_id]['when'] = data
            booking[session_id]['when_text'] = data.strftime('%d.%m.%Y')
            res['response']['text'] = 'Вы хотите заказать на {}'.format(booking[session_id]['when_text'])
        else:
            res['response']['text'] = 'Я не поняла дату.'
        return

    if not booking[session_id]['negotiations']:
        find_date(booking[session_id]['when_text'], session_id)
        res['response']['text'] = 'Я позову {}, забронирую {} переговорку, {} числа.'\
            .format(', '.join(booking[session_id]['who']), booking[session_id]['negotiations'], booking[session_id]['when_text'])
        return
