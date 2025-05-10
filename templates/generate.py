#!/usr/bin/env python3
"""
FastAPIテンプレート用リソース生成スクリプト
このスクリプトはテンプレートからリソースファイルを生成します。
"""

import os
import sys
import re
from pathlib import Path
import shutil


def snake_to_camel(snake_str):
    """スネークケースをキャメルケースに変換します。"""
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)


def generate_model(resource_name):
    """モデル、CRUD、スキーマファイルを生成します。"""
    # リソース名の検証（スネークケースであること）
    if not re.match(r'^[a-z][a-z0-9_]*$', resource_name):
        print(f"エラー: リソース名 '{resource_name}' が無効です。スネークケース形式である必要があります。")
        sys.exit(1)

    # リソース名をキャメルケースに変換
    resource_class_name = snake_to_camel(resource_name)

    # テンプレートディレクトリの取得
    template_dir = Path(__file__).parent
    app_dir = template_dir.parent / 'app'

    # テンプレートマッピングの定義
    template_mappings = [
        {
            'template': template_dir / 'db' / 'crud' / 'resource.py.template',
            'destination': app_dir / 'db' / 'crud' / f'{resource_name}.py',
        },
        {
            'template': template_dir / 'db' / 'models' / 'resource.py.template',
            'destination': app_dir / 'db' / 'models' / f'{resource_name}.py',
        },
        {
            'template': template_dir / 'db' / 'schemas' / 'resource.py.template',
            'destination': app_dir / 'db' / 'schemas' / f'{resource_name}.py',
        },
    ]

    # 各テンプレートの処理
    for mapping in template_mappings:
        process_template(mapping, resource_name, resource_class_name)

    # __init__.pyファイルの更新
    update_init_files(resource_name, resource_class_name, app_dir)

    print(f"\nモデル '{resource_name}' が正常に生成されました！")
    print(f"APIルーターを生成するには、次のコマンドを実行してください:")
    print(f"make router:generate NAME={resource_name}")


def generate_router(resource_name):
    """APIルーターファイルを生成します。"""
    # リソース名の検証（スネークケースであること）
    if not re.match(r'^[a-z][a-z0-9_]*$', resource_name):
        print(f"エラー: リソース名 '{resource_name}' が無効です。スネークケース形式である必要があります。")
        sys.exit(1)

    # リソース名をキャメルケースに変換
    resource_class_name = snake_to_camel(resource_name)

    # テンプレートディレクトリの取得
    template_dir = Path(__file__).parent
    app_dir = template_dir.parent / 'app'

    # テンプレートマッピングの定義
    template_mappings = [
        {
            'template': template_dir / 'api' / 'v1' / 'resource.py.template',
            'destination': app_dir / 'api' / 'v1' / f'{resource_name}s.py',
        },
    ]

    # 各テンプレートの処理
    for mapping in template_mappings:
        process_template(mapping, resource_name, resource_class_name)

    print(f"\nAPIルーター '{resource_name}s' が正常に生成されました！")
    print(f"app/api/v1/__init__.pyにルーターを登録することを忘れないでください")
    print(f"例: router.include_router({resource_name}s.router, prefix='/{resource_name}s', tags=['{resource_class_name}s'])")


def process_template(mapping, resource_name, resource_class_name):
    """テンプレートを処理して出力ファイルを生成します。"""
    template_path = mapping['template']
    destination_path = mapping['destination']

    # 出力先ファイルが既に存在するかチェック
    if destination_path.exists():
        overwrite = input(f"ファイル {destination_path} は既に存在します。上書きしますか？ (y/n): ")
        if overwrite.lower() != 'y':
            print(f"{destination_path} をスキップします")
            return

    # 親ディレクトリが存在しない場合は作成
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    # テンプレート内容の読み込み
    with open(template_path, 'r') as f:
        content = f.read()

    # プレースホルダーの置換
    content = content.replace('{resource_name}', resource_name)
    content = content.replace('{Resource}', resource_class_name)

    # 出力先に書き込み
    with open(destination_path, 'w') as f:
        f.write(content)

    print(f"{destination_path} を生成しました")


def update_init_files(resource_name, resource_class_name, app_dir):
    """__init__.pyファイルを更新して新しいリソースをインポートします。"""
    # db/crud/__init__.pyの更新
    crud_init_path = app_dir / 'db' / 'crud' / '__init__.py'
    if crud_init_path.exists():
        with open(crud_init_path, 'r') as f:
            content = f.read()

        # インポートが既に存在するかチェック
        import_line = f"from .{resource_name} import {resource_name}"
        if import_line not in content:
            # ファイルの末尾にインポートを追加
            with open(crud_init_path, 'a') as f:
                f.write(f"\n{import_line}\n")
            print(f"{crud_init_path} を更新しました")

    # db/models/__init__.pyの更新
    models_init_path = app_dir / 'db' / 'models' / '__init__.py'
    if models_init_path.exists():
        with open(models_init_path, 'r') as f:
            content = f.read()

        # インポートが既に存在するかチェック
        import_line = f"from .{resource_name} import {resource_class_name}"
        if import_line not in content:
            # ファイルの末尾にインポートを追加
            with open(models_init_path, 'a') as f:
                f.write(f"\n{import_line}\n")
            print(f"{models_init_path} を更新しました")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用方法: python generate.py <command> <resource_name>")
        print("コマンド:")
        print("  model  - モデル、CRUD、スキーマファイルを生成")
        print("  router - APIルーターファイルを生成")
        print("例: python generate.py model blog_post")
        sys.exit(1)

    command = sys.argv[1]
    resource_name = sys.argv[2]

    if command == "model":
        generate_model(resource_name)
    elif command == "router":
        generate_router(resource_name)
    else:
        print(f"不明なコマンド: {command}")
        print("有効なコマンド: model, router")
        sys.exit(1)
