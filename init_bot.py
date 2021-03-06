'''下面是bot的初始化'''
import asyncio
import json
from graia.application import GraiaMiraiApplication, Session
from graia.broadcast import Broadcast

from MsgObj import Msg
from config import *

GroupQA = {}
LoveTalkList = []
temp_talk = dict()  # 简易的会话管理器
WelcomeScence = {}
BlackUser = []
# 黑名单
Manager = []
# 超级管理员

start_baiDu_group = []
mast_manager_group = []
quick_find_question_list = {}
shutdown_all_group = []
loop = asyncio.get_event_loop()  # 获取bot运行的协程

json_config={}

bcc = Broadcast(loop=loop)

app = GraiaMiraiApplication(
    broadcast=bcc,
    connect_info=Session(
        host=API_ROOT,  # httpapi 服务运行的地址
        authKey=AuthKey,  # authKey
        account=BOTQQ,  # 机器人的 qq 号
        websocket=True  # Graia 已经可以根据所配置的消息接收的方式来保证消息接收部分的正常运作.
    )
)


async def ReadConfig():
    try:
        with open('config.json','r') as f:
            global json_config
            json_config = json.load(f).copy()
            if 'baiDu_group' in json_config.keys():
                for i in json_config['baiDu_group']:
                    start_baiDu_group.append(i)
            if 'shutdown_all_group' in json_config.keys():
                for i in json_config['shutdown_all_group']:
                    shutdown_all_group.append(i)
            if 'mast_manager_group' in json_config.keys():
                for i in json_config['mast_manager_group']:
                    mast_manager_group.append(i)
            print('初始化配置完成')

        pass
    except Exception:
        print('读取配置失败')
        pass


def SaveConfig():
    with open('config.json', 'w') as f:
        json_config['baiDu_group']=start_baiDu_group
        json_config['shutdown_all_group']=shutdown_all_group
        json_config['mast_manager_group']=mast_manager_group
        json.dump(json_config,f)
    pass


async def ReadQA():
    try:
        with open('QAindex.json', 'r') as f:
            tempDict = json.loads(f.read())
            for i in tempDict.keys():
                GroupQA[int(i)] = tempDict[i]
                for key in GroupQA[int(i)].keys():
                    t = tempDict[i][key]
                    GroupQA[int(i)][key] = Msg()
                    GroupQA[int(i)][key].set_dict_from_json(t)
                quick_find_question_list[int(i)] = sorted(GroupQA[int(i)].keys(), key=lambda i: len(i), reverse=False)
            f.close()
            print("读取结束")
    except:
        with open('QAIndex.json', 'w+') as f:
            f.close()


async def saveQA():  # 对已有问答数据进行保存
    AllData = dict()
    with open('QAindex.json', 'w+') as f:
        for key in GroupQA:
            t_dict = GroupQA[key]
            indexDict = dict()
            for i in t_dict:
                data = json.dumps(t_dict[i].getMsgDict())
                indexDict[i] = data
            AllData[key] = indexDict.copy()
            indexDict.clear()
        f.write(json.dumps(AllData))
        f.close()
    print("已保存")


async def Compatible_old_index():  # 对旧有数据的转化
    with open('QAindex.json', 'r') as f:
        tempDick = json.loads(f.read())
        for i in tempDick.keys():
            tempDick[i] = json.loads(tempDick[i])
            GroupQA[int(i)] = tempDick[i].copy()
            for key in tempDick[i]:
                txt = tempDick[i][key]
                GroupQA[int(i)][key] = Msg()
                TransformDict = {
                    'user_id': None,
                    'at': None,
                    'msg_txt': txt,
                    'img_url': None
                }
                GroupQA[int(i)][key].set_dict(TransformDict)

        f.close()
        await saveQA()
