## CA1.0安装要求：
系统：Ubuntu16.04
RPKI-CA：1.0

## RPKI-CA 1.0安装步骤：
### 1.安装
1. sudo apt-get update
2. sudo apt-get dist-upgrade	# 将软件包升级到最新版本
3. sudo wget -q -O /etc/apt/trusted.gpg.d/rpki.gpg https://download.rpki.net/APTng/apt-gpg-key.gpg
4. sudo wget -q -O /etc/apt/sources.list.d/rpki.list https://download.rpki.net/APTng/rpki.xenial.list
5. sudo apt-get update
6. sudo apt-get install rpki-ca
执行完这一步之后，rpki相关的守护进程须是启动的状态（通过ps aux|grep rpki)如果没有rpki守护进程运行说明前面的安装过程没有执行成功，需要重新执行上述步骤。
例如如下结果：
```bash
$ ps aux|grep rpki
rpki       382  0.0  0.5 303744  5708 ?        Sl   08:50   0:00 (wsgi:rpkigui)    -k start
rpki       565  0.0  0.8  45124  8768 ?        Ss   08:51   0:00 /usr/bin/python /usr/lib/rpki/rpki-nanny
rpki       566  0.0  0.7  45124  7408 ?        S    08:51   0:00 /usr/bin/python /usr/lib/rpki/rpki-nanny
rpki       567  0.8  4.0 224716 40408 ?        S    08:51   0:00 /usr/bin/python /usr/lib/rpki/irdbd --foreground
rpki       568  0.8  4.0 224468 40488 ?        S    08:51   0:00 /usr/bin/python /usr/lib/rpki/rpkid --foreground
rpki       569  0.7  3.6 208784 36872 ?        S    08:51   0:00 /usr/bin/python /usr/lib/rpki/pubd --foreground
postgres   605  0.0  1.4 301908 14988 ?        Ss   08:51   0:00 postgres: rpki rpki [local] idle
```

### 2.配置
1. vim /etc/rpki.conf
将handle字段修改为需要的值（如IANA,APNIC,CNNIC等）
2. 需要root权限 
```bash
# cat > /etc/rsyncd.conf << EOF
uid             = nobody
gid             = rpki

[rpki]
    use chroot          = no
    read only           = yes
    transfer logging    = yes
    path                = /usr/share/rpki/publication
    comment             = RPKI publication

# the following is only of you plan to run a root CA
[tal]
    use chroot          = no
    read only           = yes
    transfer logging    = yes
    path                = /usr/share/rpki/rrdp-publication
    comment             = MyCA TAL
EOF
```
3. 需要root权限
```bash
# cat > /etc/xinetd.d/rsync << EOF
service rsync
{
    disable         = no
    socket_type     = stream
    port            = 873
    protocol        = tcp
    wait            = no
    user            = root
    server          = /usr/bin/rsync
    server_args     = --daemon
    log_on_failure  += USERID
}
EOF
```
4. 需要root权限 systemctl restart xinetd
5. sudo systemctl restart rpki-ca
6. $ mkdir rpki_ca_data
7. $ sudo chown rpki rpki_ca_data/
8. $ cd rpki_ca_data/
#### iana节点配置
9. $ rpkic create_identity iana
10. $ sudo rsync ./iana.identity.xml /usr/share/rpki/publication/                     
11. $ rpkic -i iana configure_root
12. $ rpkic -i iana configure_publication_client iana.iana.repository-request.xml
13. $ rpkic -i iana configure_repository iana.repository-response.xml
14. $ rpkic -i iana force_publication
15. 此时通过下面的命令，应该能够看到iana（root节点）持有的资源，如果show不到资源可以等待10分钟左右，如果超过20分钟仍然show不到资源说明上述操作没有执行成功，需要重新执行
```bash
$ rpkic -i iana show_received_resources
Parent:      iana
  notBefore: 2017-05-24T15:41:39Z
  notAfter:  2018-05-24T21:30:25Z
  URI:       rsync://ubuntu/rpki/iana/CWyd0zsFZXp9ngqNC_aA9P5u5fc.cer
  SIA URI:   rsync://ubuntu/rpki/iana/
  AIA URI:   
  ASN:       0-4294967295
  IPv4:      0.0.0.0/0
  IPv6:      ::/0
```
#### apnic节点配置(及与iana节点的父子关系配置)
16. $ rpkic create_identity apnic
17. $ rpkic -i iana configure_child apnic.identity.xml
18. $ rpkic -i apnic configure_parent iana.apnic.parent-response.xml
19. $ rpkic -i iana configure_publication_client apnic.iana.repository-request.xml
20. $ rpkic -i apnic configure_repository apnic.repository-response.xml


### 3.资源分配
与0.6版本的操作完全一样（load_asns, load_prefixes, load_roa_requests），这里只以load_asns和load_prefixes为例
1. 
```bash
$ cat IANA2APNICASN.csv 
apnic   64497-64510
apnic   65537-65550 
```
2. 
```bash
$ cat IANA2APNICPREFIX.csv 
apnic   192.0.2.128/25
apnic   198.51.100.128/25
apnic   203.0.113.128/25
```
3. $ rpkic -i iana load_asns IANA2APNICASN.csv 
4. $ rpkic -i iana load_prefixes IANA2APNICPREFIX.csv 
5. $ rpkic -i iana show_child_resources
```bash
Child: apnic
  ASN: 64497-64510,65537-65550
 IPv4: 192.0.2.128/25,198.51.100.128/25,203.0.113.128/25
```

## Reference:
[QuickStart a DRLng Certificate Authority on Ubuntu Xenial](https://github.com/dragonresearch/rpki.net/blob/master/doc/quickstart/xenial-ca.md)
