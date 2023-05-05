import httpx
import json
import concurrent.futures
from threading import Lock
import os
import os.path
import sys
import queue
from datetime import datetime, timezone

class Updater():
    def __init__(self):
        limits = httpx.Limits(max_keepalive_connections=100, max_connections=100, keepalive_expiry=10)
        self.client = httpx.Client(http2=True, limits=limits)
        self.running = False
        self.index = set()
        self.queue = queue.Queue()
        self.quality = ("/img/", "/js/")
        self.force_update = False
        self.download_assets = False
        self.debug_mode = False
        
        self.manifestUri = "https://prd-game-a-granbluefantasy.akamaized.net/assets_en/js/model/manifest/"
        self.cjsUri = "https://prd-game-a-granbluefantasy.akamaized.net/assets_en/js/cjs/"
        self.imgUri = "https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img"
        self.variations = [
            ("_01{}", "", "☆☆☆☆"),
            ("_01{}_f1", "_f1", "☆☆☆☆ II"),
            ("_02{}", "", "★★★★"),
            ("_02{}_f1", "_f1", "★★★★ II"),
            ("_03{}", "", "5★"),
            ("_03{}_f1", "_f1", "5★ II"),
            ("_04{}", "", "6★"),
            ("_04{}_f1", "_f1", "6★ II")
        ]
        self.possible_class = [
                "csr_sw_{}_01", # sword
                "gzk_kn_{}_01", # dagger
                "aps_sp_{}_01", # spear
                "bsk_ax_{}_01", # axe
                "wrk_wa_{}_01", # staff
                "rlc_gu_{}_01", # gun
                "rsr_me_{}_01", # melee
                "rbn_bw_{}_01", # bow
                "els_mc_{}_01", # harp
                "kng_kt_{}_01" # katana
            ]
        self.patches = { # tuple: substitute ougi id, extra string, substitute atk file
            "3020000000": ("", "", "phit_ax_0001"),
            "3020001000": ("", "", "phit_sw_0003"),
            "3020002000": ("", "", "phit_ax_0004"),
            "3020004000": ("", "", "phit_ax_0001"),
            "3020005000": ("", "", "phit_sp_0002"),
            "3020006000": ("", "", "phit_sw_0003"),
            "3020007000": ("", "", "phit_sw_0003"),
            "3020008000": ("", "", "phit_wa_0001"),
            "3020009000": ("", "", "phit_me_0004"),
            "3020010000": ("", "", "phit_sw_0006"),
            "3020011000": ("", "", "phit_wa_0004"),
            "3020012000": ("", "", "phit_sp_0003"),
            "3020013000": ("", "", "phit_kn_0003"),
            "3020014000": ("", "", "phit_gu_0002"),
            "3020015000": ("", "", "phit_kn_0006"),
            "3020016000": ("", "", "phit_gu_0001"),
            "3020017000": ("", "", "phit_kn_0006"),
            "3020018000": ("", "", "phit_sw_0005"),
            "3020019000": ("", "", "phit_sw_0004"),
            "3020020000": ("", "", "phit_me_0005"),
            "3020021000": ("", "", "phit_wa_0001"),
            "3020022000": ("", "", "phit_kn_0003"),
            "3020023000": ("", "", "phit_gu_0001"),
            "3020024000": ("", "", "phit_ax_0005"),
            "3020025000": ("", "", "phit_ax_0001"),
            "3020026000": ("", "", "phit_kn_0004"),
            "3020027000": ("", "", "phit_sw_0003"),
            "3020028000": ("", "", "phit_kn_0003"),
            "3020030000": ("", "", "phit_kn_0002"),
            "3020031000": ("", "", "phit_kn_0006"),
            "3020033000": ("", "", "phit_me_0003"),
            "3020034000": ("", "", "phit_gu_0001"),
            "3020036000": ("", "", "phit_gu_0001"),
            "3020037000": ("", "", "phit_me_0003"),
            "3020038000": ("", "", "phit_me_0001"),
            "3020039000": ("", "", "phit_wa_0005"),
            "3020040000": ("", "", "phit_sp_0002"),
            "3020041000": ("", "", "phit_kn_0006"),
            "3020045000": ("", "", "phit_kn_0004"),
            "3020046000": ("", "", "phit_ax_0001"),
            "3020048000": ("", "", "phit_sw_0002"),
            "3020049000": ("", "", "phit_bw_0001"),
            "3020050000": ("", "", "phit_0000000000"),
            "3020051000": ("", "", "phit_me_0003"),
            "3020052000": ("", "", "phit_me_0001_silent"),
            "3020053000": ("", "", "phit_sw_0002"),
            "3020054000": ("", "", "phit_kn_0005"),
            "3020056000": ("", "", "phit_sw_0004"),
            "3020057000": ("", "", "phit_sp_0001"),
            "3020058000": ("", "", "phit_sw_0003"),
            "3020059000": ("", "b", "phit_me_0004"),
            "3020060000": ("", "", "phit_me_0001"),
            "3020061000": ("", "", "phit_wa_0006"),
            "3020062000": ("", "", "phit_me_0002"),
            "3020063000": ("", "", "phit_kn_0001"),
            "3020064000": ("", "", "phit_sw_0003"),
            "3020070000": ("", "", "phit_me_0002"),
            "3030000000": ("", "", "phit_sp_0015"),
            "3030001000": ("", "", "phit_sw_0012"),
            "3030002000": ("", "", "phit_wa_0012"),
            "3030003000": ("", "", "phit_wa_0011"),
            "3030004000": ("", "", "phit_sw_0014"),
            "3030009000": ("", "", "phit_sw_0013"),
            "3030010000": ("", "", "phit_kn_0014"),
            "3030011000": ("", "", "phit_ax_0011"),
            "3030012000": ("", "", "phit_sw_0012"),
            "3030013000": ("", "", "phit_me_0013"),
            "3030014000": ("", "", "phit_sp_0012"),
            "3030015000": ("", "", "phit_me_0011"),
            "3030016000": ("", "", "phit_gu_0011"),
            "3030018000": ("", "", "phit_bw_0014"),
            "3030019000": ("", "", "phit_sw_0016"),
            "3030020000": ("", "", "phit_me_0013"),
            "3030024000": ("", "", "phit_bw_0014"),
            "3030026000": ("", "", "phit_mc_0014"),
            "3030027000": ("", "", "phit_kn_0011"),
            "3030028000": ("", "", "phit_sp_0012"),
            "3030029000": ("", "", "phit_sw_0012"),
            "3030030000": ("", "", "phit_gu_0011"),
            "3030031000": ("", "", "phit_sw_0014"),
            "3030032000": ("", "", "phit_3030101000"),
            "3030033000": ("", "", "phit_sw_0016"),
            "3030034000": ("", "", "phit_wa_0011"),
            "3030035000": ("", "", "phit_bw_0014"),
            "3030036000": ("", "", "phit_wa_0015"),
            "3030037000": ("", "", "phit_sw_0013"),
            "3030038000": ("", "", "phit_sw_0013"),
            "3030039000": ("", "", "phit_wa_0015"),
            "3030040000": ("", "", "phit_sw_0015"),
            "3030041000": ("", "", "phit_sw_0012"),
            "3030042000": ("", "", "phit_sw_0016"),
            "3030043000": ("", "", "phit_mc_0014"),
            "3030044000": ("", "", "phit_bw_0014"),
            "3030045000": ("", "", "phit_sp_0013"),
            "3030046000": ("", "", "phit_sw_0011"),
            "3030047000": ("", "", "phit_sp_0012"),
            "3030048000": ("", "", "phit_gu_0013"),
            "3030049000": ("", "", "phit_sw_0015"),
            "3030050000": ("", "", "phit_wa_0015"),
            "3030053000": ("", "", "phit_sw_0015"),
            "3030054000": ("", "", "phit_3710177000"),
            "3030055000": ("", "", "phit_me_0013"),
            "3030056000": ("", "", "phit_sw_0013"),
            "3030057000": ("", "", "phit_me_0013"),
            "3030058000": ("", "", "phit_wa_0011"),
            "3030059000": ("", "", "phit_ax_0016"),
            "3030062000": ("", "", "phit_sw_0011"),
            "3030063000": ("", "", "phit_gu_0011"),
            "3030064000": ("", "", "phit_bw_0012"),
            "3030066000": ("", "", "phit_wa_0014"),
            "3030067000": ("", "", "phit_bw_0014"),
            "3030068000": ("", "", "phit_gu_0011"),
            "3030072000": ("", "", "phit_sw_0014"),
            "3030075000": ("", "", "phit_mc_0015"),
            "3030077000": ("", "", "phit_sw_0012"),
            "3030081000": ("", "", "phit_kt_0026"),
            "3030082000": ("", "", "phit_me_0025"),
            "3030084000": ("", "", "phit_kn_0016"),
            "3030085000": ("", "", "phit_gu_0013"),
            "3030090000": ("", "", "phit_wa_0016"),
            "3030092000": ("", "", "phit_wa_0016"),
            "3030093000": ("", "", "phit_3030093006"),
            "3030096000": ("", "", "phit_sp_0011"),
            "3030097000": ("", "", "phit_sw_0011"),
            "3030100000": ("", "", "phit_wa_0014"),
            "3030102000": ("", "", "phit_wa_0013"),
            "3030103000": ("", "", "phit_sw_0013"),
            "3030106000": ("", "", "phit_wa_0013"),
            "3030107000": ("", "", "phit_sp_0012"),
            "3030108000": ("", "", "phit_3040023000"),
            "3030109000": ("", "", "phit_me_0015"),
            "3030110000": ("", "", "phit_sp_0011"),
            "3030112000": ("", "", "phit_gu_0013"),
            "3030113000": ("", "", "phit_bw_0011"),
            "3030116000": ("", "", "phit_ax_0015"),
            "3030117000": ("", "", "phit_me_0015"),
            "3030118000": ("", "", "phit_kt_0014"),
            "3030119000": ("", "", "phit_ax_0011"),
            "3030121000": ("", "", "phit_sw_0013"),
            "3030122000": ("", "", "phit_me_0013"),
            "3030123000": ("", "", "phit_kn_0012"),
            "3030127000": ("", "", "phit_me_0011"),
            "3030128000": ("", "", "phit_ax_0014"),
            "3030129000": ("", "", "phit_sw_0016"),
            "3030133000": ("", "", "phit_sp_0013"),
            "3030134000": ("", "", "phit_kn_0013"),
            "3030139000": ("", "", "phit_ax_0013"),
            "3030140000": ("", "", "phit_wa_0015"),
            "3030147000": ("", "", "phit_me_0013"),
            "3030149000": ("", "", "phit_mc_0013"),
            "3030151000": ("", "", "phit_3030022000"),
            "3030154000": ("", "", "phit_gu_0021_silent"),
            "3030155000": ("", "", "phit_gu_0011_silent"),
            "3030157000": ("", "", "phit_sw_0003"),
            "3030158000": ("", "", "phit_3020065000"),
            "3030159000": ("", "", "phit_gu_0013"),
            "3030161000": ("", "", "phit_wa_0011"),
            "3030163000": ("", "", "phit_3040070000"),
            "3030165000": ("", "", "phit_3040007000"),
            "3030168000": ("", "", "phit_3040050000"),
            "3030169000": ("", "", "phit_me_0014"),
            "3030170000": ("", "", "phit_3040071000"),
            "3030175000": ("", "", "phit_sw_0013"),
            "3030176000": ("", "", "phit_sw_0012"),
            "3030178000": ("", "", "phit_kt_0013"),
            "3030179000": ("", "", "phit_bw_0014"),
            "3030181000": ("", "", "phit_gu_0014"),
            "3030182000": ("", "", "phit_3040098000"),
            "3030183000": ("", "", "phit_kn_0015"),
            "3030184000": ("", "", "phit_kt_0013"),
            "3030185000": ("", "", "phit_gu_0016"),
            "3030186000": ("", "", "phit_me_0012_silent"),
            "3030187000": ("", "", "phit_bw_0011"),
            "3030191000": ("", "", "phit_sw_0014"),
            "3030195000": ("", "", "phit_sw_0015"),
            "3030199000": ("", "", "phit_3040084000"),
            "3030200000": ("", "", "phit_sw_0011"),
            "3030201000": ("", "", "phit_3040052000"),
            "3030202000": ("", "", "phit_me_0004"),
            "3030203000": ("", "", "phit_3030083000"),
            "3030206000": ("", "", "phit_kt_0013"),
            "3030221000": ("", "", "phit_3040057000"),
            "3030223000": ("", "", "phit_3040006000"),
            "3030225000": ("", "", "phit_3040024000"),
            "3030230000": ("", "", "phit_gu_0001"),
            "3030233000": ("", "", "phit_3040078000"),
            "3030239000": ("", "", "phit_gu_0015"),
            "3030246000": ("", "", "phit_3040145000"),
            "3030250000": ("", "", "phit_ax_0013"),
            "3030268000": ("", "", "phit_bw_0011"),
            "3030272000": ("", "", "phit_3040191000"),
            "3030273000": ("", "", "phit_3030262000"),
            "3040014000": ("", "", "phit_3040004000"),
            "3040053000": ("", "", "phit_3040043000"),
            "3040056000": ("", "", "phit_3040028000"),
            "3040073000": ("", "", "phit_3030101000"),
            "3040090000": ("", "", "phit_3040050000"),
            "3040091000": ("", "", "phit_3040060000"),
            "3040110000": ("", "", "phit_3040070000"),
            "3040126000": ("", "b", "phit_3040100000"),
            "3040127000": ("", "", "phit_3040081000"),
            "3040128000": ("", "", "phit_3040025000"),
            "3040136000": ("", "", "phit_wa_0001"),
            "3040151000": ("", "", "phit_3040123000"),
            "3040154000": ("", "", "phit_sw_0015"),
            "3040176000": ("", "", "phit_3040068000"),
            "3040177000": ("", "", "phit_3040148000"),
            "3040210000": ("", "", "phit_3040138000"),
            "3040224000": ("", "", "phit_3040153000"),
            "3040232000": ("3040158000", "", "phit_3040158000"),
            "3710001000": ("", "", "phit_3040054000_03"),
            "3710002000": ("", "", "phit_3030008000_03"),
            "3710003000": ("", "", "phit_3040065000_03"),
            "3710004000": ("", "", "phit_3040227000"),
            "3710005000": ("", "", "phit_3030253000"),
            "3710006000": ("", "", "phit_3040027000"),
            "3710007000": ("", "", "phit_3040141000"),
            "3710008000": ("", "", "phit_3040143000"),
            "3710009000": ("", "", "phit_3040237000"),
            "3710010000": ("", "", "phit_3040237000"),
            "3710011000": ("", "", "phit_3040209000"),
            "3710012000": ("", "", "phit_3040209000"),
            "3710013000": ("", "", "phit_3040141000"),
            "3710014000": ("", "", "phit_3040255000"),
            "3710017000": ("", "", "phit_3040013000"),
            "3710018000": ("", "", "phit_3040071000_03"),
            "3710019000": ("3040028000", "", "phit_3040028000"),
            "3710020000": ("3040023000", "", "phit_3040023000"),
            "3710021000": ("", "", "phit_3040227000"),
            "3710022000": ("", "", "phit_3040083000"),
            "3710023000": ("", "", "phit_3040077000_03"),
            "3710024000": ("3030019000", "", "phit_3040141000"),
            "3710025000": ("3040057000", "", "phit_3040057000"),
            "3710026000": ("3040050000", "", "phit_3040050000"),
            "3710030000": ("", "", "phit_3040050000"),
            "3710031000": ("", "", "phit_3040237000"),
            "3710032000": ("", "", "phit_3040023000"),
            "3710033000": ("3040040000", "", "phit_3040040000"),
            "3710034000": ("3040013000", "", "phit_3040013000"),
            "3710035000": ("", "", "phit_3040054000_03"),
            "3710036000": ("", "", "phit_3040141000"),
            "3710037000": ("", "", "phit_3040077000_03"),
            "3710038000": ("", "", "phit_3040068000_03"),
            "3710039000": ("", "", "phit_3040101000"),
            "3710040000": ("", "", "phit_3040117000"),
            "3710042000": ("3040009000", "", "phit_3040009000"),
            "3710043000": ("3040003000", "", "phit_3040003000"),
            "3710045000": ("", "", "phit_3040209000"),
            "3710046000": ("", "", "phit_3040257000"),
            "3710047000": ("", "", "phit_3040054000_03"),
            "3710048000": ("", "", "phit_3040092000"),
            "3710050000": ("", "", "phit_3030008000_03"),
            "3710052000": ("", "", "phit_3040077000_03"),
            "3710053000": ("", "", "phit_3040068000_03"),
            "3710054000": ("", "", "phit_wa_0001"),
            "3710055000": ("", "", "phit_wa_0001"),
            "3710058000": ("", "", "phit_3040120000"),
            "3710060000": ("", "", "phit_3040140000"),
            "3710061000": ("", "", "phit_3030231000"),
            "3710062000": ("", "", "phit_3040010000"),
            "3710063000": ("", "", "phit_3040001000_03"),
            "3710064000": ("", "", "phit_3040060000_03"),
            "3710067000": ("", "", "phit_3040120000"),
            "3710068000": ("", "", "phit_3040035000"),
            "3710069000": ("", "", "phit_3030235000"),
            "3710070000": ("", "", "phit_3040172000_03"),
            "3710071000": ("", "", "phit_3040147000_03"),
            "3710072000": ("", "", "phit_3040031000"),
            "3710074000": ("", "", "phit_3040036000"),
            "3710076000": ("", "", "phit_3040159000"),
            "3710078000": ("", "", "phit_3040098000"),
            "3710080000": ("", "", "phit_3040030000"),
            "3710081000": ("", "", "phit_3040070000"),
            "3710082000": ("", "", "phit_3040147000"),
            "3710083000": ("", "", "phit_3040098000"),
            "3710087000": ("", "", "phit_3040187000_02"),
            "3710088000": ("", "", "phit_3040153000"),
            "3710089000": ("", "", "phit_3840153000"),
            "3710092000": ("", "", "phit_3040098000"),
            "3710097000": ("", "", "phit_3030196000"),
            "3710105000": ("", "", "phit_3040098000"),
            "3710106000": ("", "", "phit_3040033000"),
            "3710107000": ("", "", "phit_3040039000"),
            "3710112000": ("", "", "phit_1040612000"),
            "3710117000": ("", "", "phit_3030172000_03"),
            "3710125000": ("", "", "phit_3040196000"),
            "3710130000": ("", "", "phit_3040192000"),
            "3710134000": ("", "", "phit_3040155000"),
            "3710139000": ("", "", "phit_3040098000"),
            "3710167000": ("", "", "phit_3040331000")
        }
        self.class_lookup = { # need to be manually updated..... :(
            "150201_sw": ["dkf_sw", "dkf_kn"], # dark fencer
            "200201_kn": ["acm_kn", "acm_gu"], # alchemist
            "310401_sw": ["mcd_sw"], # mac do
            "130201_wa": ["hrm_wa", "hrm_kn"], # hermit
            "120401_wa": ["hlr_wa", "hlr_sp"], # iatromantis
            "150301_sw": ["csr_sw", "csr_kn"], # chaos ruler
            "170201_bw": ["sdw_bw", "sdw_gu"], # sidewinder
            "240201_gu": ["gns_gu"], # gunslinger
            "360001_me": ["vee_me"], # vyrn suit
            "310701_sw": ["fal_sw"], # fallen
            "400001_kt": ["szk_kt"], # zhuque
            "450301_sw": ["rlc_sw", "rlc_gu"], # relic buster
            "140301_kn": ["gzk_kn", "gzk_gu"], # bandit tycoon
            "110001_sw": ["kni_sw", "kni_sp"], # knight
            "270301_mc": ["ris_mc"], # rising force
            "290201_gu": ["kks_gu"], # mechanic
            "190101_sp": ["drg_sp", "drg_ax"], # dragoon
            "140201_kn": ["hky_kn", "hky_gu"], # hawkeye
            "240301_gu": ["sol_gu"], # soldier
            "120301_wa": ["sag_wa", "sag_sp"], # sage
            "120101_wa": ["cle_wa", "cle_sp"], # cleric
            "150101_sw": ["ars_sw", "ars_kn"], # arcana dueler
            "130301_wa": ["wrk_wa", "wrk_kn"], # warlock
            "130401_wa": ["mnd_wa", "mnd_kn"], # manadiver
            "310601_sw": ["edg_sw"], # eternal 2
            "120001_wa": ["pri_wa", "pri_sp"], # priest
            "180101_mc": ["mst_kn", "mst_mc"], # bard
            "200301_kn": ["dct_kn", "dct_gu"], # doctor
            "220201_kt": ["smr_bw", "smr_kt"], # samurai
            "140001_kn": ["thi_kn", "thi_gu"], # thief
            "370601_me": ["bel_me"], # belial 1
            "370701_me": ["ngr_me"], # cook
            "330001_sp": ["sry_sp"], # qinglong
            "370501_me": ["phm_me"], # anime s2 skin
            "440301_bw": ["rbn_bw"], # robin hood
            "160201_me": ["ogr_me"], # ogre
            "210301_me": ["mhs_me", "mhs_kt"], # runeslayer
            "310001_sw": ["lov_sw"], # lord of vermillion
            "370801_me": ["frb_me"], # belial 2
            "180201_mc": ["sps_kn", "sps_mc"], # superstar
            "310301_sw": ["chd_sw"], # attack on titan
            "125001_wa": ["snt_wa"], # santa
            "110301_sw": ["spt_sw", "spt_sp"], # spartan
            "310801_sw": ["ykt_sw"], # yukata
            "110201_sw": ["hsb_sw", "hsb_sp"], # holy saber
            "230301_sw": ["glr_sw", "glr_kt"], # glorybringer
            "130101_wa": ["srr_wa", "srr_kn"], # sorcerer
            "430301_wa": ["mnk_wa", "mnk_me"], # monk
            "280301_kn": ["msq_kn"], # masquerade
            "250201_wa": ["wmn_wa"], # mystic
            "160001_me": ["grp_me"], # grappler
            "110101_sw": ["frt_sw", "frt_sp"], # sentinel
            "270201_mc": ["drm_mc"], # taiko
            "300301_sw": ["crs_sw", "crs_kt"], # chrysaor
            "360101_gu": ["rac_gu"], # platinum sky 2
            "300201_sw": ["gda_sw", "gda_kt"], # gladiator
            "100101_sw": ["wrr_sw", "wrr_ax"], # warrior
            "170001_bw": ["rng_bw", "rng_gu"], # ranger
            "280201_kn": ["dnc_kn"], # dancer
            "410301_mc": ["lmb_ax", "lmb_mc"],
            "100001_sw": ["fig_sw", "fig_ax"], # fighter
            "180301_kn": ["els_kn", "els_mc"], # elysian
            "250301_wa": ["knd_wa"], # nekomancer
            "260201_kn": ["asa_kn"], # assassin
            "370301_me": ["kjm_me"], # monster 3
            "140101_kn": ["rdr_kn", "rdr_gu"], # raider
            "180001_mc": ["hpt_kn", "hpt_mc"], # superstar
            "370001_me": ["kjt_me"], # monster 1
            "165001_me": ["stf_me"], # street fighter
            "160301_me": ["rsr_me"], # luchador
            "100201_sw": ["wms_sw", "wms_ax"], # weapon master
            "170301_bw": ["hdg_bw", "hdg_gu"], # nighthound
            "230201_sw": ["sdm_sw", "sdm_kt"], # swordmaster
            "310201_sw": ["swm_sw"], # summer
            "190301_sp": ["aps_sp", "aps_ax"], # apsaras
            "100401_sw": ["vkn_sw", "vkn_ax"], # viking
            "150001_sw": ["enh_sw", "enh_kn"], # enhancer
            "220301_bw": ["kng_bw", "kng_kt"], # kengo
            "120201_wa": ["bis_wa", "bis_sp"], # bishop
            "310101_sw": ["ani_sw"], # anime season 1
            "130001_wa": ["wiz_wa", "wiz_kn"], # wizard
            "185001_kn": ["idl_kn", "idl_mc"], # idol
            "100301_sw": ["bsk_sw", "bsk_ax"], # berserker
            "160101_me": ["kun_me"], # kung fu artist
            "370201_me": ["kjb_me"], # monster 2
            "110401_sw": ["pld_sw", "pld_sp"], # paladin
            "310501_sw": ["cnq_sw"], # eternal 1
            "310901_sw": ["vss_sw"], # versus skin
            "190001_sp": ["lnc_sp", "lnc_ax"], # lancer
            "420301_sp": ["cav_sp", "cav_gu"], # cavalier
            "190201_sp": ["vkr_sp", "vkr_ax"], # valkyrie
            "260301_kn": ["tmt_kn"], # tormentor
            "210201_kt": ["nnj_me", "nnj_kt"], # ninja
            "370401_me": ["ybk_me"], # bird
            "320001_kn": ["sut_kn"], # story dancer
            "170101_bw": ["mrk_bw", "mrk_gu"], # archer
            "311001_sw": ["gkn_sw"], # school
            "340001_ax": ["gnb_ax"], # xuanwu
            "360201_gu": ["ebi_gu"], # premium friday
            "370901_me": ["byk_me"], # baihu
            "460301_sw": ["ymt_sw", "ymt_kt"] # yamato
        }
        self.class_ougi = {
            "320001_kn": "1040115000", # school dancer
            "340001_ax": "1040315700", # xuanwu
            "400001_kt": "1040913700", # zhuque
            "330001_sp": "1040216600", # qinglong
            "370901_me": "1040617400", # baihu
            "310501_sw": "1040016700", # eternal 1
            "310601_sw": "1040016800", # eternal 2
            "360101_gu": "1040508600", # platinum sky 2
            "370801_me": "1040616000", # belial 2
            "310701_sw": "1040016900", # fallen
            "370001_me": "1040610300", # monster 1
            "310901_sw": "1040019100", # versus
            "370201_me": "1040610200", # monster 2
            "370301_me": "1040610400", # monster 3
            "370601_me": "1040614400", # belial 1
            "370701_me": "1040615300", # cook
            "310001_sw": "1040009100", # lord of vermillion
            "310801_sw": "1040018800", # yukata
            "311001_sw": "1040020200", # school
            "310301_sw": "1040014200", # attack on titan
            "360201_gu": "1040515800" # premium friday
        }
        self.class_placeholders = {
            "sw": "1010000000",
            "kn": "1010100000",
            "sp": "1010200000",
            "ax": "1010300000",
            "wa": "1010400000",
            "gu": "1010500000",
            "me": "1010600000",
            "bw": "1010700000",
            "mc": "1010800000",
            "kt": "1010900000"
        }
        self.exclusion = set([])
        self.loadIndex()

    def req(self, url, headers={}, head=False):
        if head:
            response = self.client.head(url.replace('/img/', self.quality[0]).replace('/js/', self.quality[1]), headers={'connection':'keep-alive'} |headers, timeout=50)
            if response.status_code != 200: raise Exception()
            return True
        else:
            response = self.client.get(url.replace('/img/', self.quality[0]).replace('/js/', self.quality[1]), headers={'connection':'keep-alive'} |headers, timeout=50)
            if response.status_code != 200: raise Exception()
            return response.content

    def run(self):
        max_thread = 2
        print("Updating Database...")
        if self.force_update:
            print("Note: All characters will be updated")
            s = input("Type quit to exit now:").lower()
            if s == "quit":
                print("Process aborted")
                return
        self.running = True
        with concurrent.futures.ThreadPoolExecutor(max_workers=120) as executor:
            futures = []
            possibles = ["3020{}000", "3030{}000", "3040{}000", "3710{}000", "10100{}00", "10200{}00", "10300{}00", "10400{}00", "10201{}00", "10101{}00", "10301{}00", "10401{}00", "10102{}00", "10202{}00", "10302{}00", "10402{}00", "10103{}00", "10203{}00", "10303{}00", "10403{}00", "10104{}00", "10204{}00", "10304{}00", "10404{}00", "10105{}00", "10205{}00", "10305{}00", "10405{}00", "10106{}00", "10206{}00", "10306{}00", "10406{}00", "10107{}00", "10207{}00", "10307{}00", "10407{}00", "10108{}00", "10208{}00", "10308{}00", "10408{}00", "10209{}00", "10109{}00", "10309{}00", "10409{}00"]
            err = []
            for p in possibles:
                err.append([0, True, Lock(), 0])
            for i in range(max_thread):
                futures.append(executor.submit(self.styleProcessing))
                futures.append(executor.submit(self.run_class, i, max_thread))
                for j in range(len(possibles)):
                    futures.append(executor.submit(self.run_sub, i, max_thread, err[j], possibles[j]))
            finished = 0
            for future in concurrent.futures.as_completed(futures):
                future.result()
                finished += 1
                if finished == (len(futures) - max_thread):
                    self.running = False
                    print("Progress 100%")
                elif finished > (len(futures) - max_thread):
                    pass
                elif finished > 0 and finished % 10 == 0:
                    print("Progress {:.1f}%".format((100*finished)/(len(futures) - max_thread)))
        self.running = False
        print("Done")
        sum_res = 0
        for e in err:
            sum_res += e[3]
        if sum_res > 0:
            print("New additions:")
            if err[0][3] > 0: print(err[0][3], "R Characters")
            if err[1][3] > 0: print(err[1][3], "SR Characters")
            if err[2][3] > 0: print(err[2][3], "SSR Characters")
            if err[3][3] > 0: print(err[3][3], "Skins")
            i = 4
            while i < len(possibles):
                for j in range(4):
                    if err[i+j][3] > 0:
                        print(err[i+j][3], ["N", "R", "SR", "SSR"][j], ["Swords", "Daggers", "Spears", "Axes", "Staffs", "Guns", "Melees", "Bows", "Harps", "Katanas"][(i-4)//4])
                i += 4
            self.loadIndex()
            self.saveIndex()

    def run_sub(self, start, step, err, file):
        eid = start
        while err[1] and err[0] < 20 and self.running:
            f = file.format(str(eid).zfill(3))
            if self.force_update or f not in self.index:
                if file.startswith("10"): r = self.update_weapon(f)
                else: r = self.update(f)
                if not r:
                    with err[2]:
                        err[0] += 1
                        if err[0] >= 20:
                            err[1] = False
                            return
                else:
                    with err[2]:
                        err[0] = 0
                        err[3] += 1
            else:
                with err[2]:
                    err[0] = 0
            eid += step

    def run_class(self, start, step):
        keys = list(self.class_lookup.keys())
        i = start
        while i < len(keys):
            f = keys[i]
            if self.force_update or f not in self.index:
                self.update_class(f)
            i += step

    def update_class(self, id):
        try:
            if id in self.exclusion: return False
            if id not in self.class_lookup: return False
            if not self.download_assets: # don't check anything if this asset isn't found
                try:
                    self.req(self.imgUri + "/sp/assets/leader/m/" + id.split('_')[0] + "_01.jpg")
                except:
                    if not self.debug_mode: return False
            colors = []
            for i in ["01", "02", "03", "04", "05", "80", ]:
                try:
                    self.getJS(self.class_lookup[id][0] + "_0_{}".format(i))
                    if self.download_assets: self.getJS(self.class_lookup[id][0] + "_1_{}".format(i))
                    colors.append(self.class_lookup[id][0] + "_0_{}".format(i))
                except:
                    pass
            if id in self.class_ougi: # skin with custom weapon
                mortal = "mortal_B" # skin with custom ougis use this
                mc_cjs = colors[0]
                phit = "phit_" + self.class_ougi[id]
                sp = "sp_" + self.class_ougi[id]
                try:
                    self.getJS(phit)
                except:
                    phit = None
                for s in ["", "_0", "_0_s2", "_s2"]:
                    try:
                        self.getJS(sp+s)
                        sp = sp+s
                        break
                    except:
                        if s == "_s2":
                            sp = None
            else: # regular class
                mortal = "mortal_A"
                mc_cjs = colors[0]
                wid = self.class_placeholders[mc_cjs.split('_')[1]]
                sp = None
                phit = None
                for fn in ["phit_{}".format(id), "sp_{}".format(id), "sp_{}_0".format(id), "sp_{}_0_s2".format(id), "sp_{}_s2".format(id)]:
                    try:
                        self.getJS(fn)
                        if fn.startswith('phit'):
                            phit = fn
                        elif fn.startswith('sp'):
                            sp = fn
                            break
                    except:
                        pass
                if self.download_assets: # download asset
                    for fn in ["", "_1", "_2"]:
                        try:
                            print(self.imgUri + "/sp/cjs/" + wid + fn + ".png")
                            data = self.req(self.imgUri + "/sp/cjs/" + wid + fn + ".png")
                            with open("img/sp/cjs/" + wid + fn + ".png", "wb") as f:
                                f.write(data)
                        except:
                            pass
            if phit is None:
                phit = "phit_{}_0001".format(mc_cjs.split('_')[1])
            if sp is None:
                sp = 'sp_{}_01210001'.format(mc_cjs.split('_')[1])
            character_data = {}
            character_data['0'] = {'length': len(colors)*2}
            character_data['1'] = {}
            character_data['2'] = {"1": {"1": ""},"2": {"1": ""}}
            # for each version
            import traceback
            for x, c in enumerate(colors):
                if c == colors[0]: var = ""
                else: var = " v"+str(x)
                for i in range(2):
                    if i == 1:
                        if sp.endswith('_0'):
                            sp = sp[:-2] + '_1'
                            if self.download_assets: self.getJS(sp)
                        elif sp.endswith('_0_s2'):
                            sp = sp[:-5] + '_1_s2'
                            if self.download_assets: self.getJS(sp)
                    character_data['0'][str(x*2+i)] = ('Gran' if i == 0 else 'Djeeta') + var
                    character_data['1'][str(x*2+i)] = {}
                    character_data['1'][str(x*2+i)]['id'] = id # CLASS ONLY, only for fancy stuff
                    try:
                        if wid is not None:
                            character_data['1'][str(x*2+i)]['wpn'] = wid
                    except:
                        pass
                    character_data['1'][str(x*2+i)]['cjs'] = [c.replace('_0_', '_{}_'.format(i))]
                    character_data['1'][str(x*2+i)]['action_label_list'] = ['ability', mortal, 'stbwait', 'short_attack', 'double', 'triple']
                    character_data['1'][str(x*2+i)]['effect'] = [phit]
                    character_data['1'][str(x*2+i)]['special'] = [{"random":0,"list":[{"target":"them","cjs":sp,"fixed_pos_owner_bg":0,"full_screen":0}]}]
                    # update full screen mode
                    if '_s2' in character_data['1'][str(x*2+i)]['special'][0]['list'][0]['cjs'] or '_s3' in character_data['1'][str(x*2+i)]['special'][0]['list'][0]['cjs']:
                        character_data['1'][str(x*2+i)]['special'][0]['list'][0]['full_screen'] = 1
                    character_data['1'][str(x*2+i)]['cjs_pos'] = [{"y":0,"x":0}]
                    character_data['1'][str(x*2+i)]['special_pos'] = [[{"y":0,"x":0}]]
            with open("json/" + id + ".json", 'w') as outfile:
                json.dump(character_data, outfile)
            return True
        except Exception as e:
            print(traceback.format_exc())
            print("Error", e, "for id", id)
            return False

    def update_weapon(self, id):
        try:
            if id in self.exclusion: return False
            if not self.download_assets: # don't check anything if this asset isn't found
                try:
                    self.req(self.imgUri + "/sp/assets/weapon/m/" + id + ".jpg")
                except:
                    if not self.debug_mode: return False
            # containers
            mc_cjs = self.possible_class[(int(id) // 100000) % 10]
            sp = None
            phit = None
            for fn in ["phit_{}".format(id), "sp_{}".format(id), "sp_{}_0".format(id), "sp_{}_0_s2".format(id), "sp_{}_s2".format(id)]:
                try:
                    self.getJS(fn)
                    if fn.startswith('phit'):
                        phit = fn
                    elif fn.startswith('sp'):
                        sp = fn
                        break
                except:
                    pass
            if self.download_assets: # download asset
                for fn in ["", "_1", "_2"]:
                    try:
                        data = self.req(self.imgUri + "/sp/cjs/" + id + fn + ".png")
                        with open("img/sp/cjs/" + id + fn + ".png", "wb") as f:
                            f.write(data)
                    except:
                        pass
            character_data = {}
            character_data['0'] = {'length': 2}
            character_data['1'] = {}
            character_data['2'] = {"1": {"1": ""},"2": {"1": ""}}
            # for each version
            for i in range(2):
                character_data['0'][str(i)] = 'Gran' if i == 0 else 'Djeeta'
                character_data['1'][str(i)] = {}
                character_data['1'][str(i)]['wpn'] = id
                character_data['1'][str(i)]['cjs'] = [mc_cjs.format(i)]
                character_data['1'][str(i)]['action_label_list'] = ['ability', 'mortal_A', 'stbwait', 'short_attack', 'double', 'triple']
                character_data['1'][str(i)]['effect'] = [phit if phit is not None else "phit_{}_0001".format(mc_cjs.split('_')[1])]
                character_data['1'][str(i)]['special'] = [{"random":0,"list":[{"target":"them","cjs":(sp if sp is not None else 'sp_{}_01210001'.format(mc_cjs.split('_')[1])),"fixed_pos_owner_bg":0,"full_screen":0}]}]
                # update full screen mode
                if '_s2' in character_data['1'][str(i)]['special'][0]['list'][0]['cjs'] or '_s3' in character_data['1'][str(i)]['special'][0]['list'][0]['cjs']:
                    character_data['1'][str(i)]['special'][0]['list'][0]['full_screen'] = 1
                character_data['1'][str(i)]['cjs_pos'] = [{"y":0,"x":0}]
                character_data['1'][str(i)]['special_pos'] = [[{"y":0,"x":0}]]
            with open("json/" + id + ".json", 'w') as outfile:
                json.dump(character_data, outfile)
            return True
        except Exception as e:
            print("Error", e, "for id", id)
            return False

    def update(self, id, style=""):
        try:
            if id in self.exclusion: return False
            if not self.download_assets: # don't check anything if this asset isn't found
                try:
                    self.req(self.imgUri + "/sp/assets/npc/m/" + id + "_01" + style + ".jpg", head=True)
                except:
                    if not self.debug_mode: return False
            # containers
            character_data = {}
            good_variations = {}
            good_phits = {}
            good_nsp = {}
            found = False
            mortal = {}
            # npc file check
            for i in range(0, len(self.variations), 2):
                fcheck = False
                for ftype in ["", "_s2"]:
                    for j in range(2):
                        try:
                            fn = "npc_{}{}{}".format(id, self.variations[i+j][0].format(style), ftype)
                            ret = self.getJS(fn)
                            if not ret[0]:
                                data = self.req(self.cjsUri + fn + ".js").decode('utf-8')
                            else:
                                data = ret[1].decode('utf-8')
                            if self.variations[i+j] not in mortal: # for characters such as lina
                                for m in ['mortal_A', 'mortal_B', 'mortal_C', 'mortal_D', 'mortal_E', 'mortal_F', 'mortal_G', 'mortal_H', 'mortal_I', 'mortal_K']:
                                    if m in data:
                                        mortal[self.variations[i+j]] = m
                                        break
                            found = True
                            good_variations[self.variations[i+j]] = fn + ".js"
                            fcheck = True
                        except:
                            break
                    if fcheck: break
            if not found: return False # no npc found, we quit
            if not id.startswith("371") and style == "":
                self.queue.put((id, ["_st2"])) # style check
            for v in good_variations:
                found = False
                # ougi check
                for s in ["", "_s2", "_s3", "_0_s2", "_0_s3"]:
                    for m in ["", "_a", "_b", "_c", "_d", "_e", "_f", "_g", "_h", "_i", "_j"]:
                        try:
                            fn = "nsp_{}{}{}{}".format(id, v[0].format(style), s, m)
                            self.getJS(fn)
                            good_nsp[v] = fn + ".js"
                            found = True
                            break
                        except:
                            pass
                    if found: break
                # attack check
                try:
                    fn = "phit_{}{}".format(id, v[1])
                    self.getJS(fn)
                    good_phits[v] = fn + ".js"
                except:
                    pass
            
            # building the character data
            keys = list(good_variations.keys())
            character_data['0'] = {'length': len(keys)}
            character_data['1'] = {} 
            character_data['2'] = {"1": {"1": ""},"2": {"1": ""}}
            # for each version
            for i in range(len(keys)):
                character_data['0'][str(i)] = keys[i][2]
                character_data['1'][str(i)] = {}
                character_data['1'][str(i)]['cjs'] = [good_variations[keys[i]].replace('.js', '')]
                character_data['1'][str(i)]['action_label_list'] = ['ability', mortal[keys[i]], 'stbwait', 'short_attack', 'double', 'triple']
                if keys[i] in good_phits:
                    character_data['1'][str(i)]['effect'] = [good_phits[keys[i]].replace('.js', '')]
                else: # if no phit, try to use inferior uncap ones
                    for j in range(i-1, -1, -1):
                        if keys[i][1] == keys[j][1] and good_variations[keys[j]] in good_phits:
                            character_data['1'][str(i)]['effect'] = [good_phits[keys[j]].replace('.js', '')]
                            break
                # if no attack/phit AT ALL
                if 'effect' not in character_data['1'][str(i)]:
                    if id in self.patches: # apply patch if existing
                        character_data['1'][str(i)]['effect'] = [self.patches[id][2]]
                        self.getJS(character_data['1'][str(i)]['effect'][0])
                    else: # put default
                        character_data['1'][str(i)]['effect'] = ['phit_ax_0001']
                # if no ougi/nsp
                if keys[i] in good_nsp:
                    character_data['1'][str(i)]['special'] = [{"random":0,"list":[{"target":"them","cjs":good_nsp[keys[i]].replace('.js', ''),"fixed_pos_owner_bg":0,"full_screen":0}]}]
                else: # try to use inferior uncap one
                    for j in range(i-1, -1, -1):
                        if keys[j] in good_nsp:
                            character_data['1'][str(i)]['special'] = [{"random":0,"list":[{"target":"them","cjs":good_nsp[keys[j]].replace('.js', ''),"fixed_pos_owner_bg":0,"full_screen":1}]}]
                            break
                # if no special AT ALL
                if 'special' not in character_data['1'][str(i)] and id in self.patches: # apply patch if existing
                    character_data['1'][str(i)]['special'] = [{"random":0,"list":[{"target":"them","cjs":good_variations[keys[j]].replace('.js', '').replace('npc', 'nsp').replace(id, self.patches[id][0]) + self.patches[id][1] ,"fixed_pos_owner_bg":0,"full_screen":1}]}]
                    self.getJS(character_data['1'][str(i)]['special'][0]['list'][0]['cjs'])
                # raise error if still no special
                if 'special' not in character_data['1'][str(i)]: raise Exception("No special set")
                # update full screen mode
                if '_s2' in character_data['1'][str(i)]['special'][0]['list'][0]['cjs'] or '_s3' in character_data['1'][str(i)]['special'][0]['list'][0]['cjs']:
                    character_data['1'][str(i)]['special'][0]['list'][0]['full_screen'] = 1
                character_data['1'][str(i)]['cjs_pos'] = [{"y":0,"x":0}]
                character_data['1'][str(i)]['special_pos'] = [[{"y":0,"x":0}]]
            with open("json/" + id + style + ".json", 'w') as outfile:
                json.dump(character_data, outfile)
            return True
        except Exception as e:
            print("Error", e, "for id", id)
            return False

    def processManifest(self, filename, manifest):
        if not self.download_assets:
            return (False, None)
        st = manifest.find('manifest:') + len('manifest:')
        ed = manifest.find(']', st) + 1
        data = json.loads(manifest[st:ed].replace('Game.imgUri+', '').replace('src:', '"src":').replace('type:', '"type":').replace('id:', '"id":'))
        for l in data:
            src = l['src'].split('?')[0]
            if src == '/sp/cjs/nsp_3020005000_01_ef081.png': continue # R deliford base form fix
            data = self.req(self.imgUri + src)
        
            with open("img/sp/cjs/" + src.split('/')[-1], "wb") as f:
                f.write(data)
        
        data = self.req(self.cjsUri + filename)
        with open("cjs/" + filename, "wb") as f:
            f.write(data)
        return (True, data)

    def styleProcessing(self):
        count = 0
        while self.running:
            try:
                id, styles = self.queue.get(block=True, timeout=0.1)
            except:
                continue
            for s in styles:
                if self.update(id, s):
                    count += 1
        return count

    def manualUpdate(self, ids):
        max_thread = 40
        counter = 0
        tcounter = 0
        self.running = True
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_thread+2) as executor:
            futures = []
            for id in ids:
                if len(id) == 10:
                    if id.startswith("10"): futures.append(executor.submit(self.update_weapon, id))
                    else: futures.append(executor.submit(self.update, id, ""))
                    tcounter += 1
                elif len(id) == 14 and id.startswith("30") and id[10] == '_':
                    futures.append(executor.submit(self.update, id.split('_')[0], id.split('_')[1]))
                    tcounter += 1
                elif id in self.class_lookup:
                    futures.append(executor.submit(self.update_class, id))
                    tcounter += 1
            if tcounter > 0:
                futures.append(executor.submit(self.styleProcessing))
                futures.append(executor.submit(self.styleProcessing))
                print("Attempting to update", tcounter, "element(s)")
                tfinished = 0
                for future in concurrent.futures.as_completed(futures):
                    tfinished += 1
                    if tfinished >= tcounter:
                        self.running = False
                    r = future.result()
                    if isinstance(r, int): counter += r
                    elif r: counter += 1
        self.running = False
        print("Done")
        if counter > 0:
            self.loadIndex()
            self.saveIndex()
            print(counter, "successfully processed ID")

    def getJS(self, js):
        data = self.req(self.manifestUri + js + ".js")
        if self.download_assets:
            with open("model/manifest/" + js + ".js", "wb") as f:
                f.write(data)
        return self.processManifest(js + ".js", data.decode('utf-8'))

    def phitUpdate(self, phit):
        try:
            self.getJS(phit)
        except Exception as e:
            pass

    def initFiles(self):
        tmp = self.download_assets
        self.download_assets = True
        with open("view/cjs_npc_demo.js", mode="r", encoding="utf-8") as f:
            data = f.read()
            a = 0
            while True:
                a = data.find('"enemy_', a)
                if a == -1: break
                a += len('"enemy_')
                enemy_id = data[a:data.find('"', a)]
                fn = "enemy_" + enemy_id
                
                self.getJS(fn)
            print("Enemies updated")
            
            # weapons stuff
            to_update = ['phit_0000000000']
            for p in self.possible_class:
                to_update.append(p.format(0))
                to_update.append(p.format(1))
            weapons = ["sw", "kn", "sp", "ax", "wa", "gu", "me", "bw", "mc", "kt"]
            for w in weapons:
                to_update.append("sp_{}_01210001".format(w))
                for i in range(30):
                    for s in ["", "_silent"]:
                        to_update.append("phit_{}_{}{}".format(w, str(i).zfill(4), s))
            with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
                futures = []
                for phit in to_update:
                    futures.append(executor.submit(self.phitUpdate, phit))
                for future in concurrent.futures.as_completed(futures):
                    future.result()
            print("Phit files updated")
        self.download_assets = tmp

    def loadIndex(self):
        files = [f for f in os.listdir('json/') if os.path.isfile(os.path.join('json/', f))]
        known = []
        for f in files:
            if f.startswith("371") or f.startswith("304") or f.startswith("303") or f.startswith("302") or f.startswith("10") or (len(f.split('.json')[0]) == 9 and f[6] == '_'):
                known.append(f.split('.')[0])
        self.index = set(known)

    def saveIndex(self):
        with open("json/index.json", 'w') as outfile:
            i = list(self.index)
            i.sort()
            i.reverse()
            json.dump(i, outfile)
        print("Index updated")
        with open('json/changelog.json', mode='w', encoding='utf-8') as outfile:
            json.dump({'timestamp':int(datetime.now(timezone.utc).timestamp()*1000)}, outfile)
        print("changelog.json updated")

    def start(self, args):
        self.force_update = ('-force' in args)
        self.download_assets = ('-download' in args)
        self.debug_mode = ('-debug' in args)
        if '-init' in args:
            self.initFiles()
        if '-update' in args:
            self.manualUpdate(args['-update'])
        elif '-index' in args:
            self.saveIndex()
        else:
            self.run()

if __name__ == '__main__':
    args = {}
    expected_args = ["-force", "-download", "-init", "-index", "-update", "-debug"]
    update_flag = False
    for i in range(1, len(sys.argv)):
        if update_flag:
            if sys.argv[i] in expected_args:
                if sys.argv[i] in args:
                    print(sys.argv[i], "parameter already set")
                    exit(0)
                args[sys.argv[i]] = []
                update_flag = False
            else:
                args["-update"].append(sys.argv[i])
        else:
            if sys.argv[i] in expected_args:
                if sys.argv[i] in args:
                    print(sys.argv[i], "parameter already set")
                    exit(0)
                args[sys.argv[i]] = []
                if sys.argv[i] == '-update':
                    update_flag = True
            else:
                print("Unknown parameter", sys.argv[i])
                exit(0)
    Updater().start(args)