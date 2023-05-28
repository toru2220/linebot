import os
from PIL import Image
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

line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
userid = os.getenv('CHANNEL_USERID')
callbackdomain = os.getenv('CALLBACK_DOMAIN')
starturl = os.getenv('STARTURL')

names = str(os.getenv('NAMES')).split(",")

for key, value in os.environ.items():
    print(f"{key}: {value}")

staticdir = "/static/"

confirmfilename = "confirm.png"
confirmthumbfilename = "confirm_thumb.png"
reportedfilename = "report.png"
reportedthumbfilename = "report_thumb.png"

urlprefix = urllib.parse.urljoin(callbackdomain,staticdir)

confirmimageurl = urllib.parse.urljoin(urlprefix,confirmfilename)
reportedimageurl = urllib.parse.urljoin(urlprefix,reportedfilename)

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

    if event.message.text in names:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="%sの体温記録を開始します。結果通知までしばらくお待ち下さい。" % event.message.text))
        
        with sync_playwright() as playwright:

            confirmimagepath = confirmimageurl.replace(callbackdomain,'.')
            reportedimagepath = reportedimageurl.replace(callbackdomain,'.')

            run(playwright,starturl,event.message.text,confirmimagepath,reportedimagepath)

        # 画像メッセージ
        message_confirmimage = ImageSendMessage(
            original_content_url=confirmimageurl,
            preview_image_url=confirmimageurl
        )

        # 画像メッセージ
        message_reportedimage = ImageSendMessage(
            original_content_url=reportedimageurl,
            preview_image_url=reportedimageurl
        )

        # メッセージを送信
        line_bot_api.push_message(userid, messages=message_confirmimage)
        line_bot_api.push_message(userid, messages=message_reportedimage)
         
    else:
          line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='報告対象の名称でないため記録は行われません'))      

# 検温記録開始
@app.route("/report", methods=['GET'])
def make_quick_reply():

    # namesが設定されていないときは警告メッセージ表示のみ行う
    if os.getenv('NAMES') is None or len(str(os.getenv('NAMES'))) < 1:
        message = TextSendMessage(text='環境変数NAMESが設定されていません。終了します。')
        line_bot_api.push_message(userid, messages=message)
        return "OK"
    
    # ボタンテンプレートメッセージ
    actions = []
    for name in names:
        actions.append(
            MessageAction(
                label=name,  # ボタンテキスト
                text=name  # ボタンを押した時に送信されるメッセージ
            ),
        )

    buttons_template_message = TemplateSendMessage(
        alt_text='Buttons template',
        template=ButtonsTemplate(
            thumbnail_image_url='https://1.bp.blogspot.com/-jJHYvrCnLyo/XlhlE7ZYANI/AAAAAAABXiw/HZVOd4hT5g4UJ0NhIsmcjhE-kM6UMEm-QCNcBGAsYHQ/s1600/medical_taionkei_hand_375.png',  # サムネイル画像URL
            title='記録対象の選択',  # タイトル
            text='名前を選択すると、ランダムで体温を決定し報告を開始します',  # テキスト
            actions=actions
        )
    )

    line_bot_api.push_message(userid, messages=buttons_template_message)

    return 'OK'

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

def resize_image(input_image_path, output_image_path, size):
    original_image = Image.open(input_image_path)
    width, height = original_image.size
    print(f"The original image size is {width} wide x {height} tall")

    resized_image = original_image.resize(size)
    width, height = resized_image.size
    print(f"The resized image size is {width} wide x {height} tall")

    resized_image.save(output_image_path)

def run(playwright,pageurl,name,confirmimage,reportimage):
  
    # 36.4から36.7まで0.1刻みのリストを作成
    nums = [round(i * 0.1, 1) for i in range(364, 368)]

    # リストからランダムに選択
    random_choice = random.choice(nums)

    # 日付
    t_delta = datetime.timedelta(hours=9)
    JST = datetime.timezone(t_delta, 'JST')
    now = datetime.datetime.now(JST)
    datestring = now.strftime('%Y/%m/%d %H:%M')

    chromium = playwright.chromium # or "firefox" or "webkit".
    browser = chromium.launch()
    page = browser.new_page()
    page.set_viewport_size({"width": 720, "height": 1024})
    page.goto(pageurl)

    page.locator("input[aria-label='Single line text']").nth(0).fill(name)
    page.locator("input[aria-label='Single line text']").nth(1).fill(str(random_choice))
    page.locator("input[type=radio]").nth(0).check()
    page.locator("input[aria-label='Single line text']").nth(2).fill(datestring)

    # 入力内容
    page.screenshot(path=confirmimage, full_page=True)

    # 送信
    page.locator("button[data-automation-id=submitButton]").nth(0).click()
    # 通信がアイドル状態になるまで待機
    page.wait_for_load_state("networkidle")

    page.screenshot(path=reportimage, full_page=True)

if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT", 8888))
    app.run(host="0.0.0.0", port=port)
