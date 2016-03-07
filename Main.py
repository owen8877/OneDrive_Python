#!/usr/bin/python
import json
import onedrive
import os

###############################################################################
# Load config files and settings
onedrive.loadconfig()
###############################################################################

###############################################################################
# Login or refresh the token
onedrive.login()
###############################################################################

###############################################################################
# Main loop
print("Hello", onedrive.config['info']['owner']['user']['displayName'])

command = {
    "cd": onedrive.cd,
    "dir": onedrive.cd,
    "l": onedrive.ls,
    "ls": onedrive.ls,
    "list": onedrive.ls,
    "dl": onedrive.dl,
    "download": onedrive.dl,
    "dlw": onedrive.dlw,
    "downloadfromweb": onedrive.dlw,
    "ul": onedrive.ul,
    "upload": onedrive.ul,
    "mkdir": onedrive.mkdir,
    "rm": onedrive.rm,
    "remove": onedrive.rm,
    "delete": onedrive.rm,
    "check": onedrive.check_dl,
    "exit": onedrive.leave
}

node = command["cd"](["root"])
while True:
    userinput = input(os.getcwd()+"|"+node["metadata"]["name"]+">")
    inputlist = userinput.split(' ')
    if inputlist[0] in command:
        node = command[inputlist[0]](inputlist[1:], node)
    else:
        print("Command", inputlist[0], "not found!")