#!/usr/bin/env python3
# coding=utf-8

#-----------------------------------------------------------------------------
# Check following website for available Lab boxes which RA can be reached
# https://vmahopprd01.isus.emc.com/artifactory/devops-tools-release/PhoneBook/phonebook_with_inline_window.htm
# 
# May 15 2024
# starting the program...a
# TODO: Get the title of the link --> generate a HTML like the orignal one
# TODO: Use AIOHTTP to speed up!
#
# Sep 12 2024
# Back from procrastination...
# TODO: url_RA included 96% of url_SS website(4% is CS2 connection), consider using just url_RA for better speed
# TODO: Using Jinjia2 template to create the table in html 
# 
# # Sep 16 2024
# The whole function has almost finished, now just adjust a little bit
# 
# # Sep 19 2024
# Packing it into a exe
#-----------------------------------------------------------------------------


import func_html

import requests
from lxml import etree
from tqdm import tqdm
import time
import re
import os
import asyncio
import aiohttp
from aiohttp import ClientTimeout
import logging
import msvcrt




url_RA = 'https://vmahopprd01.isus.emc.com/artifactory/devops-tools-release/PhoneBook/phonebook_with_inline_window.htm'

url_SS = 'https://vmahopprd01.isus.emc.com/artifactory/devops-tools-release/PhoneBook/phonebook_V4_Simplified.htm'

SS_patern = ':8888'
RA_patern = ':9519'

SS_list = []
RA_list = []

# initializing Logging module
logging.basicConfig(
    filename='app.log',
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG
)


async def check_link(url, listname):
    # From html to get all the links of lab boxes
    try:
        # set the connection timeout 10s for each URL detection
        timeout = ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), timeout=timeout) as session:
            async with session.get(url) as response:
                status = response.status

                # put available links into corresponding list
                if status == 200:
                    listname.append(url)
                    logging.debug(f'reachable url: {url}')
                    
    except:
        logging.debug(f'unreachable url: {url}')
        

def write_file(listname):
    if listname:
        if SS_patern in listname[0]:
            filename = 'SS_links'
        else:
            filename = 'RA_links'
        
        with open(filename, 'w') as f:
            for line in listname:
                f.write(line+'\n')
        
        logging.info(f'{filename} raw file is created')
    else:
        logging.warning(f'{listname} is empty, please check...')

async def get_link(html, listname):
    # use xpath to get all the hyper link from the website    
    links = etree.HTML(html).xpath('//td/a/@href')
    
    url_count = len(links)
    logging.info(f'{url_count} urls need to be processed...')
    
    index = 0
    # count for how many urls
    count = 1
    
    # create a progress bar
    pbar = tqdm(total=url_count)
    
    # traversing the links to find available links and sorted them 
    while index < url_count:
        cur_url = links[index]
        # for url_SS links
        if SS_patern in cur_url:
            pbar.set_description('Checking Simplified Symmwin links')
            if 'M1.storage' in cur_url:
                index += 2
                pbar.update(1)
            if 'M2.storage' in cur_url:
                index +=3
                pbar.update(2)
        
        # for url_RA links:
        if RA_patern in cur_url:
            pbar.set_description('Checking Remote Anywhere links')
            index += 9
            pbar.update(8)
        
        logging.debug(f'available url: {cur_url}')
        
        await check_link(cur_url, listname)
        
        logging.info(f'Processing {count} urls')
        count += 1
        pbar.update(1)
        
    pbar.close()

        

def read_html(html):
        with open(html, 'r') as f:
            return f.read()
        logging.info(f'reading {html} into cache...')

def exit_program():
    print('Press any key to exit...')
    msvcrt.getch()

async def main():
    global SS_list
    global RA_list
    
    
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    logging.info('Disabling SSL warning message during url requests')
    
    try:
        html_RA = requests.get(url_RA, verify=False, timeout=5).text
        logging.debug(f'html_RA content: {html_RA}')
        logging.info(f'Connecting to {url_RA}')
        
        html_SS = requests.get(url_SS, verify=False, timeout=5).text
        logging.debug(f'html_SS content: {html_SS}')
        logging.info(f'Connecting to {url_RA}')
    
    except Exception as e:
        logging.error(f'Can not connect to Lab links: {url_RA} and {url_SS}, please check your Network connection and your VPN connection!!')
        logging.error('*********************************************************************************************************************')
        logging.error('Please close and retry after you fixed the network.')
        logging.error(str(e))
        exit_program()

        
    # # for internal testing
    # html_RA = read_html('html_ra_sample.html')
    # html_SS = read_html('html_ss_sample.html')

    # combine the asyncio task into one
    await asyncio.gather(
        get_link(html_RA, RA_list), 
        get_link(html_SS, SS_list)
    )
    
    # Sort the list to give a better view
    RA_list = sorted(RA_list)
    SS_list = sorted(SS_list)

    # write the available links to the files
    write_file(SS_list)
    write_file(RA_list)

    # Creating the html table
    url_list = func_html.url_to_dict(SS_list, RA_list) + func_html.url_to_dict(RA_list)
    logging.debug(f'The content of url list is {url_list}')
    
    func_html.html_table(url_list)
    
    logging.info(f'main() run successfully')


if __name__ == '__main__':

    start = time.time()
    
    # Change the event loop to Selector type to avoid "Event loop is closed" error, per link: https://www.cnblogs.com/james-wangx/p/16111485.html
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

    print(f'Took {time.time() - start}s to finish the job')
    
    # waiting for user's decision to exit program
    exit_program()
    
    logging.info(f'Took {time.time() - start}s to finish the job')

