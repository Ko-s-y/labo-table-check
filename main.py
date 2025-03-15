import os
from io import BytesIO
from dotenv import load_dotenv
from flask import Flask, request, render_template_string, send_file
from pyngrok import ngrok
from PIL import Image, ImageDraw

# .envファイルから環境変数を読み込む
load_dotenv()

auth_token = os.environ.get("NGROK_AUTH_TOKEN")
if not auth_token:
    raise ValueError("環境変数 NGROK_AUTH_TOKEN が設定されていません。")

ngrok.set_auth_token(auth_token)

# Flaskアプリを定義
app = Flask(__name__)

uploaded_image_filename = None
table_data = []  # (x座標, y座標, テーブル番号) のリスト

@app.route('/', methods=['GET', 'POST'])
def index():
    global uploaded_image_filename

    if request.method == 'POST':
        if 'image_file' in request.files:
            image = request.files['image_file']
            if image:
                # layout.png として保存 (セッション切れでファイル消える点に注意)
                filename = "layout.png"
                image.save(filename)
                uploaded_image_filename = filename

    # HTMLテンプレート（画像があれば表示してクリック取得）
    # 画像表示は "/uploaded_image" (下記ルート) を経由して返す
    html_template = '''
<html>
<head>
  <meta charset="utf-8"/>
</head>
<body>
<h2>店舗レイアウトのアップロード</h2>

<!-- 画像アップロードフォーム -->
<form method="POST" enctype="multipart/form-data">
  <input type="file" name="image_file" accept="image/*">
  <button type="submit">アップロード</button>
</form>

{% if uploaded_image %}
  <h3>アップロードされた画像:</h3>
  <img id="floor_image"
       src="/uploaded_image"
       style="max-width:600px; cursor: crosshair;"
       onclick="getClickPosition(event)">

  <script>
    function getClickPosition(event){
      const img = document.getElementById("floor_image");
      const rect = img.getBoundingClientRect();
      // 画像の左上を(0,0)としたときのクリック相対座標
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      const tableNum = prompt("テーブル番号を入力してください（例: 1, 2, 3 ...）");
      if (!tableNum) return;

      const form = document.createElement("form");
      form.method = "POST";
      form.action = "/save_coordinate";

      const inputX = document.createElement("input");
      inputX.type = "hidden";
      inputX.name = "x";
      inputX.value = x;

      const inputY = document.createElement("input");
      inputY.type = "hidden";
      inputY.name = "y";
      inputY.value = y;

      const inputT = document.createElement("input");
      inputT.type = "hidden";
      inputT.name = "tableNum";
      inputT.value = tableNum;

      form.appendChild(inputX);
      form.appendChild(inputY);
      form.appendChild(inputT);

      document.body.appendChild(form);
      form.submit();
    }
  </script>
{% endif %}

<br>
<a href="/view_tables">登録されたテーブル情報を見る</a>

</body>
</html>
    '''

    return render_template_string(html_template, uploaded_image=uploaded_image_filename)

@app.route('/uploaded_image')
def uploaded_image():
    """
    アップロードした画像に、登録された座標を赤枠で描画して返す。
    """
    global uploaded_image_filename, table_data

    if not uploaded_image_filename:
        return "No image uploaded."

    # 1) 画像ファイルをPILで開く
    img = Image.open(uploaded_image_filename)
    draw = ImageDraw.Draw(img)

    # 2) table_data の各テーブル(x, y)に赤枠を描画
    #    ここでは中心(x, y)を囲む 20x20px の四角を例にしています
    #    (x-10, y-10) ～ (x+10, y+10) を囲む
    box_size = 10
    for x_str, y_str, table_num in table_data:
        x = float(x_str)
        y = float(y_str)
        left = x - box_size
        top = y - box_size
        right = x + box_size
        bottom = y + box_size

        # outline='red' -> 赤枠, width=3 -> 枠線太さ3px
        draw.rectangle([left, top, right, bottom], outline='red', width=3)

    # 3) 書き込んだイメージをバイナリとして返す
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/save_coordinate', methods=['POST'])
def save_coordinate():
    """
    テーブルの座標・番号を table_data に追加保存する
    """
    global table_data
    x = request.form.get("x")
    y = request.form.get("y")
    table_num = request.form.get("tableNum")

    table_data.append((x, y, table_num))

    return f"""
    <p>登録しました: テーブル番号 <b>{table_num}</b> (x={x}, y={y})</p>
    <p><a href='/view_tables'>登録情報を見る</a></p>
    <p><a href='/'>トップへ戻る</a></p>
    """

@app.route('/view_tables')
def view_tables():
    """
    登録されているテーブル情報一覧を表示
    """
    global table_data
    html = "<h2>登録されたテーブル情報</h2>"
    for idx, (x, y, tnum) in enumerate(table_data):
        html += f"<p>{idx+1}：テーブル番号 <b>{tnum}</b> → (x={x}, y={y})</p>"
    html += "<br><a href='/'>トップへ戻る</a>"
    return html

# ---- Flaskサーバー起動 (port=5000) ----
public_url = ngrok.connect(5000)
print(" * ngrok tunnel URL:", public_url.public_url)

# Flaskアプリを起動
app.run(port=5000)
