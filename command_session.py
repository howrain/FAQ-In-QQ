from graia.application import Group, GroupMessage
from init_bot import *


def is_manager(message: GroupMessage) -> bool:
    if message.sender.permission == "MEMBER" or message.sender.id in Manager:
        return True
    return False


def group_is_in_list(message: GroupMessage, group: Group, start_group: list)->bool:
    if is_manager(message) and group.id in start_group:
        return True
    return False


def shutdown_Baidu(message: GroupMessage, group: Group) -> bool:
    if group_is_in_list(message, group, start_baiDu_group):
        start_baiDu_group.remove(group.id)
        return True
    return False


def shutdown_all(message: GroupMessage, group: Group) -> bool:
    if not group_is_in_list(message, group, shutdown_all_group):
        shutdown_all_group.append(group.id)
        return True
    return False


def start_Baidu(message: GroupMessage, group: Group) -> bool:
    if not group_is_in_list(message, group, start_baiDu_group):
        start_baiDu_group.append(group.id)
        return True
    return False


def start_all(message: GroupMessage, group: Group) -> bool:
    if group_is_in_list(message, group, shutdown_all_group):
        shutdown_all_group.remove(group.id)
        return True
    return False