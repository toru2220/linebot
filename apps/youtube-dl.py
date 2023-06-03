import os
from playwright.sync_api import sync_playwright
import asyncio
import urllib.parse

# datetimeモジュールを使用
import datetime
import random

from flask import Flask, request, abort, send_from_directory

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
from linebot.models import (
    TextSendMessage,
    PostbackEvent,FollowEvent,
    QuickReply, QuickReplyButton
)
from linebot.models.actions import PostbackAction
from linebot.models import TemplateSendMessage, ButtonsTemplate, MessageAction, ImageSendMessage

app = Flask(__name__)
port = 8889

# line_bot_api = LineBotApi(os.getenv('HR_CHANNEL_ACCESS_TOKEN'))
# handler = WebhookHandler(os.getenv('HR_CHANNEL_SECRET'))
# callbackdomain = os.getenv('HR_CALLBACK_DOMAIN')

line_bot_api = LineBotApi(os.getenv('YT_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('YT_CHANNEL_SECRET'))
callbackdomain = os.getenv('YT_CALLBACK_DOMAIN')

storagedir = "/storage/"

urlprefix = urllib.parse.urljoin(callbackdomain,storagedir)

@app.route("/callback", methods=['POST'])
def callback():

    print(line_bot_api)
    print(handler)
    # get X-Line-Signature header value
    # print(request.headers)
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="youtube url = %s" % event.message.text))
    
@app.route('/storage/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)

