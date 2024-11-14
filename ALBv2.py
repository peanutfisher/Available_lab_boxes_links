'''
Author: peanutfisher meifajia@outlook.com
Date: 2024-05-19 17:29:05
LastEditors: peanutfisher meifajia@outlook.com
LastEditTime: 2024-11-13 22:27:22
FilePath: \AvailableLabBox\test.py
'''
import logging
import requests
from lxml import etree
import urllib.parse
import re
from jinja2 import Environment, FileSystemLoader
import time
import os.path
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
raw_file_name = 'Raw_Data'

# Special handling for DTS boxes
dts_1162 = ['296801611M1', '10.60.35.245', 'VMAX100K', 'V3']
dts_2205 = ['220002205M1', '10.60.8.150', 'PMAX2500', 'V4']
dts_2206 = ['220002206M1', '10.60.8.156', 'PMAX2500', 'V4']
dts_0142 = ['220200142M1', '10.60.8.162', 'PMAX8500', 'V4']


    
# preset flags
cancelled_flag = False
test_flag = False
#test_flag = True

# defining the TYPE based on SN key num
SN_dict = {'202':'PMAX8500', '200':'PMAX2500', '976':'PMAX8000','979':'PMAX2000', '978':'VMAX250F', '977':'VMAX950F','975':'VMAX850F', '970':'VMAX450F', '972':'VMAX400K','967':'VMAX200K', '968':'VMAX100K'}

# defining the logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('app.log', 'w')

console_handler = logging.StreamHandler()
#console_handler.setLevel(logging.ERROR)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger.addHandler(file_handler)
logger.addHandler(console_handler)

file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# logger testing
logger.debug('this is debug information')
logger.info('this is info information')
logger.warning('this is warning information')
logger.error('this is error information')
logger.critical('this is critical information')


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
    cs1_ip = f'{ip_1}(CSControl)'
    cs2_ip = f'{ip_2}(CSControl)'

    if type == 'V4':
        dts_dict = dict(zip(['TYPE', 'RA_SN', 'RA', 'CS1_SN', 'CS2_SN'], [model, sn_1, ra_link, cs1_ip, cs2_ip]))
    else:
        dts_dict = dict(zip(['TYPE', 'RA_SN', 'RA', 'CS1_SN', 'CS2_SN'], [model, sn_1, ra_link, '', '']))
        
    
    if dts_dict:
        return dts_dict

def dts_array_list(credential):
    dts = []
    # create dict for each Sn and added to target list
    for each in [dts_1162, dts_2205, dts_2206, dts_0142]:
        result = dts_array_dict(each, credential)
        logger.debug(f'dts_dict: {result}')
        dts.append(result)
    
    if dts:
        return dts    
    
def read_html(html):
        with open(html, 'r') as f:
            return f.read()
        logger.info(f'reading {html} into cache...')

def get_link(url):
    try:
        if not test_flag:
            html = requests.get(url, verify=False, timeout=5).text
            #logger.debug(f'html content: {html}')
            logger.info(f'Connected to {url}')
        else:
            # for internal testing
            html = read_html('html_ra_sample.html')
        
        # use xpath to get all the table content from the website    
        links = etree.HTML(html).xpath('//tr')
        link_list = []
        for element in links:
            #logger.debug(element)
            # get all text from the table entry(each row had 12 entries)
            text = ["".join(td.itertext()).strip() for td in element.xpath('.//td')]
            
            #logger.debug(text)
            link_list.append(text)
        
        # delete empty one
        link_list = [entry for entry in link_list if entry]   
        #logger.debug(f'link_list: {link_list}')
        
        # get current CREDENTIAL
        cred = link_list[0][2] or link_list[1][2]
        logger.debug(f'Current CREDENTIAL: {cred}')
        
        # return the generated list and credential for next step
        return (link_list, cred)
        
    
    except Exception as e:
        logger.error(f'Can not connect to links: {url}, please check your Network connection and your VPN connection!!')
        logger.error('*********************************************************************************************************************')
        logger.error('Please close and retry after you fixed the network.')
        logger.error(str(e))
        sg.popup_error(f'Can not connect to links: {url}, please check your VPN Network connection!!', title='ERROR MESSAGE', font=('Arial', 11))
        return([],'None')

    

   
async def check_link(link_list, credential, queue, refresh_flag=False):

    """Check the item in the list and create a dict item for each SN, finally add them to a list.
    """
    global cancelled_flag
    
    # encode CREDENTIAL for web link(some special mark like +(%2B), /(%2F), etc. need to be encoded)
    web_credential = urllib.parse.quote(credential)
    
    # target list for html usage
    html_list = []
    
    # Prepare progress bar
    total_count = len(link_list)
    logger.info(f'There are total {total_count} items to be checked...')
    
    # Count for progress bar
    count = 0
    
    # Record valid links
    valid_count = 0
    
    # file to store raw item 
    raw_file = []

    # check each item in link_list
    for item in link_list:
        if cancelled_flag:
            break
        
        count += 1
        queue.put(('progress', count, total_count))

        # store the new dict value
        url_dict = {}
        
        # get each SN pattern from list and do RE search for model
        SN = item[1]
        link_RA = f'http://{SN}.storage.lab.emc.com:9519/login:{web_credential}:{PASSWORD}:SLC/remctrl_menu.html'
        link_SS = f'http://{SN}.storage.lab.emc.com:8888/toolbox/#/app?userName={web_credential}&password={PASSWORD}'
        
        # SN and link for CS2(V4)
        SN_2 = SN[:-1]+'2'
        link_SS_2 = f'http://{SN_2}.storage.lab.emc.com:8888/toolbox/#/app?userName={web_credential}&password={PASSWORD}'
        
        # Get the array model for each SN
        model = get_model(SN)
        
        if model:
            # Check if the SN belongs to V4, test the Simplified Symmiwin link if so.
            result_SS = False
            if model in {'PMAX8500', 'PMAX2500'}:
                if not refresh_flag:
                    result_SS = await test_link(link_SS)
                    logger.debug(f'result_SS: {result_SS}')
                else:
                    result_SS = True
            
            
            if not refresh_flag:
                # Test the RemoteAnywhere links no matter the SN is.
                result_RA = await test_link(link_RA)
            else:
                result_RA = True
            
            # add the valid item to raw file
            if result_RA or result_SS:
                item[2] = credential
                raw_file.append(item)
                # The links is valid so we increase the counter
                valid_count += 1
                logger.info(f'This is the {valid_count}th available link.')

                    
            
            if result_RA:
                logger.info(f'Found a available link for SN: {SN}')
                logger.debug(f'Found valid item: {item}')
                
                
                # store the new dict value, common part for both V3 and V4
                url_dict['COLOR'] = COLOR[valid_count % 2]
                url_dict['LABEL'] = item[0]
                url_dict['TYPE'] = model
                url_dict['Building'] = item[-5]
                url_dict['Lab'] = item[-4]
                url_dict['Tile'] = item[-3]
                url_dict['Owner'] = item[-2]
                url_dict['Group'] = item[-1]
                
                # RA links information
                url_dict['RA_SN'] = SN
                url_dict['RA'] = link_RA
                # default empty for V4
                url_dict['CS1_SN'] = ''
                url_dict['CS2_SN'] = ''
                url_dict['CS1'] = ''
                url_dict['CS2'] = ''
                
                # Add value for V4 boxes
                if result_SS:
                    url_dict['CS1_SN'] = SN
                    url_dict['CS2_SN'] = SN_2
                    url_dict['CS1'] = link_SS
                    url_dict['CS2'] = link_SS_2
            # A scenario is that RA not access but SS can be reached
            else:
                if result_SS:
                    logger.info(f'Found a available link for SN: {SN}')
                    logger.debug(f'Found valid item: {item}')
            
                
                    # store the new dict value, common part for both V3 and V4
                    url_dict['COLOR'] = COLOR[count % 2]
                    url_dict['LABEL'] = item[0]
                    url_dict['TYPE'] = model
                    url_dict['Building'] = item[-5]
                    url_dict['Lab'] = item[-4]
                    url_dict['Tile'] = item[-3]
                    url_dict['Owner'] = item[-2]
                    url_dict['Group'] = item[-1]
                    # values for V4
                    url_dict['CS1_SN'] = SN
                    url_dict['CS2_SN'] = SN_2
                    url_dict['CS1'] = link_SS
                    url_dict['CS2'] = link_SS_2 
                    # RA links empty
                    url_dict['RA_SN'] = ''
                    url_dict['RA'] = ''
                else:
                    logger.warning(f'No available lab box links found for {SN}!')
                            
            
                
            if url_dict:
                html_list.append(url_dict)
                #logger.debug(f'url_dict: {url_dict}')

    if not cancelled_flag:
        #logger.debug(f'html_list: {html_list}')
        logger.info('HTML list created')
        
        
        # Created Raw file for refresh using
        #logger.debug(f'raw_file:{raw_file}')
        write_file(raw_file)

        #return html_list
        queue.put(('done', html_list))
        
        

def get_model(sn):
    model = ''
    for sn_pattern in SN_dict.keys():
            p = re.compile('\d'+ sn_pattern + '\d+M\d')
            #logger.debug(f'Matching patter: {p}')
            result = p.search(sn)
            # if result found then create the dict and stop this tier for loop
            if result:
                model = SN_dict[sn_pattern]
                logger.debug(f'SN: {sn}, Model: {model}')
                
                # set a flag for jump out for loop if we found a valid entry
                break
    
    return model            
    

async def test_link(link):
    try:        
        # set the connection timeout for each URL detection
        timeout = ClientTimeout(total=18)
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), timeout=timeout) as session:
        #async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                status = response.status
                if status == 200:
                    logger.debug(f'reachable url: {link}')
                    return True
    except:
        logger.warning(f'unreachable url: {link}')
        return False

def html_table(data, dts_data, cred):
    global Cur_Time
    global PASSWORD
    logger.info('Creating HTML table')
    # Get current time as part of filename
    ctime = time.localtime()
    Cur_Time = time.strftime("%Y%m%d%H%M", ctime)
    web_time = time.strftime("%H:%M:%S %m/%d/%Y", ctime)
    
        
    if data:
        # The template location
        file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))

        # create env
        env = Environment(loader = file_loader)

        # loading template
        template = env.get_template('template.html')

        # render the template
        output = template.render(url_list=data, dts_list=dts_data, generated_time=web_time, credential=cred, password=PASSWORD)
        #logger.debug(f'Template output: {output}')
        
        
        filename = 'Available_Lab_boxes ' + Cur_Time + '.html'
        
        # Write html file
        with open(filename, 'w') as f:
            f.write(output)
        
        logger.info(f'{filename} is created under current directory, please check')
        
        
        sg.popup(f'Done! The {filename} is created, Click OK to open it in your browser')
        
        # Open the html with default browser
        cur_dir = os.getcwd()
        html_path = os.path.join(cur_dir, filename)
        webbrowser.open('file://' + html_path)
    
    else:
        logger.warning(f'URL LINK list {data} not available...check check now')
        sg.popup_error(f'Cannot generate HTML, please check your VPN connection and retry!!', title='ERROR MESSAGE', font=('Arial', 11))

def write_file(listname):
    
    if listname:
        # dump the list to json file        
        with open('Raw_Data', 'w') as f:
            json.dump(listname, f, ensure_ascii=False, indent=4)
        
        logger.info(f'Raw Data file is created')
    else:
        logger.warning(f'Raw Data file is empty, please check...')

def get_credential(url, raw_file):
    """Used to generate a latest Credential from web and generate a new html with latest credential"""
    if os.path.exists(raw_file):
        with open(raw_file, 'r') as f:
            try:
                old_list = json.load(f)
                #logger.debug(f'Loading list from {raw_file}: {old_list}')
                
                # get last CREDENTIAL
                old_cred = old_list[0][2] or old_list[1][2]
                logger.debug(f'Last CREDENTIAL: {old_cred}')
            
            except:
                old_cred = 'None'
                old_list = []
                logger.error(f"{raw_file} file is corrupted, please use 'CREATE' button to get a new HTML.")
                
        
    else:
        old_cred = 'None'
        old_list = []    
        logger.error(f'Cannot find {raw_file} file, please generate a new html.')
        
        
    # get latest CREDENTIAL
    latest_list, latest_cred = get_link(url)
    logger.debug(f'Latest CREDENTIAL: {latest_cred}')
    
    if old_cred == latest_cred:
        compare_result = 'SAME'
        compare_color = 'yellow'
        tooltip_msg = 'Latest Credential! Nothing to do :)'
    else:
        compare_result = 'NOT SAME'
        compare_color = 'red'
        tooltip_msg = 'Credential Changed! REFRESH or CREATE depends on you :>'
        
    # return those cred and list for next action
    return (old_cred, old_list, latest_cred, latest_list, compare_result, compare_color, tooltip_msg)
        
def coroutine_task(cred, list_name, queue, refresh_flag):
    """Used to run coroutine task for check_link function"""
    asyncio.run(check_link(list_name, cred, queue, refresh_flag))
    
    # start_time = time.time()
    
    # html_list = await check_link(list_name, cred)
    # html_table(html_list, cred)
    
    # took_time = time() - start_time
    # logger.info(f'It took about {took_time}s to complete the job')
 
         
def main():
    global cancelled_flag 
    # Disable the warning for SSL
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    logger.info('Disabling SSL warning message during url requests')
    
    old_cred, old_list, latest_cred, latest_list, compare_result, compare_color, tooltip_msg = get_credential(url_RA, raw_file_name)
    logger.debug(f'old_cred: {old_cred}, old_list: {old_list}, latest_cred: {latest_cred}, \
                 compare_result: {compare_result}, compare_color: {compare_color}') 
    

    # GUI part - PySimpleGUI
    layout = [
        [sg.Text('Welcome to the ALB(Available Lab Box) tool', font=('Arial', 25))],
        [sg.Push()],
        [sg.Text('This tool is used to generate a available lab box links from', font=('Arial', 15))],
        [sg.Radio('https://phonebook.nexus.cec.delllabs.net/phonebook4', font=('Consolas', 11), group_id=1, default=True)],
        [sg.Radio('https://phonebook.nexus.cec.delllabs.net/phonebook', font=('Consolas', 11), group_id=2, default=True)],
        [sg.Push()],
        [sg.Push()],
        [sg.Push()],
        
        [sg.Push(), sg.Text('Latest Credential:', font=('Arial', 13)), sg.Text(text=latest_cred, key='-LATEST-', font=('Consolas', 12), text_color='blue'), 
            sg.VerticalSeparator(),
            sg.Text(text=compare_result, key='-COMPARE-', text_color=compare_color, tooltip=tooltip_msg),
            sg.VerticalSeparator(),
            sg.Text('Last Credential:', font=('Arial', 13)), sg.Text(text=old_cred, key='-LAST-', font=('Consolas', 12), text_color='blue'),
            sg.Push()],
        
        [sg.Push()],
        [sg.Push()],
        [sg.Push()],
        [sg.Push(), sg.Frame('Button Function', 
            [[sg.Text('CREATE', font=('Arial', 11)), sg.Text('  - will generate a new HTML from above websites', font=('Arial', 9))],
            [sg.Text('REFRESH', font=('Arial', 11)), sg.Text('- refresh the old HTML with new Credential', font=('Arial', 9))],
            [sg.Text('CANCEL', font=('Arial', 11)), sg.Text('  - exit the program', font=('Arial', 9))]]), sg.Push()],
        
        [sg.Push()],
        [sg.Push()],
        
        [sg.Push(), sg.Button('CREATE', font=('Arial', 11), key='-CREATE-'),sg.Push(), sg.Button('REFRESH', font=('Arial', 11), key='-REFRESH-'), sg.Push(), sg.Button('CANCEL', font=('Arial', 11)), sg.Push()]
    ]
    
    window = sg.Window('ALB - Available Lab Box', layout=layout, element_padding=5, margins=(30, 20))
    queue = Queue()
    
    
    while True:
        event, values = window.read(timeout=100)
        if event == sg.WIN_CLOSED or event == 'CANCEL':
            break
        
        if not cancelled_flag:
            if not queue.empty():
                message = queue.get_nowait()
                logger.debug(f'message: {message}')
                if message[0] == 'progress':
                    _, count, total_count = message
                    pbar = sg.one_line_progress_meter('Checking available links', count, total_count, orientation='h', key='PROGRESSBAR')
                    # if user cancel the progress bar
                    if not pbar:
                        cancelled_flag = True
                        sg.one_line_progress_meter_cancel('PROGRESSBAR')
                        logger.warning('User cancel the CREATE action, progress bar closed!')
                        sg.popup('CREATE action is cancelled!', title='Warning', font=('Arial', 12))
                        
                
                elif message[0] == 'done':
                    html_list = message[1]
                    sg.one_line_progress_meter_cancel('PROGRESSBAR')
                    dts_data = dts_array_list(latest_cred)

                    # generate html table
                    html_table(html_list, dts_data, latest_cred)
                    
                    old_cred, old_list, latest_cred, latest_list, compare_result, compare_color, tooltip_msg = get_credential(url_RA, raw_file_name)
                    # update the credential values
                    window['-LATEST-'].update(latest_cred)
                    window['-LAST-'].update(latest_cred)
                    window['-COMPARE-'].update(value=compare_result, text_color=compare_color)
                
            
        if event == '-CREATE-':
            # reset cancel flag to False
            cancelled_flag = False
            
            logger.info('CREATE button clicked...')
            
            # empty current queue
            queue = Queue()
            # check if we got latest list
            if not latest_list:
                old_cred, old_list, latest_cred, latest_list, compare_result, compare_color, tooltip_msg = get_credential(url_RA, raw_file_name)
            
            if latest_list:
                threading.Thread(target=coroutine_task, args=(latest_cred, latest_list, queue, False), daemon=True).start()

            
        if event == '-REFRESH-':
            cancelled_flag = False
            logger.info('REFRESH button clicked...')
            
            # empty current queue
            queue = Queue()
            # check if we got latest list and latest credential
            if not latest_list:
                old_cred, old_list, latest_cred, latest_list, compare_result, compare_color, tooltip_msg = get_credential(url_RA, raw_file_name)
            
            if latest_list:
                # check if Raw_Data exists
                if old_list:
                    if compare_result == 'SAME':
                        sg.popup(f"Credential <{latest_cred}> are latest! No need to do REFRESH", title='Warning', font=('Arial', 12))
                    else:
                        threading.Thread(target=coroutine_task, args=(latest_cred, old_list, queue, True), daemon=True).start()

                else:
                    sg.popup_error(f"{raw_file_name} NOT found or Corrupted, please use 'CREATE' button to get a new HTML!", title='ERROR MESSAGE', font=('Arial', 11))

    window.close()
    
    
    
if __name__ == '__main__':
    main()

