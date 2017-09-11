#!/usr/bin/python
# -*- coding: UTF-8 -*-

import urllib2
import json
import os
from os import path
from os import system
import logging

FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger()


eurekaUrl = 'http://url/to/your/eureka/'
eurekaAuth = 'Basic base64-encoded-user-and-pass'

#The appId in eureka
appId = 'your-app-id-in-eureka'

#The nginx conf folder, must end with '/'
confPath = '/etc/nginx/conf.d/'

def getEurekaData(appId):
    req = urllib2.Request(eurekaUrl + 'apps/' + appId + '/');
    req.add_header('Authorization', eurekaAuth);
    req.add_header('Accept', 'application/json;charset=UTF-8');

    rep = urllib2.urlopen(req);
    jsonstr = rep.read();
    result = json.loads(jsonstr);
    appUrls =  [(ins["ipAddr"] + ':' + str(ins["port"]["$"])) for ins in result["application"]["instance"]]
    return appUrls;

def checkChange(appId, hosts):
    changed = True
    hostCopy = [x for x in hosts]
    hostCopy.sort()
    onelineStr = "\n".join(hostCopy);
    lastfilePath = 'last-'+ appId +'.txt'

    if path.exists(lastfilePath):
        lastfile = open(lastfilePath)
        lastContent = lastfile.read()
        lastfile.close()
        changed = onelineStr != lastContent
    return changed

def persistLastData(appId, hosts):
    hostCopy = [x for x in hosts]
    hostCopy.sort()
    onelineStr = "\n".join(hostCopy);
    lastfilePath = 'last-'+ appId +'.txt'
    lastfile = open(lastfilePath, 'w')
    lastfile.write(onelineStr)
    lastfile.close()

def tryUpdateNgConf(appId, hosts):
    #create a conf file containing upstream direction in current dir
    confName = 'upstream-' + appId + '.conf'
    conffile = open(confName, 'w')
    conffile.write('upstream ' + appId + ' {\n')
    for appUrl in hosts:
        conffile.write('    server ' + appUrl + ';\n');
    conffile.write('\n    keepalive 32;\n}')
    conffile.close();
    
    #if exists old conf file, mv it as bak file
    import shutil
    existsOldConf = False
    if path.exists(confPath + confName):
        existsOldConf = True
        shutil.move(confPath + confName, confPath + confName + '.bak')
    shutil.copy(confName, confPath + confName)

    canReload = system('nginx -t') == 0;

    if canReload:
        ret = system('nginx -s reload')
        logger.debug('Nginx conf reloaded with exit code ' + str(ret) + '.')
    else:
        if existsOldConf:
            shutil.move(confPath + confName + '.bak', confPath + confName)
        else:
            os.remove(confPath + confName)
    return canReload


def main():
    logger.info("Checking Eureka reg data for '" + appId + "'...")
    hosts = getEurekaData(appId)
    if checkChange(appId, hosts):
        logger.info("Eureka reg data for '" + appId + "' changed, trying to update nginx config...")
        if tryUpdateNgConf(appId, hosts):
            persistLastData(appId, hosts)
            logger.info("Nginx config file updated.")
        else:
            logger.warning("Nginx config file update failed, revert conf file changes.")
    else:
        logger.info("No change.")

main()
