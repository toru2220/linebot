import os
import asyncio
import urllib.parse
from urllib.parse import quote

# datetimeモジュールを使用
import datetime
import random
import uuid
import shutil
import json

from flask import Flask, Blueprint, request, abort, send_from_directory

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
from linebot.models import TemplateSendMessage, ButtonsTemplate, MessageAction, ImageSendMessage, FlexSendMessage
from yt_dlp import YoutubeDL,DownloadError
from urllib.parse import urljoin,unquote,urlparse

staticdir = "/static/"
moviedir = "/movie/"
audiodir = "/audio/"

app = Flask(__name__)

movieBp = Blueprint("movie", __name__, static_folder="movie", static_url_path="/movie")
audioBp = Blueprint("audio", __name__, static_folder="audio", static_url_path="/audio")

app.register_blueprint(movieBp)
app.register_blueprint(audioBp)

port = 8891

line_bot_api = LineBotApi(os.getenv('YT_CHANNEL_ACCESS_TOKEN',''))
handler = WebhookHandler(os.getenv('YT_CHANNEL_SECRET',''))
userid = os.getenv('YT_CHANNEL_USERID','')
callbackdomain = os.getenv('YT_CALLBACK_DOMAIN','')

staticprefix = urllib.parse.urljoin(callbackdomain,staticdir)
movieprefix = urllib.parse.urljoin(callbackdomain,moviedir)
audioprefix = urllib.parse.urljoin(callbackdomain,audiodir)

def is_url(url):
  try:
    result = urlparse(url)
    return all([result.scheme, result.netloc])
  except ValueError:
    return False
  
@app.route("/callback", methods=['POST'])
def callback():

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

    print("####################")
    print(event.message)
    print("####################")

    targeturl = event.message.text
    tmpfile = "./apps/%s/%s" % (moviedir,str(uuid.uuid4()))

    # URLとして解釈できない場合は処理しない
    if is_url(targeturl) == False:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="URLとして解釈できないため処理は中断されました。" ))
        
        return "OK"
    
    # youtube-dlでdownload
    headers = {
        "Referer" : targeturl,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
    }

    request_vars = {
        "verbose": True,
        "outtmpl": tmpfile,
        "fixup" : "never",
        # "socket_timeout" : 15000,
        "http_headers" : headers,
        "nocheckcertificate" : True,
        "format" : "bestvideo+bestaudio/best"
    }

    # simulate = Trueでmetadata取得
    request_vars["simulate"] = True

    outputfilename = ""
    with YoutubeDL(request_vars) as ydl:
        metadata = ydl.extract_info(targeturl)

        # for key, value in metadata.items():
        #     print("Key:", key)
        #     print("Value:", value)

        outputfilename = "./apps/%s/%s.%s" % (moviedir,metadata["fulltitle"],metadata["ext"])

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="ダウンロードを開始します。 url = %s" % targeturl ))
    
    try:
        request_vars["simulate"] = False       
        with YoutubeDL(request_vars) as ydl:
            metadata = ydl.extract_info(targeturl)

        if os.path.exists(tmpfile):

            shutil.move(tmpfile, outputfilename)

            downloadedurl = urllib.parse.urljoin(movieprefix,quote(os.path.basename(outputfilename)))

            print("downloaded path:%s" % downloadedurl)

            payload = f"""{{
                "type": "flex",
                "altText": "download complete",
                "contents": {{
                    "type": "bubble",
                    "hero": {{
                        "type": "image",
                        "url": "{metadata['thumbnail']}",
                        "size": "full",
                        "aspectRatio": "20:13",
                        "aspectMode": "cover",
                        "action": {{
                        "type": "uri",
                        "uri": "{downloadedurl}"
                        }}    
                    }},
                    "body": {{
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {{
                            "type": "text",
                            "text": "{metadata['fulltitle']}",
                            "weight": "bold",
                            "size": "lg"
                        }}
                        ]
                    }}
                }}
            }}"""

            jsonDict = json.loads(payload)

            container_obj = FlexSendMessage.new_from_json_dict(jsonDict)

            #最後に、push_messageメソッドを使ってPUSH送信する
            line_bot_api.push_message(to=userid, messages=container_obj)

            # # Flexメッセージのコンテンツを定義
            # # 注意点として、トリプルクォート内で波括弧 {} を表現するためには、二重の波括弧 {{}} を使用する必要があります。
            # flex_message = f"""{{
            #     "type": "bubble",
            #     "hero": {{
            #         "type": "image",
            #         "url": "{metadata['thumbnail']}",
            #         "size": "full",
            #         "aspectRatio": "20:13",
            #         "aspectMode": "cover",
            #         "action": {{
            #         "type": "uri",
            #         "uri": "{downloadedurl}"
            #         }}
            #     }},
            #     "body": {{
            #         "type": "box",
            #         "layout": "vertical",
            #         "contents": [
            #         {{
            #             "type": "text",
            #             "text": "{metadata['fulltitle']}",
            #             "weight": "bold",
            #             "size": "lg"
            #         }}
            #         ]
            #     }}
            # }}
            # """

            # # json_string = json.dumps(flex_message)

            # # FlexSendMessageオブジェクトを作成
            # flex_send_message = FlexSendMessage(alt_text='download complete', contents=flex_message)

            # # メッセージを送信
            # line_bot_api.push_message(to=userid, messages=flex_send_message)



            # # 画像メッセージ
            # message_confirmimage = ImageSendMessage(
            #     original_content_url=metadata["thumbnail"],
            #     preview_image_url=metadata["thumbnail"]
            # )

            # # メッセージを送信
            # line_bot_api.push_message(userid, messages=message_confirmimage)
            # # line_bot_api.push_message(userid, messages=message_reportedimage)
        

            # # メッセージの作成
            # message = TextSendMessage(text="ダウンロードが完了しました。")

            # # メッセージの送信
            # line_bot_api.push_message(userid, message)


        else:
            pass

    except Exception as e:

        print("error:%s" % e)
        # メッセージの作成
        message = TextSendMessage(text="対応していないURLが指定されました。中断します。 url = %s" % targeturl)

        # メッセージの送信
        line_bot_api.push_message(userid, message)



@app.route("/report", methods=['GET'])
def make_quick_reply():

    metadata = {
        "url" : "https://www.google.com",
        "title" : "TAS",
    }

    payload = f"""{{
        "type": "flex",
        "altText": "download complete",
        "contents": {{
            "type": "bubble",
            "hero": {{
                "type": "image",
                "url": "{metadata['url']}",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover",
                "action": {{
                "type": "uri",
                "uri": "{metadata['url']}"
                }}    
            }},
            "body": {{
                "type": "box",
                "layout": "vertical",
                "contents": [
                {{
                    "type": "text",
                    "text": "{metadata['title']}",
                    "weight": "bold",
                    "size": "lg"
                }}
                ]
            }}
        }}
    }}"""

    jsonDict = json.loads(payload)

    container_obj = FlexSendMessage.new_from_json_dict(jsonDict)

    #最後に、push_messageメソッドを使ってPUSH送信する
    line_bot_api.push_message(to=userid, messages=container_obj)

    #     # FlexSendMessageオブジェクトを作成
    # flex_send_message = FlexSendMessage(alt_text='download complete', contents=json_string)
    # # flex_send_message = FlexSendMessage(alt_text='download complete', contents=flex_message)

    # # メッセージを送信
    # line_bot_api.push_message(to=userid, messages=flex_send_message)

    return 'OK'

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)


