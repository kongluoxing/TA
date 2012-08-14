#!/usr/bin/env python
#coding:utf-8
from pyh import *
import types
import ConfigParser, time
import telnetlib
import re
#import logging
import paramiko

__author__ = 'Kong Luo Xing, konglx@ffcs.cn jayklx@gmail.com'
__version__ = 'v0.9 alpha version'
__config__ = 'ta_config.ini'
__now__ = time.strftime('%Y%m%d_%H%M%S', time.localtime())
__time__ = time.strftime('%Y-%m-%d %X', time.localtime())
#__path__ = os.path.abspath(os.path.dirname(__file__))


class Connect(object):
    def __init__(self):
        '''从ta_config.ini载入配置'''
        self.TELNET = False
        config = ConfigParser.ConfigParser()
        config.read(__config__)
        if config.get('os', 'telnet') == '1':
            self.TELNET = True
            self.PROMPT = config.get('os', 'prompt')
        self.IPADDR = config.get('os', 'ipaddr')
        self.PORT = config.getint('os', 'port')
        self.USERNAME = config.get('os', 'username')
        self.PASSWORD = config.get('os', 'password')
        self.DBIPADDR = config.get('db', 'dbipaddr')
        self.DBPORT = config.get('db', 'dbport')
        self.DBPASSWORD = config.get('db', 'dbpassword')
        self.EXTRA_ARGS = config.get('db', 'extra_args')
        self.conn = self.remote_init()
    def check_rpm(self, rpm_name):
        rpms = self.remote_exec('rpm -qa')
#        print rpms
        for pkgs in rpms:
            if rpm_name in pkgs[0]:
                return True
        else:
            print u'未安装' + rpm_name + u'包，请安装后重试'
            return False
    def telnet_init(self):
        enter_key = '\n'
        host = self.IPADDR
        port = self.PORT
        account = self.USERNAME
        password = self.PASSWORD
        tn = telnetlib.Telnet(host, port)
        tn.write(enter_key)
        ret = tn.read_until('login', 2)
        tn.write(account + enter_key)
        ret = tn.read_until('assword:', 2)
        tn.write(password + enter_key)
        tn.read_until(self.PROMPT)
        return tn
        #tn.write('ls\r\n')
        #ret = tn.read_very_eager()
        #print ret
        #tn.write('exit\r\n')
        #tn.close()
    def remote_init(self):
        '''初始化ssh连接

        返回telnet or ssh对象实例'''
        if self.TELNET:
            try:
                tn = self.telnet_init()
            except:
                print 'telnet connect false'
                exit(1)
            print 'telnet connect success'
            self.TELNET = True
            return tn
        else:
            ssh_client =  paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh_client.connect(self.IPADDR, self.PORT, self.USERNAME, self.PASSWORD)
                return ssh_client
            except:
                print 'ssh connect false, try telnet'
                try:
                    tn = self.telnet_init()
                except:
                    print 'telnet connect false'
                    exit(1)
                self.TELNET = True
                print 'connect success'
                return tn
    def remote_exec(self, command, x=0, y=0, info=''):
        '''执行命令

        conn: telnet or ssh对象实例'''
        conn = self.conn
        timeout = 2
        enter_key = '\n'
        if self.TELNET:
            self.conn.write(command + enter_key)
            response = conn.read_until(self.PROMPT)
            #输出第一行是命令，最后一行是prompt，要删掉
            #return response.splitlines()[:-1]
            tmp_out = response.splitlines()
            stdout = []
            if command in tmp_out[0]:
                del tmp_out[0]
            if '#' in tmp_out[-1]:
                del tmp_out[-1]
            for line in tmp_out:
                stdout.append([line])
            #conn.write(command + enter_key)
            #stdout = conn.read_very_eager()
        else:
            try:
                stdin, stdout, stderr = conn.exec_command(command)
            except Exception:
                print '警告：' + command + '命令未能成功执行，报表可能不完整'
#        print stdout.readlines()
#        stdout.insert(0, command)
#        if stderr:
#            print stderr
        #out: ['', '', [],[].....]
        out = self.parse_output(stdout, x, y)
        print u'正在处理' + command
        out.insert(0, command)
        if info:
            out.insert(1, info)
        return out
    def exec_single(self, command):
        '''针对只有一行输出的命令'''
        return self.remote_exec(command)[1][0].rstrip()
    def parse_output(self, output, x = 0, y = 0):
        '''转换命令输出为2维list

        x表示要删除的行数，y表示要删除的列数(从第一行/列开始)'''
        list = []
        for lines in output:
            list.append(lines)
#            if '#' in output[-1]:
#                output = output[:-1]
        #删除不需要元素
        if x > 0:
            for i in range(x):
                del list[0]
        if y > 0:
            for i in range(y):
                for item in list:
                    del item[0]
        return list
class OsInfo(object):
    def __init__(self, i_conn):
        self.i_conn = i_conn
    def choose(self):
        '''选择操作系统

        i_conn: Connect对象实例'''
        s = self.i_conn.remote_exec('uname')[1][0].lstrip()
        #self.os_type = s[1][0].rstrip()
        chooseOS = {'Linux':lambda:self.linux_func(),
                    'AIX':lambda:self.aix_func(),
                    'HP-UX':lambda:self.hp_func(),
                    'Solaris':lambda:self.sol_func()}
        #chooseOS[self.os_type]()
        chooseOS[s]()
    def basic_func(self):
        hostname = self.i_conn.remote_exec('hostname')[1][0].rstrip()
        ipaddr = self.i_conn.remote_exec("/sbin/ifconfig -a|grep 'inet addr:'|awk '{print $2}'")[1][0][5:].rstrip()
        arch = self.i_conn.remote_exec('uname -m')[1][0].rstrip()
        manufacturer = self.i_conn.remote_exec('/usr/sbin/dmidecode | grep Manufacturer | head -n 1')[1][1].rstrip()
        sn = self.i_conn.remote_exec("dmidecode | grep -i 'serial number' | head -n 1 | awk {'print $3'}")[1][0].rstrip()
        self.basic_list = ['', '', ['主机名', 'IP 地址', '操作系统', 'CPU架构', '快照时间', '厂商', '序列号'],
                      [hostname, ipaddr,self.os_type, arch, __time__, manufacturer, sn]]

    def linux_func(self):
        self.basic_func()
        #系统版本信息
        sys_ver = self.i_conn.remote_exec('cat /etc/redhat-release')
        p = re.compile('\d')
        sys_ver = p.findall(''.join(str(n) for n in sys_ver))
        sys_ver = '.'.join(str(n) for n in sys_ver)
#        print sys_ver
        kernel = self.i_conn.exec_single('uname -r')
        gcc = self.i_conn.remote_exec('/usr/bin/gcc --version', info = 'GCC')[2][2]
        version = ['', '', ['系统版本', '内核版本', 'GCC版本'],[sys_ver, kernel, gcc]]
        #java 版本号获取不到
#        java = conn.remote_exec('/usr/java/default/bin/java -version', info = 'Java')
#        print java
        #获取cpu信息
        def cpu_func(matches):
            cpuinfo = self.i_conn.remote_exec("grep '" +  matches + "' /proc/cpuinfo | tail -n 1")[1]
#            print cpuinfo
            cpuinfo = cpuinfo[len(cpuinfo)-1:]
            return cpuinfo[0]
#        print self.basic_list

        cpu_manuf = cpu_func('vendor_id')
        cpu_bit = self.i_conn.exec_single('getconf LONG_BIT')
        cpu_model_t = self.i_conn.remote_exec("grep 'model' /proc/cpuinfo | tail -n 1")[1]
        if cpu_model_t[7] == '@':
            cpu_model = cpu_model_t[6]
        else:
            cpu_model = cpu_model_t[6]+(cpu_model_t[7])
        cpu_cores = cpu_func('cores')
        cpu_frq = cpu_func('model')
        cpu_count = cpu_func('processor')
        cpu_list = ['cat /proc/cpuinfo', 'CPU信息',
                    ['制造商', 'BIT', '型号', 'CPU个数', '每CPU核心数', '频率'],
                    [cpu_manuf, cpu_bit, cpu_model, (int(cpu_count)+1)/int(cpu_cores), cpu_cores, cpu_frq]]
        mpstat = self.i_conn.remote_exec('mpstat 2 5', x=2, y=2, info='总CPU使用率')
        mpstat[8].insert(0, 'Average')
#        print cpu_list
        #获取内存信息
        meminfo = self.i_conn.remote_exec('cat /proc/meminfo')
        memlist = ['cat /proc/meminfo', '内存信息(单位KByte)',
                   ['总内存', '剩余内存', 'Buffers', 'Cached', '总swap', '剩余swap'],
                   [meminfo[1][1], meminfo[2][1], meminfo[3][1], meminfo[4][1], meminfo[12][1], meminfo[13][1]]]
#        print memlist
        pvlist = self.i_conn.remote_exec('pvs', info='物理卷')
        vglist = self.i_conn.remote_exec('vgs', info='卷组')
        lvlist = self.i_conn.remote_exec('lvs', info='逻辑卷')
        del lvlist[2][4:]
        dflist = self.i_conn.remote_exec('df -h', info='文件系统信息')
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

        router = self.i_conn.remote_exec('netstat -rn', x=1, info='内核路由表')
        net_pkg = self.i_conn.remote_exec('netstat -in', x=1, info='网卡工作状态')
        ipnet = self.i_conn.remote_exec('ifconfig | grep -A 1 eth | grep inet', y=1, info='IP/掩码')
        ipnet.insert(2,['IP地址', '广播地址', '子网掩码'])

        iostat = self.i_conn.remote_exec('iostat', x=5, info='I/O状态')
        vmstat = self.i_conn.remote_exec('vmstat 2 5', 1, 0, 'vmstat输出')
        top = self.i_conn.remote_exec('top -bn 1 | head -n 17', 6, 0, info = 'CPU TOP 10 进程')
        mem_top = self.i_conn.remote_exec("top -bn 1 | sed '1,7 d' | sort -rn -k10 -k6 | head -n 10", info = 'MEM TOP 10进程')
        mem_top.insert(2, top[2])
        sysctl = self.i_conn.remote_exec("sysctl -p | sed 's/=//g'", info = '非默认内核参数')
        sysctl.insert(2, ['参数', '值'])
        for index, item in enumerate(sysctl):
            if len(item) > 2 and type(item) is types.ListType:
                t = ' | '.join(str(n) for n in item[1:])
                item = item[:1]
                item.append(t)
                sysctl[index] = item
#                print item
        startups = self.i_conn.remote_exec('chkconfig --list', info = '启动服务列表')
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
        #basic_func()
        i_conn = self.i_conn
        hostname = i_conn.exec_single('hostname')
        ipaddr = i_conn.exec_single("ifconfig -a | grep inet | head -n 1 | awk '{print $2}'")
        arch = i_conn.exec_single('uname -m')
        #manufacturer = self.i_conn.remote_exec('/usr/sbin/dmidecode | grep Manufacturer | head -n 1')[1][1].rstrip()
        manufacturer = 'IBM'
        sn = i_conn.exec_single('uname -u')
        self.basic_list = ['', '', ['主机名', 'IP 地址', '操作系统', 'CPU架构', '快照时间', '厂商', '序列号'],
            [hostname, ipaddr,self.os_type, arch, __time__, manufacturer, sn]]
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
    def hp_func(self):
        basic_func()
    def sol_func(self):
        basic_func()
def get_db_info(self):
    pass

#info = OsInfo()

def gen_table(com_out_list):
    '''生成表格

    参数为命令输出解析完的list'''
    rpt_table = p() << table(width='500', border='1')
    def thb(args):
        return th(args, cl='awrbg', colspan='0')
    def tdc(args):
        return td(args, cl='awrc', align='left', colspan='0')
    def tdnc(args):
        return td(args, cl='awrnc', align='left', colspan='0')
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
        #TODO: tr标签闭合不正确
        tro << tr()
    rpt_table << tro
    return rpt_table
def gen_html(info):
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
            report << br()
        else:
            report << br()
            report << h3(line[1], cl='awr')

            if line[0]:
                report << br()
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
def main():
    connection = Connect()
    #connection.remote_init()
    #connection.check_rpm('dmidecode')
    #connection.check_rpm('sysstat')
    info = OsInfo(connection)
    info.choose()
    #gen_html(info)
if __name__ == '__main__':
    main()

