import os
from dotenv import load_dotenv
from flask import Flask, request, render_template_string
from pyngrok import ngrok

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
                # Colabセッション内に画像を保存(セッション切れで消えます)
                filename = "layout.png"
                image.save(filename)
                uploaded_image_filename = filename

    # HTMLテンプレート（画像があれば表示してクリック取得）
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
       src="{{ uploaded_image }}"
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

@app.route('/save_coordinate', methods=['POST'])
def save_coordinate():
    global table_data
    x = request.form.get("x")
    y = request.form.get("y")
    tableNum = request.form.get("tableNum")

    table_data.append((x, y, tableNum))

    return f"""
    <p>登録しました: テーブル番号 <b>{tableNum}</b> (x={x}, y={y})</p>
    <p><a href='/view_tables'>登録情報を見る</a></p>
    <p><a href='/'>トップへ戻る</a></p>
    """

@app.route('/view_tables')
def view_tables():
    global table_data
    html = "<h2>登録されたテーブル情報</h2>"
    for idx, (x, y, tnum) in enumerate(table_data):
        html += f"<p>{idx+1}：テーブル番号 <b>{tnum}</b> → (x={x}, y={y})</p>"
    html += "<br><a href='/'>トップへ戻る</a>"
    return html

# ---- Flaskサーバー起動 (port=5000) ----
# Colab上でngrokトンネルを開く
public_url = ngrok.connect(5000)
print(" * ngrok tunnel URL:", public_url.public_url)

# Flaskアプリを起動
app.run(port=5000)
s