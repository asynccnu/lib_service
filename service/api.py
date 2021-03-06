# -*- coding: utf-8 -*-
import json
from . import app
from flask import Blueprint, jsonify, request
from paginate import _Pagination
from spider import search_books, get_book, book_me, renew_book
from decorator import require_lib_login, tojson
from models import connection, Attention

api = Blueprint(
        'api',
        __name__,
        )


@api.route('/lib/login/')
@require_lib_login
def api_lib_login(s, sid):
    """
    :function: api_lib_login
    :args:
        - s: 爬虫session对象
        - sid: 学号
    :rv: json message

    模拟登录图书馆API
    """
    app.logger.debug('User {sid} logged in'.format(sid=sid))
    return jsonify({}), 200


@api.route('/lib/search/')
def api_search_books():
    """
    :function: api_search_books
    :args: none
    :rv: 图书信息
    搜索图书, 返回图书相关信息, 分页(每页20条)
    """
    per_page = 20
    keyword = request.args.get('keyword')
    page = int(request.args.get('page') or '1')
    app.logger.debug('User searched {kw}'.format(kw=keyword))
    if keyword:
        book_info_list = search_books(keyword)
        pg_book_info_list = _Pagination(book_info_list, page, per_page)
        return jsonify({'meta': {
                'max': pg_book_info_list.max_page,
                'per_page': per_page },
            'results': book_info_list[(page-1)*per_page:page*per_page]}), 200


@api.route('/lib/')
def api_book_detail():
    """
    :function: api_book_detail
    :args: none
    :rv: 图书详细信息
    图书详情
    """
    bid = request.args.get('id')
    app.logger.debug('Ask for book {bid} detail'.format(bid=bid))
    return jsonify(get_book(bid)), 200


@api.route('/lib/me/')
@require_lib_login
def api_book_me(s, sid):
    """
    :function: api_book_me
    :args:
        - s: 爬虫session对象
        - sid: 学号
    """
    app.logger.debug("User {sid} get book me".format(sid=sid))
    return jsonify(book_me(s)), 200


@api.route('/lib/renew/', methods=['POST'])
@require_lib_login
def api_renew_book(s, sid):
    """
    :function: api_renew_book
    :args:
        - s: 爬虫session对象
        - bar_code: 图书bar_code字段
        - check: 图书check字段
    """
    bar_code = request.get_json().get('bar_code')
    check = request.get_json().get('check')
    res_code = renew_book(s, bar_code, check)
    return jsonify({}), res_code


@api.route('/lib/create_atten/', methods=['POST'])
@require_lib_login
def api_create_atten(s, sid):
    """
    :function: api_create_atten
    :args:
        - s: 爬虫session对象
        - sid: 学号
    添加关注图书, 存储mongodb数据库
    """
    def init_atten(connection, book_name, book_id, book_bid, book_author, sid):
        """提醒初始化"""
        atten = connection.Attention()
        atten['bid'] = book_bid
        atten['book'] = book_name
        atten['id'] = book_id
        atten['author'] = book_author
        atten['sid'] = sid
        atten.save()
        return atten

    if request.method == 'POST':
        book_bid = request.get_json().get('bid')
        book_name = request.get_json().get('book')
        book_id = request.get_json().get('id')
        book_author = request.get_json().get('author')
        print 'ok'

        if not(book_bid and book_name and book_id and book_author):
            return
        print 'ok'

        atten = connection.Attention.find_one({
            'bid': book_bid,
            'book': book_name,
            'id': book_id,
            'author': book_author,
            'sid': sid
        })
        print 'ok'
        if atten:
            return jsonify({}), 409
        print 'ok'

        atten = init_atten(connection, book_name, book_id, book_bid, book_author, sid)
        print 'ok'
        atten.save()
        print 'ok'
        return jsonify({}), 201


@api.route('/lib/get_atten/')
@require_lib_login
def api_get_atten(s, sid):
    """
    :function: api_get_atten
    :args:
        - s: 爬虫session对象
        - sid: 学号
    获取关注的图书列表
    """
    def isavailable(book_id):
        """获取图书是否可借"""
        book_list = get_book(book_id)
        for book in book_list['books']:
            if book['status'].encode('utf-8') == '\xe5\x8f\xaf\xe5\x80\x9f': return "y"
        return "n"

    all_list = list()
    available_list = list()

    attens = connection.Attention.find({'sid': sid})
    try: attens[0]
    except IndexError: return jsonify({}), 404

    for each_atten in attens:
        all_list.append({
            "bid": each_atten['bid'],
            "book": each_atten['book'],
            "id": each_atten['id'],
            "author": each_atten['author'],
            "avbl": isavailable(each_atten['id'])
        })

    return jsonify(all_list), 200


@api.route('/lib/del_atten/', methods=['DELETE'])
@require_lib_login
def api_del_atten(s, sid):
    """
    :function: api_del_atten
    :args:
        - s: 爬虫session对象
        - sid: 学号
    删除图书关注提醒
    """
    if request.method == 'DELETE':
        book_id = request.get_json().get('id')

        atten = connection.Attention.find_one({
            'id': book_id,
            'sid': sid,
        })

        if not atten: return jsonify({}), 404
        atten.delete()
        return jsonify({}), 200
