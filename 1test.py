'''
Author: peanutfisher meifajia@outlook.com
Date: 2024-11-06 15:02:22
LastEditors: peanutfisher meifajia@outlook.com
LastEditTime: 2024-11-12 16:41:37
FilePath: \AvailableLabBox\1test.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import urllib.parse
dts_1162 = ['296801611M1', '10.60.35.245', 'VMAX100K', 'V3']
dts_2205 = ['220002205M1', '10.60.8.150', 'PMAX2500', 'V4']
dts_2206 = ['220002206M1', '10.60.8.156', 'PMAX2500', 'V4']
dts_0142 = ['220200142M1', '10.60.8.162', 'PMAX8500', 'V4']

PASSWORD = '1nternal'

def dts_array_dict(dts_list, credential):
    dts_dict = {}
    sn_1 = dts_list[0]
    sn_2 = dts_list[0][:-1] + '2'
    ip_1 = dts_list[1]
    ip_2 = ip_1[:-1] + str(int(ip_1[-1]) + 1)
    model = dts_list[2]
    type = dts_list[-1]
    # encode CREDENTIAL for web link(some special mark like +(%2B), /(%2F), etc. need to be encoded)
    web_credential = urllib.parse.quote(credential)
    
    ra_link = f'http://{ip_1}:9519/login:{web_credential}:{PASSWORD}:SLC/remctrl_menu.html'
    cs1_link = f'http://{ip_1}:8888/toolbox/#/app?userName={web_credential}&password={PASSWORD}'
    cs2_link = f'http://{ip_2}:8888/toolbox/#/app?userName={web_credential}&password={PASSWORD}'

    if type == 'V4':
        dts_dict = dict(zip(['TYPE', 'RA_SN', 'RA', 'CS1_SN', 'CS1', 'CS2_SN', 'CS2'], [model, sn_1, ra_link, sn_1, cs1_link, sn_2, cs2_link]))
    else:
        dts_dict = dict(zip(['TYPE', 'RA_SN', 'RA', 'CS1_SN', 'CS1', 'CS2_SN', 'CS2'], [model, sn_1, ra_link, '', '', '', '']))
        
    
    if dts_dict:
        return dts_dict

def dts_array_list(credential):
    dts = []
    # create dict for each Sn and added to target list
    for each in [dts_1162, dts_2205, dts_2206, dts_0142]:
        result = dts_array_dict(each, credential)
        print(f'dts_dict: {result}')
        dts.append(result)
    
    if dts:
        print('========================================================================')
        print(dts)
        return dts 

dts_array_list('AwBOdwVS064G')