# PDF比較ツール
<p align="center">
  <img src='../images/logo.png' width=300>
</p>

<p align="center">
    【<a href="../doc/README-English.md">英語</a> | <a href="../doc/README-Chinese.md">中文</a> | 日本語】
</p>

## 📖 概要
このツールは、PDFファイルのコンテンツを校正するのに多くの時間を費やす必要がある人々のために設計されたもので、異なるPDFファイル間の差異を効果的に比較します。このツールで生成された比較結果のサンプルを通じて、PDFファイル間のピクセルとテキストの違いを迅速に識別できます。

比較結果のサンプル：
<p align="center">
  <img src='../images/example.jpg' width=600>
</p>

## ❓ PDF比較ツールは何ができますか？

#### 1. 画像の差異比較
このツールは、対応するページごとに3段構成の比較画像を生成します。上段は左右ページのテキスト差分ハイライト、中段は左右ページのピクセル差分オーバーレイ、下段はグレースケールの絶対差分とその反転表示です。

<p align="center">
  <img src='../images/example_image.jpg' width=900>
</p>

#### 2. テキストの差異比較
このツールは、PDF内のすべての認識可能なテキストを色付きのマスクで表示し、異なる色には異なる意味があります。

- **緑色**：単語は変更されていません。
- **オレンジ色**：テキストは同じですが、サイズや色が変化しています。
- **赤色**：未一致、追加、または変更されたテキストです。

<p align="center">
  <img src='../images/example_text.jpg' width=900>
</p>

### 🖥️ クイックスタート

以下の手順に従って操作してください：

1. **GitHubリポジトリのクローン：** 次のコマンドを使用してリポジトリをクローンします：

```bash
git clone https://github.com/VintLin/pdf-comparator.git
```

2. **Python環境の設定：** "pdf-comparator"プロジェクトディレクトリを開き、Python 3.8以上のバージョンがインストールされていることを確認してください。次のコマンドを使用して、環境を作成しアクティブにします。必要に応じて "venv" を好きな環境名に置き換えてください：

```bash
cd pdf-comparator
python3 -m venv venv
```

3. **依存関係のインストール：** 次のコマンドを実行して必要な依存関係をインストールします：

```bash
pip3 install -r requirements.txt
```

ページ描画は `pypdfium2` を使用するため、`poppler` を別途インストールする必要はありません。

4. **コードを直接実行：** 次のコマンドを使用してPDFファイルを比較します：

```bash
python3 -m pdfcomparator "/compare_file_1.pdf" "/compare_file_2.pdf" "/result_folder/"
```

5. **実行可能ファイルのビルド：** 必要に応じて、cx-Freezeを使用して実行可能ファイルをビルドできます（成功した場合、実行可能ファイルは "/build/" ディレクトリにあります）：

```bash
python3 setup.py build
```

6. **実行可能ファイルを実行：** 次のコマンドを使用してPDFファイルを比較します：

```bash
./pdfcomparator.exe "/compare_file_1.pdf" "/compare_file_2.pdf" "/result_folder/"
```

### コマンドライン引数の使用方法

このプログラムは次のコマンドライン引数を受け付けます：

- `file1`（必須）：ファイル1のパス。比較したい最初のファイルのパスを指定してください。

- `file2`（必須）：ファイル2のパス。比較したい第二のファイルのパスを指定してください。

- `output_folder`（必須）：出力フォルダのパス。比較結果はこのフォルダに保存されます。

- `--log-dir`、`--cache`、または`-c`：`app.log` の出力先ディレクトリを指定するオプションです。`--cache` は互換性維持のための旧別名です。

### 例

以下はいくつかの使用例です：

```bash
# 比較を実行
python3 -m pdfcomparator file1.pdf file2.pdf output_folder/

# 比較を実行し、ログを指定ディレクトリに出力する
python3 -m pdfcomparator file1.pdf file2.pdf output_folder/ --log-dir /path/to/logs
```

## 👨‍💻‍ 貢献者

<a href="https://github.com/VintLin/pdf-comparator/contributors">
  <img src="https://contrib.rocks/image?repo=VintLin/pdf-comparator" />
</a>

[contrib.rocks](https://contrib.rocks)で作成されました。

## ⚖️ ライセンス

- ソースコードライセンス: 当プロジェクトのソースコードはMITライセンスの下でライセンスされています。このライセンスにはMITライセンスの指定条件が含まれており、コードの使用、変更、配布が許可されています。
- プロジェクトのオープンソースステータス: このプロジェクトは確かにオープンソースですが、この指定は主に非営利目的を意図しています。コミュニティからの研究および非商用アプリケーションへの協力と寄付を奨励していますが、プロジェクトのコンポーネントを商業目的で利用する場合、別途ライセンス契約が必要です。

## 🌟 スター履歴

[![Star History Chart](https://api.star-history.com/svg?repos=VintLin/pdf-comparator&type=Date)](https://star-history.com/#VintLin/pdf-comparator&Date)

## 📬 お問い合わせ

質問、フィードバック、またはお問い合わせがある場合は、[vintonlin@gmail.com](mailto:vintonlin@gmail.com) までお気軽にお問い合わせください。
