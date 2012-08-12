#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pyh import *
import ConfigParser, time
import re
#import logging
import paramiko

__author__ = 'Kong Luo Xing, konglx@ffcs.cn jayklx@gmail.com'
__version__ = 'v0.9 alpha version'
__config__ = 'ta_config.ini'
__now__ = time.strftime('%Y%m%d_%H%M%S', time.localtime())
__time__ = time.strftime('%Y-%m-%d %X', time.localtime())
#__path__ = os.path.abspath(os.path.dirname(__file__))

class SSH(object):
    def __init__(self):
        '''从ta_config.ini载入配置'''
        config = ConfigParser.ConfigParser()
        config.read(__config__)
        self.IPADDR = config.get('os', 'ipaddr')
        self.PORT = config.getint('os', 'port')
        self.USERNAME = config.get('os', 'username')
        self.PASSWORD = config.get('os', 'password')
        self.DBIPADDR = config.get('db', 'dbipaddr')
        self.DBPORT = config.get('db', 'dbport')
        self.DBPASSWORD = config.get('db', 'dbpassword')
        self.EXTRA_ARGS = config.get('db', 'extra_args')
    def check_rpm(self, rpm_name, ssh):
        rpms = ssh.ssh_exec('rpm -qa')
#        print rpms
        for pkgs in rpms:
            if rpm_name in pkgs[0]:
                return True
        else:
            print u'未安装' + rpm_name + u'包，请安装后重试'
            return False
    def ssh_init(self):
        '''初始化ssh连接'''
        self.ssh =  paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.IPADDR, self.PORT, self.USERNAME, self.PASSWORD)
    def ssh_exec(self, command, x=0, y=0, info=''):
        '''执行命令'''
        try:
            stdin, stdout, stderr = self.ssh.exec_command(command)
        except Exception:
            print '警告：' + command + '命令未能成功执行，报表可能不完整'
#        print stdout.readlines()
#        stdout.insert(0, command)
#        if stderr:
#            print stderr
        out = self.parse_output(stdout, x, y)
        print u'正在处理' + command
        out.insert(0, command)
        if info:
            out.insert(1, info)
        return out
    def parse_output(self, output, x = 0, y = 0):
        '''转换命令输出为2层列表

        x表示要删除的行数，y表示要删除的列数(从第一行/列开始)'''
        list = []
        for lines in output:
            list.append(lines.split())
        #删除不需要元素
        if x > 0:
            for i in range(x):
                del list[0]
        if y > 0:
            for i in range(y):
                for item in list:
                    del item[0]
        return list
#init ssh
ssh = SSH()
ssh.ssh_init()
#检测必要软件包是否存在
ssh.check_rpm('dmidecode', ssh)
ssh.check_rpm('sysstat', ssh)
class OsInfo(object):
    def __init__(self):
        s = ssh.ssh_exec('uname')
        self.os_type = s[1][0].rstrip()
#        self.basic_func()
#        print os_type
        chooseOS = {'Linux':lambda:self.linux_func(),
                    'AIX':lambda:self.aix_func(),
                    'HP-UX':lambda:self.hp_func(),
                    'Solaris':lambda:self.sol_func()}
        chooseOS[self.os_type]()
    def basic_func(self):
        hostname = ssh.ssh_exec('hostname')[1][0].rstrip()
        ipaddr = ssh.ssh_exec("/sbin/ifconfig eth0|grep 'inet addr:'|awk '{print $2}'")[1][0][5:].rstrip()
        arch = ssh.ssh_exec('uname -m')[1][0].rstrip()
        manufacturer = ssh.ssh_exec('/usr/sbin/dmidecode | grep Manufacturer | head -n 1')[1][1].rstrip()
        self.basic_list = ['', '', ['主机名', 'IP 地址', '操作系统', 'CPU架构', '快照时间', '厂商', '序列号'],
                      [hostname, ipaddr,self.os_type, arch, __time__, manufacturer]]

    def linux_func(self):
        self.basic_func()
        #系统版本信息
        sys_ver = ssh.ssh_exec('cat /etc/redhat-release')
        p = re.compile('\d')
        sys_ver = p.findall(''.join(str(n) for n in sys_ver))
        sys_ver = '.'.join(str(n) for n in sys_ver)
#        print sys_ver
        kernel = ssh.ssh_exec('uname -r')
        kernel = kernel[1][0]
        gcc = ssh.ssh_exec('/usr/bin/gcc --version', info = 'GCC')[2][2]
        version = ['', '', ['系统版本', '内核版本', 'GCC版本'],[sys_ver, kernel, gcc]]
        #java 版本号获取不到
#        java = ssh.ssh_exec('/usr/java/default/bin/java -version', info = 'Java')
#        print java
        #获取cpu信息
        def cpu_func(matches):
            cpuinfo = ssh.ssh_exec("grep '" +  matches + "' /proc/cpuinfo | tail -n 1")[1]
#            print cpuinfo
            cpuinfo = cpuinfo[len(cpuinfo)-1:]
            return cpuinfo[0]
#        print self.basic_list

        cpu_manuf = cpu_func('vendor_id')
        cpu_bit = ssh.ssh_exec('getconf LONG_BIT')[1][0].rstrip()
        cpu_model_t = ssh.ssh_exec("grep 'model' /proc/cpuinfo | tail -n 1")[1]
        cpu_model = cpu_model_t[6]+(cpu_model_t[7])
        cpu_cores = cpu_func('cores')
        cpu_frq = cpu_func('model')
        cpu_count = cpu_func('processor')
        cpu_list = ['cat /proc/cpuinfo', 'CPU信息',
                    ['制造商', 'BIT', '型号', 'CPU个数', '每CPU核心数', '频率'],
                    [cpu_manuf, cpu_bit, cpu_model, int(cpu_count)+1, cpu_cores, cpu_frq]]
        mpstat = ssh.ssh_exec('mpstat 2 5', x=2, y=2, info='总CPU使用率')
        mpstat[8].insert(0, 'Average')
#        print cpu_list
        #获取内存信息
        meminfo = ssh.ssh_exec('cat /proc/meminfo')
        memlist = ['cat /proc/meminfo', '内存信息(单位Byte)',
                   ['总内存', '剩余内存', 'Buffers', 'Cached', '总swap', '剩余swap'],
                   [meminfo[1][1], meminfo[2][1], meminfo[3][1], meminfo[4][1], meminfo[12][1], meminfo[13][1]]]
#        print memlist
        pvlist = ssh.ssh_exec('pvs', info='物理卷')
        vglist = ssh.ssh_exec('vgs', info='卷组')
        lvlist = ssh.ssh_exec('lvs', info='逻辑卷')
        del lvlist[2][4:]
        dflist = ssh.ssh_exec('df -h', info='文件系统信息')
        del dflist[2][6]
        dflist[2][5]='Mounted on'
        #美化df输出
        next = None
        for index, line in enumerate(dflist):
#            print line
            if len(line) == 1:
                next = dflist[index + 1]
                next.insert(0, line[0])
                dflist.remove(line)

        router = ssh.ssh_exec('netstat -rn', x=1, info='内核路由表')
        net_pkg = ssh.ssh_exec('netstat -in', x=1, info='网卡工作状态')
        ipnet = ssh.ssh_exec('ifconfig | grep -A 1 eth | grep inet', y=1, info='IP/掩码')
        ipnet.insert(2,['IP地址', '广播地址', '子网掩码'])

        iostat = ssh.ssh_exec('iostat', x=5, info='I/O状态')
        vmstat = ssh.ssh_exec('vmstat 2 5', 1, 0, 'vmstat输出')
        top = ssh.ssh_exec('top -bn 1 | head -n 17', 6, 0, info = 'CPU TOP 10 进程')
        mem_top = ssh.ssh_exec("top -bn 1 | sed '1,7 d' | sort -rn -k10 -k6 | head -n 10", info = 'MEM TOP 10进程')
        mem_top.insert(2, top[2])
        sysctl = ssh.ssh_exec("sysctl -p | sed 's/=//g'", info = '非默认内核参数')
        sysctl.insert(2, ['参数', '值'])
        startups = ssh.ssh_exec('chkconfig --list', info = '启动服务列表')
        startups.insert(2, ['程序名', 'init 0', 'init 1', 'init 2', 'init 3', 'init 4', 'init 5', 'init 6'])
        #以此结构组织输出格式
        appendlist = [['基本信息'],
                      self.basic_list,
                      ['版本信息'],
                      version,
                      ['CPU/内存'],
                      cpu_list, mpstat, memlist,
                      ['存储信息'],
                      pvlist, vglist, lvlist, dflist,
                      ['网络信息'],
                      ipnet, router, net_pkg,
                      ['系统状态'],
                      iostat, vmstat, top, mem_top, sysctl, startups
                     ]

        self.outlist = []
        outlist = self.outlist
        for item in appendlist:
            outlist.append(item)
    def aix_func(self):
        basic_func()
    def hp_func(self):
        basic_func()
    def sol_func(self):
        basic_func()
def get_db_info(self):
    pass

info = OsInfo()

def gen_table(com_out_list):
    '''生成表格

    参数为命令输出解析完的list'''
    rpt_table = p() << table(width='500', border='1')
    def thb(args):
        return th(args, cl='awrbg')
    def tdc(args):
        return td(args, cl='awrc', align='left')
    def tdnc(args):
        return td(args, cl='awrnc', align='left')
    rpt_table = rpt_table
    tro = tr()
    table_head = com_out_list[2]
    for item in table_head:
       tro  << thb(item)
    rpt_table << tro
    tro = tr()
    table_data = com_out_list[3:]
    c_or_nc = True
    for line in table_data:
        if c_or_nc:
            for item in line:
                tro << tdnc(item)
            c_or_nc = False
        else:
            for item in line:
                tro << tdc(item)
            c_or_nc = True
        tro << tr()
    rpt_table << tro
    return rpt_table
def gen_html():
    '''生成html'''
    print u'正在生成html报表'
    try:
        #读取模板文件,写入新文件
#        template = open(os.path.abspath(os.path.dirname(__file__)) + '/template/rpt_template.html')
        template = open('template/rpt_template.html')
    except Exception:
        print u'读取模板文件失败，请检查文件是否存在，以及是否有读写权限'
    rpt_file = open('reports/ta_report_' + __now__ + '.html', 'a')
#    rpt_file.write(template.read())
#    rpt_file = open(__path__ + '/reports/ta_report_' + __now__ + '.html', 'rw+')
#    report = PyH(template.readlines())
    report = PyH('TA report for ' + info.basic_list[3][0] + ' at ' + __time__)
    report << h1('TA report for ' + info.basic_list[3][0] + ' at ' + __time__, cl='awr')
    report.head << template.read()
#    report << h1('基本信息', cl='awr')
#    report << gen_table(info.basic_list)
    liawr = li(cl='awr')
    for line in info.outlist:
        if len(line) == 1:
            report << br()
            report << h2(line[0], cl='awr')
            report << a('回到顶部', cl='awr', href='#TOP')
        else:
            report << p(line[1], cl='awr')
            if line[0]:
                report << liawr << a(line[0],
                                     href='http://man.he.net/?topic='+line[0].split()[0]+'&section=all')
                liawr = li(cl='awr')
            report << br()
            report << gen_table(line)
    report << a('回到顶部', cl='awr', href='#TOP')
    #写入文件
    rpt_file.writelines(report.render())
    rpt_file.flush()
    rpt_file.close()
    print u'报表生成完成：' + 'reports/ta_report_' + __now__ + '.html'
#    print soup.html.head.title
#    table_head =
gen_html()
