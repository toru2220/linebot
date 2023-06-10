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
from pprint import pprint
from pydub import AudioSegment

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
from urllib.parse import urljoin,unquote,urlparse,parse_qs

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

def convert_to_mp3(input_path, output_path, bitrate='192k'):
    audio = AudioSegment.from_file(input_path)
    audio.export(output_path, format='mp3', bitrate=bitrate)

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
    metadata = {}
    with YoutubeDL(request_vars) as ydl:
        metadata = ydl.extract_info(targeturl)

        # for key, value in metadata.items():
        #     print("Key:", key)
        #     print("Value:", value)

        outputfilename = "./apps/%s/%s.%s" % (moviedir,metadata["fulltitle"],metadata["ext"])

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"{metadata['fulltitle']}のダウンロードを開始します。"))
    
    try:
        request_vars["simulate"] = False       
        with YoutubeDL(request_vars) as ydl:
            metadata = ydl.extract_info(targeturl)

        # print("#### downloaded metadata #####")
        # pprint(metadata)
        # print(metadata["requested_downloads"][0]["filepath"])
        # print("###########")

        downloadedtmpfile = metadata["requested_downloads"][0]["filepath"]

        if os.path.exists(downloadedtmpfile):

            shutil.move(downloadedtmpfile, outputfilename)

            downloadedurl = urllib.parse.urljoin(movieprefix,quote(os.path.basename(outputfilename)))

            print("downloaded path:%s" % downloadedurl)

            payload = f"""{{
                "type": "flex",
                "altText": "download complete",
                "contents": {{
                    "type": "bubble",
                    "size": "giga",
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
                            "weight": "regular",
                            "size": "xxs",
                            "align": "start"
                        }}
                        ]
                    }},
                    "footer": {{
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                        {{
                            "type": "image",
                            "url": "{staticprefix}/convert.png",
                            "action": {{
                            "type": "postback",
                            "label": "Audio変換",
                            "data": "type=convert2audio&name={quote(os.path.basename(outputfilename))}"
                            }},
                            "size": "xxs"
                        }}
                        ],
                        "flex": 0
                    }}     
                }}              
            }}"""
            jsonDict = json.loads(payload)

            container_obj = FlexSendMessage.new_from_json_dict(jsonDict)

            #最後に、push_messageメソッドを使ってPUSH送信する
            line_bot_api.push_message(to=userid, messages=container_obj)

        else:
            print("file not found:%s" % tmpfile)
            pass

    except Exception as e:

        print("error:%s" % e)
        # メッセージの作成
        message = TextSendMessage(text="対応していないURLが指定されました。中断します。 url = %s" % targeturl)

        # メッセージの送信
        line_bot_api.push_message(userid, message)

@handler.add(PostbackEvent)
def handle_postback_event(event):
    # postbackイベントの処理
    postback_data = event.postback.data
    reply_message = "Received postback data: " + postback_data

    # クエリ文字列を解析してキーと値のペアを取得
    parameters = parse_qs(postback_data)

    # typeがkeyにない場合は処理しない

    if not "type" in parameters:
        # メッセージの作成
        message = TextSendMessage(text="変換方法が指定されていません。中断します。")
        # メッセージの送信
        line_bot_api.push_message(userid, message)

        return "OK"
    
    if not "name" in parameters:
        # メッセージの作成
        message = TextSendMessage(text="ファイル名が指定されていません。中断します。")
        # メッセージの送信
        line_bot_api.push_message(userid, message)

        return "OK"
    

    decodedFile = unquote(parameters["name"][0])
    
    targetFullPath = f"./apps/movie/{decodedFile}"
    nameonly, ext = os.path.splitext(decodedFile)
    decodedFulPathMp3 = f"./apps/audio/{nameonly}.mp3"

    # ファイルが見つからない場合は処理しない
    if not os.path.exists(targetFullPath):
        # メッセージの作成
        message = TextSendMessage(text=f"{targetFullPath}が見つかりません。中断します。")
        # メッセージの送信
        line_bot_api.push_message(userid, message)

        return "OK"

    if parameters["type"][0] == "convert2audio":
        # メッセージの作成
        message = TextSendMessage(text="変換を開始します。")
        # メッセージの送信
        line_bot_api.push_message(userid, message)

        convert_to_mp3(targetFullPath, decodedFulPathMp3, bitrate='192k')
        downloadedurl = urllib.parse.urljoin(audioprefix,quote(os.path.basename(decodedFulPathMp3)))

        print(downloadedurl)

        payload = f"""{{
            "type": "flex",
            "altText": "download complete",
            "contents": {{
                "type": "bubble",
                "hero": {{
                    "type": "image",
                    "url": "https://img.freepik.com/premium-vector/modern-flat-design-of-mp3-file-icon-for-web-simple-style_599062-487.jpg",
                    "size": "xxs",
                    "aspectRatio": "5:5",
                    "aspectMode": "cover",
                    "action": {{
                        "type": "uri",
                        "uri": "{downloadedurl}"
                    }}
                }}
            }}              
        }}"""
        jsonDict = json.loads(payload)

        container_obj = FlexSendMessage.new_from_json_dict(jsonDict)

        #最後に、push_messageメソッドを使ってPUSH送信する
        line_bot_api.push_message(to=userid, messages=container_obj)

    return "OK"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)


