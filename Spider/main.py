import json
import os
from time import sleep
from datetime import datetime
import logging
import redis
import multiprocessing
from sysuwebsite import *


def send_notification(title, content=''):
    with open('notification_list.json', 'r', encoding='utf-8') as nf_list:
        notification_list = json.load(nf_list)
    for user in notification_list:
        while True:
            message = {
                'text': title,
                'desp': 'Hi! %s: \n\n%s\n\n%s' % (user['name'], content, datetime.now().strftime("%m-%d %H:%M"))
            }
            try:
                requests.post(user['url'], message)
                break
            except BaseException as e:
                logging.error(e)
                sleep(5)


def post_big_news(website):
    token = '_your_token_'
    while True:
        try:
            requests.post(url='http://cat.sysu.space/api/big-news',
                          data={
                              'token': token,
                              'name': website.name,
                              'url': website.url
                          })
            break
        except BaseException as e:
            logging.error(e)
            sleep(5)


def send_codo(website):
    while True:
        try:
            response = requests.post(
                url="http://api.sysu.space/api/reminder",
                params={
                    "token": token,
                },
                data={
                    "channel_id": "211",
                    "title": website.name,
                    "content": website.url,
                    "priority": "2",
                    "type": "0",
                }
            )
            if json.loads(response.text)['ret'] == 0:
                break
        except BaseException as e:
            logging.error(e)
            sleep(5)


def spider_task(website):
    res = website.read()
    if res is None:
        logging.warning('Read from %s fail.' % website.name)
        return None
    logging.info('Read from %s succeed.' % website.name)
    redis_db = redis.StrictRedis()
    last_data = redis_db.get(website.name)
    if last_data is None:
        redis_db.set(website.name, res)
        logging.info('Initialize %s done.' % website.name)
    else:
        if res != last_data:
            msg = '%s又有新内容啦！[点我直达网站！](%s)' % (website.name, website.url)
            redis_db.set(website.name, res)
            logging.info('%s搞了个大新闻。' % website.name)
            send_notification('%s搞了个大新闻' % website.name, msg)
            post_big_news(website)
            send_codo(website)
        else:
            logging.info('%s闷声发大财。' % website.name)


def master(queue, sleep_time):
    logging.info('Master start.')
    website_list = [
        StaticWebsite('人工智能课件', 'http://smie2.sysu.edu.cn/~ryh/ai/presentation.html'),
        StaticWebsite('人工智能作业', 'http://smie2.sysu.edu.cn/~ryh/ai/homework.html'),
        StaticWebsite('人工智能实验', 'http://smie2.sysu.edu.cn/~ryh/ai/lab.html'),
        StaticWebsite('云计算', 'http://sdcs.sysu.edu.cn/space/080004/ccapp/'),
        StaticWebsite('无线传感器课件', 'http://sdcs.sysu.edu.cn/space/090058/'),
        StaticWebsite('嵌入式作业',
                      'http://human-robot.sysu.edu.cn/course/%e5%b5%8c%e5%85%a5%e5%bc%8f%e5%af%bc%e8%ae%ba1.htm'),
        EdinWebsite('移动应用开发', 'http://edin.sysu.edu.cn/wiki/doku.php?id=mad2016'),
        ElearningWebsite('数据库实验文档',
                         'http://elearning.sysu.edu.cn/webapps/blackboard/content/listContent.jsp?course_id=_12034_1&content_id=_248969_1',
                         '_248969_1'),
        ElearningWebsite('数据库实验作业',
                         'http://elearning.sysu.edu.cn/webapps/blackboard/content/listContent.jsp?course_id=_12034_1&content_id=_249029_1',
                         '_249029_1'),
        ElearningWebsite('数据库理论作业',
                         'http://elearning.sysu.edu.cn/webapps/blackboard/content/listContent.jsp?course_id=_12034_1&content_id=_249159_1',
                         '_249159_1'),
        XiaoxiWebsite('Web 实验', 'http://172.18.187.11'),
        FTPWebsite('计网实验', 'ftp://222.200.180.109', '222.200.180.109', 21, '16net', 'b402')
    ]
    while True:
        for website in website_list:
            queue.put(website)
            logging.info('Put %s in queue' % website.name)
        sleep(sleep_time)


def slave(queue):
    logging.info('Slave start.')
    pools_size = 2
    pool = multiprocessing.Pool(processes=pools_size)
    while True:
        website = queue.get()
        logging.info('%s get %s' % (os.getpid(), website.name))
        pool.apply_async(func=spider_task, args=(website,))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    website_queue = multiprocessing.Queue()
    master_p = multiprocessing.Process(target=master, args=(website_queue, 20), name='Master')
    slave_p = multiprocessing.Process(target=slave, args=(website_queue,), name='Slave')
    slave_p.start()
    master_p.start()
    check_time = 120
    while True:
        if not master_p.is_alive():
            logging.error('Master exit unexpected.')
            exit(1)
        if not slave_p.is_alive():
            logging.error('Slave exit unexpected.')
            exit(1)
        sleep(check_time)
