import json
import os
import requests
import time
import webbrowser
from urllib.parse import urlparse
import urllib

from progressbar import *
from widgets import *
from compat import *


class itemNotFoundException(Exception):
    def __init__(self, value, local=False):
        self.name = value
        self.local = local

    def __str__(self):
        return self.name


class notFolderException(Exception):
    def __init__(self, value):
        self.name = value

    def __str__(self):
        return self.name


class notFileException(Exception):
    def __init__(self, did, name, downloadable=True):
        self.id = did
        self.name = name
        self.downloadable = downloadable

    def __str__(self):
        return self.name


class indexOutOfRangeException(Exception):
    def __init__(self, value):
        self.index = value

    def __str__(self):
        return str(self.index)


class syntaxErrorException(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "Syntax Error"


class downloadInfo(Exception):
    def __init__(self, did, name):
        self.id = did
        self.name = name

    def __str__(self):
        return self.id


class uploadDirInfo(Exception):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class nodeInfo(Exception):
    def __init__(self, did):
        self.id = did

    def __str__(self):
        return self.id


# config['info'] should look like
# {
#   'quota': {
#       'total': 16106127360,
#       'state': 'normal',
#       'remaining': 15200982666,
#       'used': 905144694,
#       'deleted': 377047
#   },
#   'owner': {
#       'user': {
#           'id': 'ea27fa95aad1d031',
#           'displayName': '陈Owen'
#       }
#   },
#   'id': 'ea27fa95aad1d031',
#   '@odata.context': 'https://api.onedrive.com/v1.0/$metadata#drives/$entity',
#   'driveType': 'personal'
# }
#
# config['token'] should look like
# {
#   "token_type":"bearer",
#   "expires_in": 3600,
#   "scope":"wl.basic onedrive.readwrite",
#   "access_token":"EwCo...AA==",
#   "refresh_token":"eyJh...9323"
# }

config = {
    'defaultdownloadpath': ".",
    'app': {
        'client_id': "000000004C185E10",
        'code': "M766296ef-6f3c-8a3b-9d26-f6f9e18b0f67",
        'client_secret': "T5hI3x4rDXD9J8ZCJahII6QVumOPR51X"
    },
    'token': {},
    'info': {}
}

dltask = []
proxyDict = {}

def onedrive_init():
    print("We need to acquire your authorization of the app.")
    print("Please input THE ENTIRE REDIRECT URL from the browser later after you sign in.")
    print("Press ENTER to jump to Microsoft OneDrive Auth page.")
    input()
    webbrowser.open_new("https://login.live.com/oauth20_authorize.srf?client_id="
                        + config['app']['client_id']
                        + "&scope=wl.signin%20wl.offline_access%20onedrive.readwrite"
                        + "&response_type=code"
                        + "&redirect_uri=https://login.live.com/oauth20_desktop.srf")
    code_url = input("Paste THE ENTIRE REDIRECT URL here : ")
    config['app']['code'] = urllib.parse.parse_qs(urlparse(code_url).query, True)['code']

    token_response = requests.post("https://login.live.com/oauth20_token.srf",
                  headers={"Content-Type": "application/x-www-form-urlencoded"},
                  data={
                      "client_id": config['app']['client_id'],
                      "redirect_uri": "https://login.live.com/oauth20_desktop.srf",
                      "client_secret": config['app']['client_secret'],
                      "code": config['app']['code'],
                      "grant_type": "authorization_code"
                  },
                  proxies=proxyDict)
    if token_response.status_code == 200:
        print("Login Successfully!!!")
        config['token'] = json.loads(token_response.text)
        config['token']['timestamp'] = time.mktime(time.gmtime())
        config['info'] = json.loads(get("/drive").text)
        cfgfile = open("onedrive.conf", mode='w')
        cfgfile.write(json.dumps(config))
        cfgfile.close()

        print("Before you freely browse your files, let's set up the configurations.")
        config['defaultdownloadpath'] = input("Your default download path :")

    else:
        print(token_response.status_code)
        print(token_response.headers)
        print(token_response.text)


def loadconfig():
    try:
        cfgfile = open("onedrive.conf", mode='r')
        proxyfile = open("proxy.conf", mode='r')
        global config, proxyDict
        config = json.loads(cfgfile.read())
        proxyDict = json.loads(proxyfile.read())
        cfgfile.close()
        proxyfile.close()

    except FileNotFoundError:
        onedrive_init()


def login():
    if 'timestamp' in config['token'] and time.mktime(time.gmtime()) - config['token']['timestamp'] < 50 * 60:
        return
    loginresponse = get("/drive")
    if loginresponse.status_code != 200:
        # print("Login failed! Status code :", loginresponse.status_code)
        refresh = purepost(
            "https://login.live.com/oauth20_token.srf",
            {
                'client_id': config['app']['client_id'],
                'redirect_uri': "https://login.live.com/oauth20_desktop.srf",
                'client_secret': config['app']['client_secret'],
                'refresh_token': config['token']['refresh_token'],
                'grant_type': "refresh_token"
            }
        )
        # print(refresh.text)
        config['token'] = json.loads(refresh.text)
        config['token']['timestamp'] = time.mktime(time.gmtime())
        config['info'] = json.loads(get("/drive").text)
        # print("Token refresh successfully!")
        cfgfile = open("onedrive.conf", mode='w')
        cfgfile.write(json.dumps(config))
        cfgfile.close()
    else:
        # print("Login successfully!")
        pass


def get(webpath, stream=False):
    return requests.get(
        "https://api.onedrive.com/v1.0" + webpath,
        headers={"Authorization": "bearer " + config['token']['access_token']},
        proxies=proxyDict,
        stream=stream
    )


def pureget(webpath, stream=False):
    return requests.get(
        webpath,
        headers={"Authorization": "bearer " + config['token']['access_token']},
        proxies=proxyDict,
        stream=stream
    )


def getjson(webpath):
    return json.loads(get(webpath).text)


def getnode(id):
    return {
        "metadata": getjson("/drive/items/"+id),
        "children": getjson("/drive/items/"+id+"?expand=children")["children"]
    }


def post(webpath, payload=None, headers=None):
    if headers is None:
        headers = {"Authorization": "bearer " + config['token']['access_token']}
    else:
        headers.update({"Authorization": "bearer " + config['token']['access_token']})
    return requests.post(
        "https://api.onedrive.com/v1.0"+webpath,
        headers=headers,
        data=payload,
        proxies=proxyDict
    )


def delete(webpath, payload=None, headers=None):
    if headers is None:
        headers = {"Authorization": "bearer " + config['token']['access_token']}
    else:
        headers.update({"Authorization": "bearer " + config['token']['access_token']})
    return requests.delete(
        "https://api.onedrive.com/v1.0"+webpath,
        headers=headers,
        data=payload,
        proxies=proxyDict
    )


def purepost(webpath, payload=None, headers=None):
    if headers is None:
        headers = {"Authorization": "bearer " + config['token']['access_token']}
    else:
        headers.update({"Authorization": "bearer " + config['token']['access_token']})
    return requests.post(
        webpath,
        headers=headers,
        data=payload,
        proxies=proxyDict
    )


def put(webpath, payload=None, headers=None):
    if headers is None:
        headers = {"Authorization": "bearer " + config['token']['access_token']}
    else:
        headers.update({"Authorization": "bearer " + config['token']['access_token']})
    # print("putting...","https://api.onedrive.com/v1.0" + webpath)
    return requests.put(
        "https://api.onedrive.com/v1.0" + webpath,
        headers=headers,
        data=payload,
        proxies=proxyDict
    )


def ls(params, node):
    try:
        if len(params) != 0:
            if params[0] == "-l":
                for item in os.listdir("."):
                    print(item)
            else:
                raise syntaxErrorException()
        else:
            i = 0
            if "parentReference" in node["metadata"]:
                print(i, "\t", "Folder\t", "..")
            for child in node["children"]:
                i += 1
                if 'file' in child:
                    print(i, "\t", "File\t", child['name'])
                elif 'folder' in child:
                    print(i, "\t", "Folder\t", child['name'])

    except syntaxErrorException:
        print("Usage: 'ls' or 'ls -l'")

    return node


def cd(params, node=None):
    if len(params) == 0:
        return node
    try:
        if params[0] == '-i':
            # use an index to indicate the directory
            index_str = params[1]
            if index_str.isnumeric():
                index = int(index_str)
                if index < 0 or index > len(node["children"]):
                    raise indexOutOfRangeException(index)
                elif index == 0:
                    if 'parentReference' not in node["metadata"]:
                        return node
                    else:
                        return getnode(node["metadata"]["parentReference"]["id"])
                else:
                    if "folder" in node["children"][index-1]:
                        return getnode(node["children"][index-1]["id"])
                    else:
                        raise notFolderException(node["children"][index-1]["name"])
            else:
                raise syntaxErrorException()
        if params[0] == '-l':
            # changes local dir
            dir_to_ch = " ".join([param for param in params[1:]])
            try:
                os.chdir(dir_to_ch)
            except FileNotFoundError as fnfe:
                print("No such directory:", dir_to_ch)
            except NotADirectoryError as nade:
                print("Not a directory:", dir_to_ch)
        else:
            directory = " ".join([param for param in params])
            if directory == "/" or directory == "root":
                return getnode("root")
            elif directory == ".":
                return getnode(node["metadata"]["id"])
            elif directory == "..":
                if 'parentReference' not in node["metadata"]:
                    return node
                else:
                    return getnode(node["metadata"]["parentReference"]["id"])
            else:
                for item in node["children"]:
                    if directory == item["name"] and "folder" in item:
                        return getnode(item["id"])
                else:
                    raise itemNotFoundException(directory)

    except notFolderException as nfe:
        print(nfe, "is not a directory")
    except itemNotFoundException as fnfe:
        print("Cannot find", fnfe)
    except indexOutOfRangeException as ioore:
        print("Index", ioore, "out of range")
    except nodeInfo as ni:
        return {
            "metadata": getjson(ni.id),
            "children": getjson(ni.id+"?expand=children")["children"]
        }
    except syntaxErrorException:
        print("Usage: 'cd [directory]' or 'cd -i [index]'")

    return node


def dlfile(fileid, filename, path=""):
    # Here we download the file
    if path == "":
        downloadpath = input("Save file to ( default '"+config['defaultdownloadpath']+"' ) : ")
        if (downloadpath == ""):
            downloadpath = config['defaultdownloadpath']
    else:
        downloadpath = path

    if not os.path.exists(downloadpath):
        # print(downloadpath, "doesn't exist")
        os.makedirs(downloadpath)
    if not os.path.isdir(downloadpath):
        print(downloadpath, "is not a directory")
        return
    if os.path.exists(downloadpath+"/"+filename):
        print("File", filename, "already exists in directory", downloadpath)
        return

    try:
        res = get("/drive/items/"+fileid+"/content", True)
        if res.status_code == 200:
            with open(downloadpath+"/"+filename, 'wb') as f:
                pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=int(res.headers['content-length'])).start()
                block = 1024
                length = - block
                for chunk in res.iter_content(block):
                    f.write(chunk)
                    length += block
                    pbar.update(length)
                f.close()
                pbar.finish()
        print("Saved file to", downloadpath+"/"+filename)
    except Exception:
        os.remove(downloadpath+"/"+filename)
        raise


def dlfolder(folderid, foldername, path=""):
    if path == "":
        defaultpath = "/home/xdroid"
        path = input("Save folder to ( default '"+defaultpath+"' ) : ")
        if (path == ""):
            path = defaultpath

    if not os.path.exists(path):
        # print(path, "doesn't exist")
        os.makedirs(path)
    if not os.path.isdir(path):
        print(path, "is not a directory")
        return

    for child in getnode(folderid)["children"]:
        if 'folder' in child:
            dlfolder(child["id"], child["name"], path+"/"+foldername)
        elif 'file' in child:
            dlfile(child["id"], child["name"], path+"/"+foldername)


def dl(params, node):
    try:
        if len(params) == 0:
            raise syntaxErrorException()
        if params[0] == '-i':
            # use an index to indicate the directory
            index_str = params[1]
            if index_str.isnumeric():
                index = int(index_str)
                if index < 0 or index > len(node["children"]):
                    raise indexOutOfRangeException(index)
                elif index == 0:
                    raise notFileException("", "..", False)
                else:
                    if "file" in node["children"][index-1]:
                        raise downloadInfo(node["children"][index-1]["id"], node["children"][index-1]["name"])
                    else:
                        raise notFileException(node["children"][index-1]["id"], node["children"][index-1]["name"])
            else:
                raise syntaxErrorException()
        elif params[0] == '-w':
            return dlw(params[1:], node)
        else:
            file = " ".join([param for param in params])
            if file == "/" or file == "root" or file == "..":
                raise notFileException("", file, False)
            else:
                for item in node["children"]:
                    if file == item["name"]:
                        if "file" in item:
                            raise downloadInfo(item["id"], item["name"])
                        else:
                            raise notFileException(item["id"], file)
                else:
                    raise itemNotFoundException(file)

    except notFileException as nfe:
        if not nfe.downloadable:
            print("Cannot download ", nfe.name)
            return node
        confirm = input("Do you want to download the whole folder '"+nfe.name+"' ? (y|n)")
        if confirm == "n":
            return node
        dlfolder(nfe.id, nfe.name)
    except itemNotFoundException as fnfe:
        print("Cannot find", fnfe)
    except indexOutOfRangeException as ioore:
        print("Index", ioore, "out of range")
    except syntaxErrorException:
        print("Usage: 'dl [file|folder]' or 'dl -i [index]' or 'dl -w [weburl]'")
    except downloadInfo as di:
        dlfile(di.id, di.name)

    return node


def dlw(params, node):
    try:
        if len(params) == 0:
            raise syntaxErrorException()
        weburl = " ".join([param for param in params])
        defaultfilename = weburl.split('/')[-1]
        filename = input("Filename ( default : "+defaultfilename+" ) : ");
        if filename == "":
            filename = defaultfilename
        r = post(
            "/drive/items/"+node["metadata"]["id"]+"/children",
            headers={
                "Content-Type": "application/json",
                "Prefer": "respond-async"
            },
            payload=json.dumps({
                "@content.sourceUrl": weburl,
                "name": filename,
                "file": {}
            })
        )
        dltask.append({
            "name": filename,
            "monitor": r.headers.get('Location'),
            "status": "notStarted",
            "progress": 0.0,
            "path": ""
        })
        if 'parentReference' not in node["metadata"]:
            dltask[-1]["path"] = "/" + filename
        else:
            dltask[-1]["path"] = node["metadata"]["parentReference"]["path"] + filename

    except syntaxErrorException:
        print("Usage: 'dlw [weburl]'")

    return node


def ulfile(file, node):
    # print(file, node["metadata"]["name"], os.getcwd())
    with open(os.getcwd()+"/"+file, "rb") as f:
        res = put("/drive/items/"+node["metadata"]["id"]+":/"+f.name.split("/")[-1]+":/content", payload=f)
        if res.status_code == 201:
            print("Upload", f.name, "successfully!")
        else:
            print("Failed!", res.status_code)
            print(res.headers)
            print(res.text)


def createFolder(folder, node, refresh=True):
    res = put("/drive/items/"+node["metadata"]["id"]+"/children/"+folder,
              payload='{"name": "'+folder+'", "folder": {}}',
              headers={"Content-Type": "application/json"})
    if res.status_code == 201:
        print("Folder", folder, "created successfully!")
        if refresh:
            return getnode(json.loads(res.text)["id"])
    else:
        print("Failed!", res.status_code)
        print(res.headers)
        print(res.text)


def ulfolder(folder, node, createself=False):
    if createself:
        for item in node["children"]:
            if folder == item["name"]:
                node = cd([folder], node)
                break
        else:
            node = createFolder(folder, node)
    os.chdir(folder)
    items = os.listdir(".")
    # print(folder, node["metadata"]["name"], os.getcwd())
    for item in items:
        if os.path.isdir(item):
            # Directory
            try:
                for child in node["children"]:
                    if item == child["name"]:
                        if "folder" in child:
                            # Good, lets upload the sub directory!
                            subnode = cd([item], node)
                            raise uploadDirInfo(item)
                        else:
                            print("Directory", item, "already exists as a file!")
                        break
                else:
                    # Create a folder at remote
                    subnode = createFolder(item, node)
                    raise uploadDirInfo(item)

            except uploadDirInfo as udf:
                print("okay")
                ulfolder(udf.name, subnode, False)
        else:
            # File
            ulfile(item, node)
    os.chdir("..")


def ul(params, node):
    try:
        if len(params) == 0:
            raise syntaxErrorException()
        item = " ".join([param for param in params])
        if not os.path.exists(item):
            raise itemNotFoundException(item)
        if os.path.isdir(item):
            confirm = input("Do you want to upload the whole folder '"+item+"' ? (y|n)")
            if confirm == "n":
                return node
            ulfolder(item, node, True)
        else:
            # item is a file
            ulfile(item, node)

    except syntaxErrorException:
        print("Usage: 'ul [file|folder]'")
    except itemNotFoundException as infe:
        print("Local file/folder", infe.name, "not found!")

    return cd(['.'], node)


def mkdir(params, node):
    try:
        if len(params) == 0:
            raise syntaxErrorException()
        folder = " ".join([param for param in params])
        createFolder(folder, node, False)

    except syntaxErrorException:
        print("Usage: 'mkdir [folder]'")

    return cd(["."], node)


def rm(params, node):
    try:
        if len(params) == 0:
            raise syntaxErrorException()
        if params[0] == "-l":
            item = " ".join([param for param in params[1:]])
            if not os.path.exists(item):
                raise itemNotFoundException(item, True)
            confirm = input("Do you want to remove '"+item+"' ? (y|n)")
            if confirm == "n":
                return node
            if os.path.isdir(item):
                confirm = input("Do you want to remove the whole folder '"+item+"' ? (y|n)")
                if confirm == "n":
                    return node
                os.removedirs(item)
                print("Removed", item)
            else:
                # item is a file
                os.remove(item)
                print("Removed", item)
        else:
            file = " ".join([param for param in params])

            confirm = input("Do you want to remove '"+file+"' ? (y|n)")
            if confirm == "n":
                return node

            for item in node["children"]:
                if file == item["name"]:
                    file_id = item["id"]
                    break
            else:
                raise itemNotFoundException(file)
            res = delete("/drive/items/"+file_id)
            if res.status_code == 204:
                print("Deleted", file)
            else:
                print("Failed!", res.status_code)
                print(res.headers)
                print(res.text)

    except syntaxErrorException:
        print("Usage: 'rm [file|folder]' or 'rm -l [file|folder]")
    except itemNotFoundException as infe:
        if infe.local:
            print("Local file/folder", infe.name, "doesn't exist!")
        else:
            print("Remote file/folder", infe.name, "doesn't exist!")

    return cd(["."], node)


def check_dl(params, node):
    for task in dltask:
        if task["status"] == "complete" or task["status"] == "failed":
            print(task["name"]+"\t"+task["status"]+"\t"+task["path"])
        else:
            r = pureget(task["monitor"])
            if r.status_code == 200:
                # Download complete
                task["status"] = "complete"
                task["progress"] = 100.0
                print(task["name"]+"\t"+task["status"]+"\t"+task["path"])
            elif r.status_code != 404:
                # Downloading...
                task["status"] = r.json()["status"]
                task["progress"] = r.json()["percentageComplete"]
                print(task["name"]+"\t"+task["status"]+"\t"+str(task["progress"])+"%\t"+task["path"])
            else:
                # Failed!
                task["status"] = "failed"
                task["progress"] = r.json()["percentageComplete"]
                print(task["name"]+"\t"+task["status"]+"\t"+task["path"])
    return node


def leave(params, node):
    print("Au revoir!")
    exit(0)