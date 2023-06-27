from flask import Flask, request, render_template
import requests
from lxml import html
import re
from urllib.parse import unquote
import traceback
from threading import Lock
import os
app = Flask(__name__)

# 全局请求计数器
request_counter = 0

# 创建一个锁对象
lock = Lock()


# 从文件加载初始计数器值
if os.path.exists("counter.txt"):
    with open("counter.txt", "r") as file:
        request_counter = int(file.read())


@app.before_request
def before_request():
    global request_counter
    with lock:
        request_counter += 1


@app.teardown_request
def teardownrequest(exc):
    global request_counter
    # 将计数器的值写入到文件
    with lock:
        with open("counter.txt", "w") as file:
            file.write(str(request_counter))


@app.route('/', methods=['GET', 'POST'])
def home():
    global request_counter

    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            return fetch_data(url)
    return render_template('index.html', counter=request_counter)


def fetch_data(url):
    try:
        result = re.findall(
            "https://.+", url)

        if result:
            url = result[0]
        else:
            raise

        # 发送请求
        response = requests.get(url)

        # 解析HTML
        tree = html.fromstring(response.text)

        # 用XPath获取<img>标签的src属性值，即图片地址
        song_cover = tree.xpath('//img[starts-with(@src, "https:")]/@src')
        img_url = song_cover[0] if song_cover else None

        # 用XPath获取<div class="title">的文本内容，即歌曲名称

        song_title_list = tree.xpath('//div[@class="title"]/text()')
        if not song_title_list:
            song_title_list = tree.xpath(
                '//div[@class="artist-name ellipse"]/text()')
            if not song_title_list:
                song_title_list = ['none']
        song_title = song_title_list[0]
        # 用XPath获取<script id="RENDER_DATA" type="application/json">中的内容
        script_content = tree.xpath('//script[@id="RENDER_DATA"]')[0].text
        # 用正则截取https到songMaker中的字符串，返回第一个分组的匹配结果

        pattern = r'(https.+btag%3.+[0-9]{3,}).+songMaker'

        match = re.search(pattern, script_content)

        song_url = None
        if match:
            song_url = unquote(match.group(1)).replace(
                "mime_type=audio_mp4", "mime_type=audio_mp3")
        else:
            pattern = r'(https.+btag%3D.{9}).+'
            match = re.search(pattern, script_content)
            if not match:
                print(url)
                raise

        # Render the result template with the fetched data
        return render_template('result.html', song_title=song_title, img_url=img_url, song_url=song_url)
    except Exception:
        traceback.print_exc()
        return render_template('result.html', error="解析失败")


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port="5000")
