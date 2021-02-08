# -*- coding: UTF-8 -*-
import json

import requests

from snmp_cmds import snmpwalk
from concurrent.futures import ThreadPoolExecutor
import time


def get_ip_from_oid(oid):
    """
    :params:
    oid: 形式如下：'.1.3.6.1.2.1.4.22.1.2.4097.10.254.1.1'
    :return: '10.254.1.1'
    """
    return '.'.join(oid.split('.')[-4:])


def format_mac(mac_str):
    # 规范Mac地址
    """
    :params:
    oid: 形式如下：'0:1c:54:42:40:db'
    :return: '00:1c:54:42:40:db'
    """

    mac_list = []

    # mac_str 形式如：'0:1c:54:42:40:db'
    if ':' in mac_str:
        mac_list = mac_str

    # mac_str 形式如：'00 11 22 33 44 55' 分隔符为空格改为':'
    elif ' ' in mac_str:
        mac_list = ':'.join(mac_str.split(' '))

    # mac_str 形式如： 'abcd-abcd-abcd' 或'abcd.abcd.abcd' 分隔符'-'或'.'改为':'
    elif '-' or '.' in mac_str:
        mac_res = []
        for j in ('-', '.'):
            for i in mac_str.split(j):
                mac_res.append(i[:2])
                mac_res.append(i[-2:])
            mac_list = ':'.join(mac_res)

    else:
        print(mac_str + "格式错误")

    mac_result = []
    # '0:1c:54:42:40:db'改为 '00:1c:54:42:40:db'
    for i in mac_list.split(':'):
        mac_result.append('0' + i) if len(i) == 1 else mac_result.append(i)

    # lower()把大写字母全部改为小写
    return ':'.join(mac_result).lower()


def get_oid_mac(ip, oid, community):
    """

    :param ip:
    :param oid:
    :param community:
    :return: 形式如下：'.1.3.6.1.2.1.4.22.1.2.4097.10.254.1.1' '00:1c:54:42:40:db'
    """
    return snmpwalk(ipaddress=ip, oid=oid, community=community)


class ItmpApi(object):

    def __init__(self, itmp_ip):
        self.header = {
            "Authorization": "JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiZXhwIjoxNjEwMzI4MjkyLCJlbWFpbCI6ImFkbWluQG1jZW50ZXIuY29tIn0.FvF1HvgBq0KrK6w0ZnWmmky-NBkBeTs2UqeWtYyZPj8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
            "Content-Type": "application/json"
        }
        self.itmp_ip = itmp_ip

    # 获得json数据形如{'count':1, 'results':[]}
    def get_ip_addr_manage(self, params):
        return requests.get(
            url='http://{}/v1/asset/ip-addr-manage/'.format(self.itmp_ip),
            params=params,
            headers=self.header
        ).json()

    # 把Mac地址赋给对应的ip地址
    def patch_ip_addr_manage(self, ip_addr_manage_id, data):
        return requests.patch(
            url='http://{}/v1/asset/ip-addr-manage/{ip_addr_id}/'.format(
                self.itmp_ip, ip_addr_id=str(ip_addr_manage_id)
            ),
            # data 为Mac地址
            data=json.dumps(data),
            headers=self.header,
        )

    # 以post方式获得json数据
    def get_assets_ip(self, data):
        return requests.post(
            url="http://{}/v1/asset/assetlist/".format(self.itmp_ip),
            headers=self.header,
            data=json.dumps(data)
        ).json()


def distribution_mac(results, to_project_id):
    to_project_result = {}
    ip_mac_result_dic = {}
    for j in results:
        ip_mac_result_dic[get_ip_from_oid(j[0])] = format_mac(j[1])
    # {to_project1: {ip: mac, ip2: mac2}, to_project2: {ip: mac, ip2: mac2}}
    for i in to_project_id:
        to_project_result[i] = ip_mac_result_dic

    itmp_obj = ItmpApi('10.254.50.229:18020')
    for to_project in to_project_result:
        for key in to_project_result[to_project]:  # key:ip
            ip_addr_manage = itmp_obj.get_ip_addr_manage(
                {'page': 1, 'page_size': 20, 'ip_addr': key, 'to_project': to_project})
            print(ip_addr_manage)
            if ip_addr_manage['count'] == 1:
                itmp_obj.patch_ip_addr_manage(str(ip_addr_manage['results'][0]['id']),
                                              {"mac_addr": ip_mac_result_dic[key]})
                print(0)
            else:
                print(key)


def process(ip, oid, community, to_project_id):
    res = get_oid_mac(ip, oid, community)
    distribution_mac(res, to_project_id)


def main():
    # 加载配置文件的内容，result为配置文件的内容列表
    with open(r"D:\PycharmProject\ip-oid-co.txt", 'r') as f:
        result = []
        for line in f:
            result.append(list(line.strip('\n').split(',')))
    ip = []
    oid = []
    community = []
    to_project_id = []
    for i in result:
        ip.append(i[0])
        oid.append(i[1])
        community.append(i[2])
        to_project_id.append(i[3])

    # 创建有4个线程的线程池
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(process, ip, oid, community, to_project_id)


if __name__ == '__main__':
    main()

