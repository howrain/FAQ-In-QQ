import functools
import gc
import os
import signal
import subprocess
import sys
import threading
import psutil
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from graia.application import FriendMessage, Friend
from graia.application.event.mirai import *
from graia.broadcast.builtin.decoraters import Depend
from pulgin import *
from MsgObj import Msg
from init_bot import *
from command_session import *
import sched

'''
各文件说明：
    init_bot.py 初始化bot对象和一些需要用到的list或者dict
    faq_bot.py 运行的main文件，包括消息指令入口
    MsgObj.py 独立封装的message消息类，便于对消息数据进行保存和调用
    pulgin.py bot所需要到的一些函数的封装
    config.py bot运行所需要的配置，端口号，bot的QQ号等，配置参见Graia文档
    command_session.py 命令解析器相关函数
'''

commands = {  # 命令解析器
    'startBaidu': start_Baidu,
    'shutdownBaidu': shutdown_Baidu,
    'startQA': start_all,
    'shutdownQA': shutdown_all,
    'manage': open_manager,
    'closeManage': close_manager
}

'''
问答模块，集合了
    添加问题
    修改问题
    会话管理
    删除问题
    问答功能
（注：这部分代码十分恶心，请谨慎阅读，之后会重构）
'''


@bcc.receiver("GroupMessage")
async def help_in_group(commandApp: GraiaMiraiApplication, message: GroupMessage, group: Group):
    if parser(message, "~help"):
        await app.sendGroupMessage(group=group, message=message.messageChain.create([
            Plain(
'''--------FAQ相关指令--------
~command相关：
startBaidu 二级命令 开启本群百科检索
shutdownBaidu 二级命令 关闭本群百科检索
startQA 二级命令 开启本群检索相关功能
shutdownQA 二级命令 关闭本群检索相关功能
----------------
检索功能相关：
百度 检索百度百科 例(百度 awsl)
萌娘 检索萌娘百科 例(萌娘 awsl)
sx 缩写词检索 例(sx awsl)
----------------
问答功能相关：
列表 查看已添加的问题
添加问题 添加一个问题
修改问题 修改一个问题
删除问题 删除一个问题''')
        ]))
        pass

    pass


@bcc.receiver("GroupMessage")
async def close_in_group(commandApp: GraiaMiraiApplication, message: GroupMessage, group: Group):
    if parser(message, "~command "):
        if not is_manager(message):
            return
        command = message.messageChain.get(Plain)[0].text.replace('~command ', '')
        send_msg = f"未知的指令{command},目前可执行指令：\n"
        if commands.get(command):
            flag: bool = commands[command](message, group)
            SaveConfig()
            if flag is None:
                return
            if flag:
                send_msg = f"已执行命令{command}"
            else:
                send_msg = f"此群尚不具备{command}指令的条件！"
        else:
            for i in commands.keys():
                send_msg += f"{i}"
        await commandApp.sendGroupMessage(group, message.messageChain.create(
            [Plain(send_msg)]
        ))


async def indexes(message: GroupMessage, group: Group):
    id: str = message.messageChain.get(Plain)[0].text.strip().replace('#', '')
    if id.isdigit():
        temp_list: list = quick_find_question_list[group.id]
        question: str = temp_list[int(id)]
        answer: Msg = search(question, group)
        send_msg = answer.get_msg_graia(message.messageChain)
        await app.sendGroupMessage(group, send_msg)


async def FQA(message: GroupMessage, group: Group) -> bool:
    if not message.messageChain.has(Plain):
        return False
    msg = Msg(message)
    msg_chain = message.messageChain
    # 首先对消息进行问答解析
    Question = msg.txt.strip()
    if Question == '列表':
        await app.sendGroupMessage(group, FQA_list(message, group))
        del msg
        return True
    at = msg_chain.get(At)[0].target if msg_chain.has(At) else 0
    tempQ = search(Question, group)
    if tempQ is not None:
        send_msg = tempQ.get_msg_graia(msg_chain)
    else:
        if at == BOTQQ:
            send_msg = msg_chain.create([
                Plain("没有找到这个问题，请等待学长学姐来回答或回复“列表”查看已有问题")
            ])
        else:
            send_msg = None
    if send_msg is not None:
        await app.sendGroupMessage(group, send_msg)
        del msg
        return True
    del msg
    return False


@bcc.receiver("GroupMessage")
async def BaiDu(message: GroupMessage, group: Group):
    if only_group_in_list(group, shutdown_all_group) \
            or not only_group_in_list(group, start_baiDu_group): return
    if parser(message, "百度 "):
        entry = message.messageChain.get(Plain)[0].text.strip().replace("百度 ", "")
        await app.sendGroupMessage(group=group, message=message.messageChain.create([
            Plain(getBaiduKnowledge(entry))
        ]))
    elif parser(message, "萌娘 "):
        entry = message.messageChain.get(Plain)[0].text.strip().replace("萌娘 ", "")
        await app.sendGroupMessage(group=group, message=message.messageChain.create([
            Plain(getACGKnowledge(entry))
        ]))


'''
缩写短语查询
'''


@bcc.receiver("GroupMessage")
async def Guess(message: GroupMessage, group: Group):
    if parser(message, "sx "):
        entry = message.messageChain.get(Plain)[0].text.strip().replace("sx ", "")
        await app.sendGroupMessage(group=group, message=message.messageChain.create([
            Plain(getGuess(entry))
        ]))
    pass


@bcc.receiver("GroupMessage")
async def group_message_handler(message: GroupMessage, group: Group):
    if group_is_in_list(message, group, shutdown_all_group):
        return
    if parser(message, "百度 ") \
            or parser(message, "萌娘 "):
        return
    msg = Msg(message)
    question = message.messageChain.get(Plain)[0].text if message.messageChain.has(Plain) else None
    has_session = temp_talk.get(msg.user_id)
    if has_session is not None:
        await session_manager(message, group)
        return
    if await FQA(message, group):
        return

    if parser(message, '#'):
        await indexes(message, group)
        return
    if group.id in mast_manager_group:
        if not is_manager(message):
            return
    if parser(message, "添加问题 "):
        # 创建添加问题的新会话
        question = question.replace("添加问题 ", "").strip()
        if has_session is None:
            add_temp_talk(msg.user_id, 'Add', True, question)
            sendMsg = await AddQA(message, group)
            if sendMsg is not None:
                await app.sendGroupMessage(group, sendMsg)
        del msg
        return

    if parser(message, "修改问题 "):
        # 创建修改问题的新会话
        question = question.replace("修改问题", "").strip()
        question = question if not re.search("#", question) \
            else quick_find_question_list[group.id][int(question.replace('#', ''))]
        if has_session is None:
            add_temp_talk(msg.user_id, 'Change', True, question)
            sendMsg = await change(group=group, GM=message)
            if sendMsg is not None:
                await app.sendGroupMessage(group, sendMsg)
        del msg
        return

    if parser(message, "删除问题 "):
        # 删除问题
        question = question.replace("删除问题", "").strip()
        question = question if not re.search("#", question) \
            else quick_find_question_list[group.id][int(question.replace('#', ''))]
        isdeleteOK: str = f"删除问题{question}成功" if deleteQA(question, group) else "不存在这个问题"
        await app.sendGroupMessage(group, message.messageChain.create([
            Plain(isdeleteOK)
        ]))
        await saveQA()
        del msg
        gc.collect()
        return


def apscheduler(*args, **kwargs):
    def decorator(func):
        @functools.wraps(func)
        def wrapper():
            scheduler = BlockingScheduler()
            scheduler.add_job(func, args[0],
                              hours=kwargs['hour'])
            scheduler.start()
            return func(args=args, kwargs=kwargs)

        return wrapper

    return decorator


@apscheduler('interval', hour=1)
def restart():
    print("程序重新开始")
    python = sys.executable
    os.execl(python, python, *sys.argv)


@bcc.receiver("FriendMessage")
async def restart_manager(message: FriendMessage, friend: Friend):
    if friend.id in Manager and message.messageChain.asDisplay().startswith("重启"):
        restart()


if __name__ == '__main__':
    # 初始化GroupQA
    # loop.run_until_complete(Compatible_old_index())
    nest_asyncio.apply()
    threading.Thread(target=restart, args=()).start()

    loop.run_until_complete(ReadConfig())
    loop.run_until_complete(ReadQA())
    loop.run_until_complete(read_love())
    app.launch_blocking()
