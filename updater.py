from urllib import request
import json
import concurrent.futures
from threading import Lock
import json
import os
import os.path
import re
import zlib
import sys

class Updater():
    def __init__(self):
        self.index = set()
        self.quality = ("/img/", "/js/")
        self.force_update = False
        self.download_assets = False
        self.version = str(self.getGameVersion())
        if self.version == "None":
            print("Can't retrieve the game version")
            exit(0)
        
        self.manifestUri = "http://prd-game-a-granbluefantasy.akamaized.net/assets_en/{}/js/model/manifest/".format(self.version)
        self.cjsUri = "http://prd-game-a-granbluefantasy.akamaized.net/assets_en/{}/js/cjs/".format(self.version)
        self.imgUri = "http://prd-game-a-granbluefantasy.akamaized.net/assets_en/img"
        self.variations = [
            ("_01", "", "☆☆☆☆"),
            ("_01_f1", "_f1", "☆☆☆☆ II"),
            ("_02", "", "★★★★"),
            ("_02_f1", "_f1", "★★★★ II"),
            ("_03", "", "5★"),
            ("_03_f1", "_f1", "5★ II"),
            ("_04", "", "6★"),
            ("_04_f1", "_f1", "6★ II")
        ]
        self.patches = { # tuple: substitute id, extra string
            "3040232000": ('3040158000', ''), # s.alexiel,
            "3710019000": ('3040028000', ''), # zeta skin
            "3710020000": ('3040023000', ''), # lancelot skin
            "3710024000": ('3040023000', ''), # vira skin
            "3710025000": ('3040057000', ''), # vampy skin
            "3710026000": ('3040050000', ''), # percival skin
            "3710033000": ('3040040000', ''), # jannu skin
            "3710034000": ('3040013000', ''), # seruel skin
            "3710042000": ('3040009000', ''), # cog skin
            "3710043000": ('3040003000', '') # birdman skin
        }
        self.exclusion = ['3030114000']
        self.loadIndex()

    def req(self, url, headers={}):
        return request.urlopen(request.Request(url.replace('/img/', self.quality[0]).replace('/js/', self.quality[1]), headers=headers), timeout=50)

    def getGameVersion(self):
        vregex = re.compile("Game\.version = \"(\d+)\";")
        handler = self.req('https://game.granbluefantasy.jp/', headers={'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36", 'Accept-Language':'en', 'Accept-Encoding':'gzip, deflate', 'Host':'game.granbluefantasy.jp', 'Connection':'keep-alive'})
        try:
            res = zlib.decompress(handler.read(), 16+zlib.MAX_WBITS)
            handler.close()
            return int(vregex.findall(str(res))[0])
        except:
            return None

    def run(self):
        max_thread = 10
        print("Updating Database...")
        if self.force_update: print("Note: All characters will be updated")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_thread*4) as executor:
            futures = []
            err = [[0, True, Lock()], [0, True, Lock()], [0, True, Lock()], [0, True, Lock()]]
            for i in range(max_thread):
                futures.append(executor.submit(self.run_sub, i, max_thread, err[0], "3020{}000"))
                futures.append(executor.submit(self.run_sub, i, max_thread, err[1], "3030{}000"))
                futures.append(executor.submit(self.run_sub, i, max_thread, err[2], "3040{}000"))
                futures.append(executor.submit(self.run_sub, i, max_thread, err[3], "3710{}000"))
            for future in concurrent.futures.as_completed(futures):
                future.result()
        print("Done")
        self.loadIndex()
        self.saveIndex()

    def run_sub(self, start, step, err, file):
        id = start
        while err[1] and err[0] < 20:
            f = file.format(str(id).zfill(3))
            if self.force_update or id not in self.index:
                if not self.update(f):
                    with err[2]:
                        err[0] += 1
                        if err[0] >= 20:
                            err[1] = False
                            return
                else:
                    with err[2]:
                        err[0] = 0
            id += step

    def update(self, id):
        try:
            if not self.download_assets:
                try:
                    url_handle = self.req(self.imgUri + "/sp/assets/npc/m/" + id + "_01.jpg")
                    url_handle.read()
                    url_handle.close()
                except:
                    return False
            character_data = {}
            good_variations = {}
            good_phits = {}
            good_nsp = {}
            found = False
            for i in range(0, len(self.variations), 2):
                for j in range(2):
                    try:
                        fn = "npc_{}{}.js".format(id, self.variations[i+j][0])
                        url_handle = self.req(self.manifestUri + fn)
                        data = url_handle.read()
                        url_handle.close()
                        if self.download_assets:
                            with open("model/manifest/" + fn, "wb") as f:
                                f.write(data)
                        self.processManifest(fn, data.decode('utf-8'))
                        found = True
                        good_variations[self.variations[i+j]] = fn
                    except:
                        break
            if not found: return False
            for v in good_variations:
                for s in ["", "_s2", "_s3", "_0_s2", "_0_s3"]:
                    try:
                        fn = "nsp_{}{}{}.js".format(id, v[0], s)
                        url_handle = self.req(self.manifestUri + fn)
                        data = url_handle.read()
                        url_handle.close()
                        if self.download_assets:
                            with open("model/manifest/" + fn, "wb") as f:
                                f.write(data)
                        self.processManifest(fn, data.decode('utf-8'))
                        good_nsp[v] = fn
                        break
                    except:
                        pass
                try:
                    fn = "phit_{}{}.js".format(id, v[1])
                    url_handle = self.req(self.manifestUri + fn)
                    data = url_handle.read()
                    url_handle.close()
                    if self.download_assets:
                        with open("model/manifest/" + fn, "wb") as f:
                            f.write(data)
                    self.processManifest(fn, data.decode('utf-8'))
                    good_phits[v] = fn
                except:
                    pass
            character_data['0'] = {'length': len(good_variations.keys())}
            character_data['1'] = {} 
            character_data['2'] = {"1": {"1": ""},"2": {"1": ""}}
            keys = list(good_variations.keys())
            for i in range(len(keys)):
                character_data['0'][str(i)] = keys[i][2]
                character_data['1'][str(i)] = {}
                character_data['1'][str(i)]['cjs'] = [good_variations[keys[i]].replace('.js', '')]
                character_data['1'][str(i)]['action_label_list'] = ['ability', 'mortal_A', 'stbwait', 'short_attack', 'double', 'triple']
                if keys[i] in good_phits:
                    character_data['1'][str(i)]['effect'] = [good_phits[keys[i]].replace('.js', '')]
                else:
                    for j in range(i-1, -1, -1):
                        if keys[i][1] == keys[j][1] and good_variations[keys[j]] in good_phits:
                            character_data['1'][str(i)]['effect'] = [good_phits[keys[j]].replace('.js', '')]
                            break
                if 'effect' not in character_data['1'][str(i)]:
                    character_data['1'][str(i)]['effect'] = ['phit_ax_0001']
                if keys[i] in good_nsp:
                    character_data['1'][str(i)]['special'] = [{"random":0,"list":[{"target":"them","cjs":good_nsp[keys[i]].replace('.js', ''),"fixed_pos_owner_bg":0,"full_screen":0}]}]
                else:
                    for j in range(i-1, -1, -1):
                        if keys[j] in good_nsp:
                            character_data['1'][str(i)]['special'] = [{"random":0,"list":[{"target":"them","cjs":good_nsp[keys[j]].replace('.js', ''),"fixed_pos_owner_bg":0,"full_screen":1}]}]
                            break
                if 'special' not in character_data['1'][str(i)] and id in self.patches:
                    character_data['1'][str(i)]['special'] = [{"random":0,"list":[{"target":"them","cjs":good_variations[keys[j]].replace('.js', '').replace('npc', 'nsp').replace(id, self.patches[id][0]) + self.patches[id][1] ,"fixed_pos_owner_bg":0,"full_screen":1}]}]
                if '_s2' in character_data['1'][str(i)]['special'][0]['list'][0]['cjs'] or '_s3' in character_data['1'][str(i)]['special'][0]['list'][0]['cjs']: character_data['1'][str(i)]['special'][0]['list'][0]['full_screen'] = 1
                character_data['1'][str(i)]['cjs_pos'] = [{"y":0,"x":0}]
                character_data['1'][str(i)]['special_pos'] = [[{"y":0,"x":0}]]
            with open("json/" + str(id) + ".json", 'w') as outfile:
                json.dump(character_data, outfile)
            return True
        except Exception as e:
            print("Error", e, "for id", id)
            return False

    def processManifest(self, filename, manifest):
        if not self.download_assets:
            return
        st = manifest.find('manifest:') + len('manifest:')
        ed = manifest.find(']', st) + 1
        data = json.loads(manifest[st:ed].replace('Game.imgUri+', '').replace('src', '"src"').replace('type', '"type"').replace('id', '"id"'))
        for l in data:
            src = l['src'].split('?')[0]
            url_handle = self.req(self.imgUri + src)
            data = url_handle.read()
            url_handle.close()
        
            with open("img/sp/cjs/" + src.split('/')[-1], "wb") as f:
                f.write(data)

        url_handle = self.req(self.cjsUri + filename)
        data = url_handle.read()
        url_handle.close()
        with open("cjs/" + filename, "wb") as f:
            f.write(data)

    def retrieveAnimationlist(self, filename, cjs, animation_list):
        key = "mc_" + filename.split('.')[0] + "_"
        cur = cjs.find("mc_" + filename.split('.')[0] + "=function")
        if cur == -1: cur = 0
        while True:
            a = cjs.find(key, cur)
            if a == -1: break
            a += len(key)
            pos = [cjs.find('=', a), cjs.find('.', a), cjs.find(',', a)]
            i = 0
            while i < len(pos):
                if pos[i] == -1: pos.pop(i)
                else: i += 1
            if len(pos) == 0: break
            x = min(*pos)
            cur = x + 1
            if filename not in animation_list:
                animation_list[filename] = []
            if cjs[a:x] not in animation_list[filename]:
                animation_list[filename].append(cjs[a:x])
        # cleanup
        base = ['ab_motion', 'down', 'short_attack', 'triple', 'double', 'hide', 'mortal_A', 'chara_in', 'chara_out', 'dead', 'damage', 'win', 'ability', 'attack', 'stbwait', 'setup', 'wait']
        i = 0
        while i < len(animation_list[filename]):
            if animation_list[filename][i] in base: animation_list[filename].pop(i)
            else: i+= 1
        animation_list[filename].sort()
        animation_list[filename] = ['ability', 'mortal_A', 'stbwait', 'short_attack', 'double', 'triple'] + animation_list[filename]

    def manualUpdate(self, ids):
        print("Attempting to update", len(ids), "element(s)")
        max_thread = 40
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_thread) as executor:
            futures = []
            for id in ids:
                if len(id) == 10:
                    futures.append(executor.submit(self.update, id))
            for future in concurrent.futures.as_completed(futures):
                future.result()
        print("Done")
        self.loadIndex()
        self.saveIndex()

    def enemyUpdate(self):
        with open("view/cjs_npc_demo.js", mode="r", encoding="utf-8") as f:
            data = f.read()
            a = data.find('"enemy_') + len('"enemy_')
            enemy_id = data[a:data.find('"', a)]
            fn = "enemy_" + enemy_id + ".js"
            url_handle = self.req(self.manifestUri + "enemy_" + enemy_id + ".js")
            data = url_handle.read()
            url_handle.close()
            with open("model/manifest/" + fn, "wb") as f:
                f.write(data)
            self.processManifest(fn, data.decode('utf-8'))
            print("Enemy updated")

    def loadIndex(self):
        files = [f for f in os.listdir('json/') if os.path.isfile(os.path.join('json/', f))]
        known = []
        for f in files:
            if f.startswith("371") or f.startswith("304") or f.startswith("303") or f.startswith("302"):
                known.append(f.split('.')[0])
        self.index = set(known)

    def saveIndex(self):
        with open("json/index.json", 'w') as outfile:
            i = list(self.index)
            i.sort()
            i.reverse()
            json.dump(i, outfile)
        print("Index updated")

if __name__ == '__main__':
    u = Updater()
    if '-force' in sys.argv:
        u.force_update = True
    if '-download' in sys.argv:
        u.download_assets = True
    if '-enemy' in sys.argv:
        u.enemyUpdate()
        u.run()
    elif '-index' in sys.argv:
        u.loadIndex()
        u.saveIndex()
    elif len(sys.argv) >= 2 and sys.argv[1] == '-update':
        if len(sys.argv) == 2:
            print("Add IDs to update after '-update'")
            print("Example 'updater.py -update 3040000000 3040001000'")
        else:
            u.manualUpdate(sys.argv[2:])
    else:
        u.run()