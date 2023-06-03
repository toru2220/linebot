import os
import importlib
from flask import Flask
import concurrent.futures

def run_app(app, port):
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    app_directory = 'apps'  # アプリファイルが格納されているサブディレクトリ
    app_files = []

    # サブディレクトリ内のファイルを検索し、.py拡張子を持つファイルを取得
    for file in os.listdir(app_directory):
        if file.endswith('.py'):
            app_files.append(file[:-3])

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 各アプリをスレッドで並列実行
        futures = []
        for app_file in app_files:
            module_name = f"{app_directory}.{app_file}"
            future = executor.submit(importlib.import_module, module_name)
            futures.append(future)

        # 完了したスレッドから結果を取得してアプリを起動
        for future in concurrent.futures.as_completed(futures):
            module = future.result()
            app = getattr(module, 'app')
            port = getattr(module, 'port')
            executor.submit(run_app, app, port)
