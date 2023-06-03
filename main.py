import os
import importlib
from flask import Flask

if __name__ == '__main__':
    app_directory = 'apps'  # アプリファイルが格納されているディレクトリ
    app_files = []

    # ディレクトリ配下のファイルを検索し、.py拡張子を持つファイルを取得
    for file in os.listdir(app_directory):
        if file.endswith('.py') and file != 'main.py':
            app_files.append(file[:-3])

    for app_file in app_files:
        module = importlib.import_module(app_file)
        app = getattr(module, 'app')
        port = getattr(module, 'port')
        app.run(port=port)
