import logging
import requests
from lxml import etree
import urllib.parse
import re
from jinja2 import Environment, FileSystemLoader
import time
import os
import json
import aiohttp
from aiohttp import ClientTimeout
import asyncio
import PySimpleGUI as sg
import webbrowser
import threading
from queue import Queue

url_RA = 'https://phonebook.nexus.cec.delllabs.net/phonebook'
url_SS = 'https://phonebook.nexus.cec.delllabs.net/phonebook4'

PASSWORD = '1nternal'
Cur_Time = ''
COLOR = ['silver', 'lime']
raw_file = []
raw_file_name = 'Raw_Data'

SN_dict = {'202':'PMAX8500', '200':'PMAX2500', '976':'PMAX8000','979':'PMAX2000', '978':'VMAX250F', '977':'VMAX950F','975':'VMAX850F', '970':'VMAX450F', '972':'VMAX400K','967':'VMAX200K', '968':'VMAX100K'}

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('app.log', 'w')
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.addHandler(file_handler)
logger.addHandler(console_handler)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.debug('this is debug information')
logger.info('this is info information')
logger.warning('this is warning information')
logger.error('this is error information')
logger.critical('this is critical information')

def read_html(html):
    with open(html, 'r') as f:
        return f.read()
    logger.info(f'reading {html} into cache...')

def get_link(url):
    try:
        html = requests.get(url, verify=False, timeout=5).text
        logger.info(f'Connected to {url}')
    except Exception as e:
        logger.error(f'Can not connect to links: {url}, please check your Network connection and your VPN connection!!')
        sg.popup_error(f'Can not connect to links: {url}, please check your Network connection and your VPN connection!!', title='ERROR MESSAGE', font=('Arial', 11))
        return ([], 'None')

    links = etree.HTML(html).xpath('//tr')
    link_list = []
    for element in links:
        text = ["".join(td.itertext()).strip() for td in element.xpath('.//td')]
        link_list.append(text)
    
    link_list = [entry for entry in link_list if entry]
    cred = link_list[0][2] or link_list[1][2]
    return (link_list, cred)

async def check_link(link_list, credential, queue):
    web_credential = urllib.parse.quote(credential)
    html_list = []
    total_count = len(link_list)
    logger.info(f'There are total {total_count} items to be checked...')
    count = 0
    valid_count = 0

    for item in link_list:
        count += 1
        queue.put(('progress', count, total_count))
        
        url_dict = {}
        SN = item[1]
        link_RA = f'http://{SN}.storage.lab.emc.com:9519/login:{web_credential}:{PASSWORD}:SLC/remctrl_menu.html'
        link_SS = f'http://{SN}.storage.lab.emc.com:8888/toolbox/#/app?userName={web_credential}&password={PASSWORD}'
        SN_2 = SN[:-1]+'2'
        link_SS_2 = f'http://{SN_2}.storage.lab.emc.com:8888/toolbox/#/app?userName={web_credential}&password={PASSWORD}'
        model = get_model(SN)
        
        result_SS = False
        if model in {'PMAX8500', 'PMAX2500'}:
            result_SS = await test_link(link_SS)

        result_RA = await test_link(link_RA)
        
        if result_RA or result_SS:
            raw_file.append(item)
            valid_count += 1
            logger.info(f'This is the {valid_count}th available link.')
        
        if result_RA:
            url_dict.update({
                'COLOR': COLOR[valid_count % 2],
                'LABEL': item[0],
                'TYPE': model,
                'Building': item[-5],
                'Lab': item[-4],
                'Tile': item[-3],
                'Owner': item[-2],
                'Group': item[-1],
                'RA_SN': SN,
                'RA': link_RA,
                'CS1_SN': '',
                'CS2_SN': '',
                'CS1': '',
                'CS2': ''
            })
            if result_SS:
                url_dict.update({
                    'CS1_SN': SN,
                    'CS2_SN': SN_2,
                    'CS1': link_SS,
                    'CS2': link_SS_2
                })
        else:
            if result_SS:
                url_dict.update({
                    'COLOR': COLOR[count % 2],
                    'LABEL': item[0],
                    'TYPE': model,
                    'Building': item[-5],
                    'Lab': item[-4],
                    'Tile': item[-3],
                    'Owner': item[-2],
                    'Group': item[-1],
                    'CS1_SN': SN,
                    'CS2_SN': SN_2,
                    'CS1': link_SS,
                    'CS2': link_SS_2,
                    'RA_SN': '',
                    'RA': ''
                })
            else:
                logger.warning(f'No available lab box links found for {SN}!')
        
        if url_dict:
            html_list.append(url_dict)

    write_file(raw_file)
    queue.put(('done', html_list))

def get_model(sn):
    model = ''
    for sn_pattern in SN_dict.keys():
        p = re.compile('\d'+ sn_pattern + '\d+M\d')
        result = p.search(sn)
        if result:
            model = SN_dict[sn_pattern]
            break
    return model

async def test_link(link):
    try:
        timeout = ClientTimeout(total=18)
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), timeout=timeout) as session:
            async with session.get(link) as response:
                if response.status == 200:
                    return True
    except:
        logger.warning(f'unreachable url: {link}')
    return False

def html_table(data, cred):
    global Cur_Time
    global PASSWORD
    ctime = time.localtime()
    Cur_Time = time.strftime("%Y%m%d%H%M", ctime)
    web_time = time.strftime("%H:%M:%S %m/%d/%Y", ctime)
    
    if data:
        file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))
        env = Environment(loader = file_loader)
        template = env.get_template('template.html')
        output = template.render(url_list=data, generated_time=web_time, credential=cred, password=PASSWORD)
        
        filename = 'Available_Lab_boxes ' + Cur_Time + '.html'
        with open(filename, 'w') as f:
            f.write(output)
        
        sg.popup(f'Done! The {filename} is created, Click OK to open it in your browser')
        cur_dir = os.getcwd()
        html_path = os.path.join(cur_dir, filename)
        webbrowser.open('file://' + html_path)
    else:
        sg.popup_error(f'Cannot generate HTML, please check your Network connection and your VPN connection!!', title='ERROR MESSAGE', font=('Arial', 11))

def write_file(listname):
    if listname:
        with open('Raw_Data', 'w') as f:
            json.dump(listname, f, ensure_ascii=False, indent=4)
        logger.info(f'Raw Data file is created')
    else:
        logger.warning(f'Raw Data file is empty, please check...')

def get_credential(url, raw_file):
    if os.path.exists(raw_file):
        with open(raw_file, 'r') as f:
            try:
                old_list = json.load(f)
                old_cred = old_list[0][2] or old_list[1][2]
            except:
                old_cred = 'None'
                old_list = []
                logger.error(f"{raw_file} file is corrupted, please use 'CREATE' button to get a new HTML.")
    else:
        old_cred = 'None'
        old_list = []
        logger.error(f'Cannot find {raw_file} file, please generate a new html.')
    
    latest_list, latest_cred = get_link(url)
    return (old_cred, old_list, latest_cred, latest_list)
        
def generate_html(cred, list_name, queue):
    asyncio.run(check_link(list_name, cred, queue))

def main():
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    logger.info('Disabling SSL warning message during url requests')
    old_cred, old_list, latest_cred, latest_list = get_credential(url_RA, raw_file_name)
    
    if old_cred == latest_cred:
        compare_result = 'SAME'
        compare_color = 'yellow'
    else:
        compare_result = 'NOT SAME'
        compare_color = 'red'
        
    layout = [
        [sg.Text('Welcome to the ALB(Available Lab Box) tool', font=('Arial', 25))],
        [sg.Push()],
        [sg.Text('This tool is used to generate a available lab box links from', font=('Arial', 15))],
        [sg.Radio('https://phonebook.nexus.cec.delllabs.net/phonebook4', font=('Consolas', 11), group_id=1, default=True)],
        [sg.Radio('https://phonebook.nexus.cec.delllabs.net/phonebook', font=('Consolas', 11), group_id=2, default=True)],
        [sg.Push()],
        [sg.Push()],
        [sg.Push()],
        [sg.Text('Latest Credential:', font=('Arial', 13)), sg.Text(text=latest_cred, font=('Consolas', 12), text_color='blue'), 
         sg.VerticalSeparator(), sg.Text(text=compare_result, text_color=compare_color),
         sg.VerticalSeparator(), sg.Text('Last Credential:', font=('Arial', 13)), sg.Text(text=old_cred, font=('Consolas', 12), text_color='blue')],
        [sg.Push()],
        [sg.Push()],
        [sg.Push()],
        [sg.Frame('Button Function', 
                  [[sg.Text('CREATE', font=('Arial', 11)), sg.Text('  - will generate a new HTML from above websites', font=('Arial', 9))],
                   [sg.Text('REFRESH', font=('Arial', 11)), sg.Text('- refresh the old HTML with new Credential', font=('Arial', 9))],
                   [sg.Text('CANCEL', font=('Arial', 11)), sg.Text('  - exit the program', font=('Arial', 9))]])],
        [sg.Push()],
        [sg.Push()],
        [sg.Push(), sg.Button('CREATE', font=('Arial', 11), key='-CREATE-'), sg.Push(), sg.Button('REFRESH', font=('Arial', 11), key='-REFRESH-'), sg.Push(), sg.Button('CANCEL', font=('Arial', 11)), sg.Push()]
    ]

    window = sg.Window('ALB - Available Lab Box', layout=layout, element_padding=5, margins=(30, 20))
    queue = Queue()

    while True:
        event, values = window.read(timeout=100)
        if event == sg.WIN_CLOSED or event == 'CANCEL':
            break

        if not queue.empty():
            message = queue.get()
            if message[0] == 'progress':
                _, count, total_count = message
                sg.one_line_progress_meter('Checking available links', count, total_count, orientation='h', key='PROGRESSBAR')
            elif message[0] == 'done':
                html_list = message[1]
                html_table(html_list, latest_cred)
                sg.one_line_progress_meter_cancel('PROGRESSBAR')

        if event == '-CREATE-':
            threading.Thread(target=generate_html, args=(latest_cred, latest_list, queue), daemon=True).start()

        if event == '-REFRESH-':
            if old_list:
                if compare_result == 'SAME':
                    sg.popup(f"Credential <{latest_cred}> are latest! No need to do REFRESH", title='Warning', font=('Arial', 12))
                else:
                    threading.Thread(target=generate_html, args=(latest_cred, old_list, queue), daemon=True).start()
            else:
                sg.popup_error(f"{raw_file_name} NOT found or Corrupted, please use 'CREATE' button to get a new HTML!", title='ERROR MESSAGE', font=('Arial', 11))

    window.close()

if __name__ == '__main__':
    main()