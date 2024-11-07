'''
Author: peanutfisher meifajia@outlook.com
Date: 2024-05-19 17:29:05
LastEditors: peanutfisher meifajia@outlook.com
LastEditTime: 2024-11-07 14:46:00
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
from tqdm import tqdm
import aiohttp
from aiohttp import ClientTimeout
import asyncio
import PySimpleGUI as sg
import webbrowser

url_RA = 'https://phonebook.nexus.cec.delllabs.net/phonebook'

url_SS = 'https://phonebook.nexus.cec.delllabs.net/phonebook4'


PASSWORD = '1nternal'
Cur_Time = ''
COLOR = ['silver', 'lime']
raw_file = []
raw_file_name = 'Raw_Data'

# defining the TYPE based on SN key num
SN_dict = {'202':'PMAX8500', '200':'PMAX2500', '976':'PMAX8000','979':'PMAX2000', '978':'VMAX250F', '977':'VMAX950F','975':'VMAX850F', '970':'VMAX450F', '972':'VMAX400K','967':'VMAX200K', '968':'VMAX100K'}

# defining the logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('test.log', 'w')

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

def read_html(html):
        with open(html, 'r') as f:
            return f.read()
        logger.info(f'reading {html} into cache...')

def get_link(url):
    # try:
    #     html = requests.get(url, verify=False, timeout=5).text
    #     logger.debug(f'html content: {html}')
    #     logger.info(f'Connected to {url}')
        
    
    # except Exception as e:
    #     logger.error(f'Can not connect to links: {url}, please check your Network connection and your VPN connection!!')
    #     logger.error('*********************************************************************************************************************')
    #     logger.error('Please close and retry after you fixed the network.')
    #     logger.error(str(e))
    #     #exit_program()

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
    logger.debug(f'link_list: {link_list}')
    
    # get current CREDENTIAL
    cred = link_list[0][2] or link_list[1][2]
    logger.debug(f'Current CREDENTIAL: {cred}')
    
    # return the generated list and credential for next step
    return (link_list, cred)

   
async def check_link(link_list, credential):

    """Check the item in the list and create a dict item for each SN, finally add them to a list.
    """

    # encode CREDENTIAL for web link(some special mark like +(%2B), /(%2F), etc. need to be encoded)
    web_credential = urllib.parse.quote(credential)
    
    # target list for html usage
    html_list = []
    
    # Prepare progress bar
    total_count = len(link_list)
    logger.info(f'There are total {total_count} items to be checked...')
    pbar = tqdm(total=total_count)
    
    count = 0
    # check each item in link_list
    for item in link_list:
        pbar.update(1)
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
        
        # Check if the SN belongs to V4, test the Simplified Symmiwin link if so.
        result_SS = False
        if model in {'PMAX8500', 'PMAX2500'}:
            result_SS = await test_link(link_SS)
            logger.debug(f'result_SS: {result_SS}')
        

        # Test the RemoteAnywhere links no matter the SN is.
        result_RA = await test_link(link_RA)
        
        if result_RA or result_SS:
            raw_file.append(item)

                
        
        if result_RA:
            logger.info(f'Found a available link for SN: {SN}')
            logger.debug(f'Found valid item: {item}')
            
            count += 1
            logger.debug(f'Found {count} valid entries')
            
            # store the new dict value, common part for both V3 and V4
            url_dict['COLOR'] = COLOR[count % 2]
            url_dict['LABEL'] = item[0]
            url_dict['SN'] = SN
            url_dict['TYPE'] = model
            url_dict['RA'] = link_RA
            url_dict['Building'] = item[-5]
            url_dict['Lab'] = item[-4]
            url_dict['Tile'] = item[-3]
            url_dict['Owner'] = item[-2]
            url_dict['Group'] = item[-1]
            # default empty for V3
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
            
                count += 1
                logger.debug(f'Found {count} valid entries')
            
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
                pass
                #logger.error('No available lab box links found!')
                         
                
            
        if url_dict:
            html_list.append(url_dict)
            logger.debug(f'url_dict: {url_dict}')
    
    logger.debug(f'html_list: {html_list}')
    
    # Close progress bar
    pbar.close()
    
    # Created Raw file for refresh using
    logger.debug(f'raw_file:{raw_file}')
    write_file(raw_file)

    return html_list 

def get_model(sn):
    model = ''
    for sn_pattern in SN_dict.keys():
            p = re.compile('\d'+ sn_pattern + '\d+M\d')
            logging.debug(f'Matching patter: {p}')
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
        # response = requests.get(link, verify=False, timeout=4)
        # if response.status_code == 200:
        #     logger.info(f'reachable url: {link}')
        
        # set the connection timeout 10s for each URL detection
        timeout = ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), timeout=timeout) as session:
        #async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                status = response.status

                # put available links into corresponding list
                if status == 200:
                    logging.debug(f'reachable url: {link}')
        return True
    except:
        logger.warning(f'unreachable url: {link}')
        return False

def html_table(data, cred):
    global Cur_Time
    global PASSWORD
    
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
        output = template.render(url_list=data, generated_time=web_time, credential=cred, password=PASSWORD)
        #logger.debug(f'Template output: {output}')
        
        
        filename = 'Available_Lab_boxes ' + Cur_Time + '.html'
        
        # Write html file
        with open(filename, 'w') as f:
            f.write(output)
        
        logging.info(f'{filename} is created under current directory, please check')
        
        # Open the html with default browser
        cur_dir = os.getcwd()
        html_path = os.join(cur_dir, filename)
        webbrowser.open('file://' + html_path)
    
    else:
        logging.warning(f'URL LINK list {data} not available...check check now')

def write_file(listname):
    if listname:
        # dump the list to json file        
        with open('Raw_Data', 'w') as f:
            json.dump(listname, f, ensure_ascii=False, indent=4)
        
        logging.info(f'Raw Data file is created')
    else:
        logging.warning(f'Raw Data file is empty, please check...')

def get_credential(url, raw_file):
    """Used to generate a latest Credential from web and generate a new html with latest credential"""
    if os.path.exists(raw_file):
        with open(raw_file, 'r') as f:
            try:
                old_list = json.load(f)
                logger.debug(f'Loading list from {raw_file}: {old_list}')
                
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
    
    # return those cred and list for next action
    return (old_cred, old_list, latest_cred, latest_list)
        
async def generate_html(cred, list_name):
    """Used to generate a latest Credential from web and generate a new html with latest credential"""
    html_list = await check_link(list_name, cred)
    html_table(html_list, cred)
 
         
async def main():   
    # Disable the warning for SSL
    
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    logger.info('Disabling SSL warning message during url requests')
    
    old_cred, old_list, latest_cred, latest_list = get_credential(url_RA, raw_file_name)
    logger.debug(f'old_cred: {old_cred}, old_list: {old_list}, latest_cred: {latest_cred}, latest_list: {latest_list}')
    if old_cred == latest_cred:
        compare_result = 'SAME'
        compare_color = 'yellow'
    else:
        compare_result = 'NOT SAME'
        compare_color = 'red'
    
    
    # GUI part - PySimpleGUI
    layout = [
        [sg.Text('Welcome to the ALB(Available Lab Box) tool', font=('Arial', 25))],
        [sg.Push()],
        [sg.Text('This tool is used to generate a available lab box links from', font=('Arial', 15))],
        [sg.Radio('https://phonebook.nexus.cec.delllabs.net/phonebook4', font=('Consolas', 11), group_id=1, default=True)],
        [sg.Radio('https://phonebook.nexus.cec.delllabs.net/phonebook', font=('Consolas', 11), group_id=2, default=True)],
        [sg.Push()],
        [sg.Push()],
        
        [sg.Text('Latest Credential:', font=('Arial', 13)), sg.Text(text=latest_cred, font=('Consolas', 12), text_color='blue'), 
            sg.VerticalSeparator(),
            sg.Text(text=compare_result, text_color=compare_color),
            sg.VerticalSeparator(),
            sg.Text('Last Credential:', font=('Arial', 13)), sg.Text(text=old_cred, font=('Consolas', 12), text_color='blue')],
        
        [sg.Push()],
        [sg.Push()],
        
        [sg.Frame('Button Function', 
            [[sg.Text('CREATE', font=('Arial', 11)), sg.Text('  - will generate a new HTML from above websites', font=('Arial', 9))],
            [sg.Text('REFRESH', font=('Arial', 11)), sg.Text('- refresh the old HTML with new Credential', font=('Arial', 9))],
            [sg.Text('CANCEL', font=('Arial', 11)), sg.Text('  - exit the program', font=('Arial', 9))]])],
        
        [sg.Push()],
        [sg.Push()],
        
        [sg.Push(), sg.Button('CREATE', font=('Arial', 11), key='-CREATE-'),sg.Push(), sg.Button('REFRESH', font=('Arial', 11), key='-REFRESH-'), sg.Push(), sg.Button('CANCEL', font=('Arial', 11)), sg.Push()]
    ]
    window = sg.Window('ALB - Available Lab Box', layout=layout, element_padding=5, margins=(30, 20))
    
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'CANCEL':
            break
        
        if event == '-CREATE-':
            await generate_html(latest_cred, latest_list)

        if event == '-REFRESH-':
            if old_list:
                if compare_result == 'SAME':
                    sg.popup(f"Credential {latest_cred} are latest! No need to do REFRESH", title='Warning', font=('Arial', 11))
                else:
                    await generate_html(latest_cred, old_list)
            else:
                sg.popup_error(f"{raw_file_name} NOT found or Corrupted, please use 'CREATE' button to get a new HTML!", title='ERROR MESSAGE', font=('Arial', 11))
            
    
    
    window.close()
    
    
    
if __name__ == '__main__':
    asyncio.run(main())
