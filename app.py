# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import os
import pandas as pd
import sys
import requests
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot.v3 import (
     WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage
)

from linebot.models import (
    UnfollowEvent,
    MessageAction,
    TemplateSendMessage,
    ButtonsTemplate
)

from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Local package

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

handler = WebhookHandler(channel_secret)

configuration = Configuration(
    access_token=channel_access_token
)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    user_id = event.source.user_id
    mess = event.message.text
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        profile = line_bot_api.get_profile(user_id)
        name = profile.display_name
        if 'https://shopee.tw/' in mess:
            buttons_template = ButtonsTemplate(
                title='My buttons sample',
                text='Hello, my buttons',
                actions=[
                    URIAction(label='Go to line.me', uri='https://line.me'),
                    PostbackAction(label='ping', data='ping'),
                    PostbackAction(label='ping with text', data='ping', text='ping'),
                    MessageAction(label='Translate Rice', text='米')
                ])
            message = TemplateMessage(
                alt_text='Buttons alt text',
                template=buttons_template
            )
        else:
            message = TextMessage(text=f"{name} 您好\n{mess}")

        line_bot_api.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[message]
            )
        )

@app.route("/test_push_message", methods=['GET'])
def test_push_message():
    headers = request.headers
    bearer = headers.get('Authorization')
    token = bearer.split()[1]
    if token != os.getenv('token', None):
        return "OK"
    
    notify_uids = os.getenv('notify_uid', '')
    if not notify_uids:
        return "No UID"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        for uid in notify_uids.split(','):
            line_bot_api.push_message(
                PushMessageRequest(to=uid, messages=[TextMessage(text='推播測試。')]))
    return "OK"

@app.route("/healthcheck", methods=['GET'])
def healthcheck():
    return "OK"

def keep_awake():
    url = os.getenv('SELF_URL', None)
    if not url:
        print("URL Not FOUND.")
        return
    resp = requests.get(f"{url}/healthcheck")

# Use scheduler to health check
scheduler = BackgroundScheduler(daemon=True, job_defaults={'max_instances': 1})
trigger = CronTrigger(year="*", month="*", day="*", hour="*", minute="*/10")
trigger1 = CronTrigger(year="*", month="*", day="*", hour="4,12", minute="0", second="0")
trigger3 = CronTrigger(year="*", month="*", day="*", hour="2-12", minute="0", second="0")
scheduler.add_job(keep_awake, trigger=trigger)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)