#!/usr/bin/env python
# coding: utf8

import shutil
from collections import namedtuple
# DataLoader用于解析yaml/json/ini文件
from ansible.parsing.dataloader import DataLoader
# VariableManager用于分析ansible用到的变量
from ansible.vars.manager import VariableManager
# InventoryManager用于分析主机文件
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
# task_queue_manager管理任务队列
from ansible.executor.task_queue_manager import TaskQueueManager
import ansible.constants as C  # ansible的常量（不会变化的数据）

# since API is constructed for CLI it expects certain options to always be set, named tuple 'fakes' the args parsing options object
Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check', 'diff'])
# connection有三个选择local/ssh/smart
# local表示在本机执行，ssh表示通过ssh协议执行，smart表示自动选择
options = Options(connection='smart', module_path=['/to/mymodules'], forks=10, become=None, become_method=None, become_user=None, check=False, diff=False)

# initialize needed objects
loader = DataLoader()  # Takes care of finding and reading yaml, json and ini files
passwords = dict()  # 用于存储加密密码、远程连接密码等

# create inventory, use path to host config file as source or hosts in a comma separated string
# 声明被ansible管理的主机有哪些，可以把各主机用逗号分开形成字符串
# 也可以使用主机清单文件路径，将路径放到列表中
# inventory = InventoryManager(loader=loader, sources='localhost,')
inventory = InventoryManager(loader=loader, sources=['myansi/hosts'])

# variable manager takes care of merging all the different sources to give you a unifed view of variables available in each context
variable_manager = VariableManager(loader=loader, inventory=inventory)

# create datastructure that represents our play, including tasks, this is basically what our YAML loader does internally.
play_source = dict(
        name="Ansible Play",  # Play名称
        # hosts='localhost',  # 在哪些主机上执行命令
        hosts='webservers',  # 在哪些主机上执行命令
        gather_facts='no',  # 不收集主机信息
        tasks=[
            # 以下是执行的命令
            # dict(action=dict(module='shell', args='ls'), register='shell_out'),
            # dict(action=dict(module='debug', args=dict(msg='{{shell_out.stdout}}'))),
            # dict(action=dict(module='yum', args='name=httpd state=absent'), register='shell_out'),
            dict(action=dict(module='yum', args='name=httpd state=latest'), register='shell_out'),
            dict(action=dict(module='debug', args=dict(msg='{{shell_out}}')))
         ]
    )

# Create play object, playbook objects use .load instead of init or new methods,
# this will also automatically create the task objects from the info provided in play_source
play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

# Run it - instantiate task queue manager, which takes care of forking and setting up all objects to iterate over host list and tasks
tqm = None
try:
    tqm = TaskQueueManager(
              inventory=inventory,
              variable_manager=variable_manager,
              loader=loader,
              options=options,
              passwords=passwords,
          )
    result = tqm.run(play) # most interesting data for a play is actually sent to the callback's methods
finally:
    # we always need to cleanup child procs and the structres we use to communicate with them
    if tqm is not None:
        tqm.cleanup()

    # Remove ansible tmpdir
    shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)
