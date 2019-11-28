#!/usr/bin/python
#-*-coding:utf-8-*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4
# copyright 2019 WShuai, Inc.
# All Rights Reserved.

# @File: qrobot.py
# @Author: WShuai, WShuai, Inc.
# @Time: 2019/11/27 19:29

import os
import json
import uuid
import execjs
import logging
import requests

FORMAT = '[%(asctime)s]  [%(process)d] [%(thread)d] [%(filename)16s:%(lineno)4d] [%(levelname)-6s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

class QRobot(object):
    def __init__(self, login_user, target_user, target_path, cookie, logger):
        self.login_user = login_user
        self.target_user = target_user
        self.target_path = target_path
        self.cookie = cookie
        self.logger = logger
        self.headers = {
            'Referer': 'https://qzs.qq.com/qzone/photo/v7/page/photo.html?init=photo.v7/module/albumList/index&navBar=1',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0 Iceweasel/38.3.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'cookie': cookie
        }
        self.session = None
        self.t = None
        self.gtk = None
        self.gtk_t = None
        self.albums = []
        return

    def http_get(self, url):
        response = None
        while True:
            try:
                response = self.session.get(url, headers = self.headers)
                break
            except requests.exceptions.Timeout:
                self.logger.error('http get {0} timeout, retry...'.format(url))
            except requests.exceptions.ConnectionError:
                self.logger.error('http get {0} connect error, retry...'.format(url))
        return response.content

    def get_params(self):
        self.t = execjs.compile("function time(){return String(Math.random().toFixed(16)).slice(-9).replace(/^0/, '9')}").call('time')
        self.gtk_t = 'function a(skey){var hash = 5381;for (var i = 0, len = skey.length;i < len;++i) {hash += (hash << 5) + skey.charCodeAt(i);}return hash & 2147483647;}'
        self.gtk = execjs.compile(self.gtk_t).call('a', self.cookie.split("p_skey=")[1].split(";")[0])
        self.session = requests.session()
        return

    def get_album(self):
        albums_url = "{0}?{1}&{2}&{3}&{4}&{5}&{6}&{7}&{8}&{9}&{10}&{11}&{12}&{13}&{14}&{15}&{16}&{17}&{18}&{19}&{20}".format(
            "https://h5.qzone.qq.com/proxy/domain/photo.qzone.qq.com/fcgi-bin/fcg_list_album_v3",
            "t={0}".format(self.t),
            "g_tk={0}".format(self.gtk),
            "uin={0}".format(self.login_user),
            "hostUin={0}".format(self.target_user),
            "callback=shine0_Callback",
            "appid=4",
            "inCharset=utf-8",
            "outCharset=utf-8",
            "source=qzone",
            "plat=qzone",
            "format=jsonp",
            "notice=0",
            "filter=1",
            "handset=4",
            "pageNumModeSort=40",
            "pageNumModeClass=15",
            "needUserInfo=1",
            "idcNum=4",
            "callbackFun=shine0",
            "_=1516544656243"
        )
        result = self.http_get(albums_url)
        if result:
            decode_result = result.decode()
            json_result = json.loads(decode_result[decode_result.index('{'):decode_result.rindex('}')+1].replace('\n', '').replace(' ', '').replace('\t', ''))
            self.albums = json_result['data']['albumListModeSort']
        return

    def get_photo(self):
        for album in self.albums:
            #self.logger.debug('album id is {0}'.format(album['id']))
            count = int(album['total'] / 500) + 1
            for index in range(count):
                album_url = '{0}?{1}&{2}&{3}&{4}&{5}&{6}&{7}&{8}&{9}&{10}&{11}&{12}&{13}'.format(
                    'https://h5.qzone.qq.com/proxy/domain/photo.qzone.qq.com/fcgi-bin/cgi_list_photo',
                    'g_tk={0}'.format(self.gtk),
                    't={0}'.format(self.t),
                    'hostUin={0}'.format(self.target_user),
                    'topicId={0}'.format(album['id']),
                    'uin={0}'.format(self.login_user),
                    'pageStart={0}'.format(index * 500),
                    'pageNum={0}'.format(500),
                    'callback=shine0_Callback',
                    'mode=0&idcNum=4&noTopic=0',
                    'skipCmtCount=0&singleurl=1&batchId=&notice=0&appid=4',
                    'inCharset=utf-8&outCharset=utf-8',
                    'source=qzone&plat=qzone',
                    'outstyle=json&format=jsonp&json_esc=1&question=&answer=&callbackFun=shine0&_=1516549331973'
                )
                result = self.http_get(album_url)
                if result:
                    decode_result = result.decode()
                    json_result = json.loads(
                        decode_result[decode_result.index('{'):decode_result.rindex('}') + 1].replace('\n', '').replace(
                            ' ', '').replace('\t', '')
                    )

                    album['photo_urls'] = [item['url'] for item in json_result['data']['photoList']]
        return

    def download_photo(self):
        #self.logger.debug('self.albums is {0}'.format(self.albums))
        for album in self.albums:
            for photo_url in album['photo_urls']:
                try:
                    result = self.http_get(photo_url)
                    #self.logger.debug('name is {0}'.format(album['name']))
                    image_path = os.path.join(self.target_path, album['name'])
                    if not os.path.isdir(image_path):
                        os.makedirs(image_path)
                    image_file = os.path.join(image_path, '{0}.jpg'.format(uuid.uuid4()))
                    with open(image_file, 'wb') as file_handler:
                        file_handler.write(result)
                except Exception as e:
                    self.logger.error('download {0} Exception: {1}'.format(photo_url, e))
        return

import sys
import argparse
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--login_user", help="login user QQ number", type=str, required=True)
    parser.add_argument("--target_user", help="target user QQ number", type=str, required=True)
    parser.add_argument("--target_path", help="target path save images", type=str, required=True)
    parser.add_argument("--cookie", help="cookie", type=str, required=True)
    args = parser.parse_args()

    if not args.target_path:
        args.target_path = './target'

    qrbot = QRobot(args.login_user, args.target_user, args.target_path, args.cookie, logging)
    qrbot.get_params()
    qrbot.get_album()
    qrbot.get_photo()
    qrbot.download_photo()
    sys.exit(0)
