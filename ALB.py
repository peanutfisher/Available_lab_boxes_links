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
#-----------------------------------------------------------------------------



import requests
#from bs4 import BeautifulSoup
from lxml import etree
from tqdm import tqdm
import time
import re
import os
import asyncio
import aiohttp
import func_html

url_RA = 'https://vmahopprd01.isus.emc.com/artifactory/devops-tools-release/PhoneBook/phonebook_with_inline_window.htm'

url_SS = 'https://vmahopprd01.isus.emc.com/artifactory/devops-tools-release/PhoneBook/phonebook_V4_Simplified.htm'

SS_patern = ':8888'
RA_patern = ':9519'

SS_list = []
RA_list = []


async def check_link(url, listname):
    # From html to get all the links of lab boxes
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), conn_timeout=10) as session:
            async with session.get(url) as response:
                status = response.status

                # put available links into corresponding list
                if status == 200:
                    listname.append(url)

                         


    except:
        #print(f'Failed to connect URL: {url}')
        pass

def write_file(listname):
    if SS_patern in listname[0]:
        filename = 'SS_links'
    else:
        filename = 'RA_links'
    
    with open(filename, 'w') as f:
        for line in listname:
            f.write(line+'\n')
    print(f'{filename} is created')

async def get_link(html, listname):
    # use xpath to get all the hyper link from the website    
    links = etree.HTML(html).xpath('//td/a/@href')
    
    url_count = len(links)
    #print(f'{url_count} urls need to be processed...')
    
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
        #print(cur_url)
        await check_link(cur_url, listname)
        
        #print(f'Processing {count} urls')
        count += 1
        pbar.update(1)
        
    pbar.close()

        

def read_html(html):
        with open(html, 'r') as f:
            return f.read()

async def main():
    global SS_list
    global RA_list
    html_RA = requests.get(url_RA, verify=False, timeout=5).text
    html_SS = requests.get(url_SS, verify=False, timeout=5).text
    
    # html_RA = read_html('html_ra_sample.html')
    # html_SS = read_html('html_ss_sample.html')
    
    # loop = asyncio.get_event_loop()
    # try:
    #     tasks = [get_link(html_RA, RA_list), get_link(html_SS, SS_list)]
        
    #     loop.run_until_complete(asyncio.wait(tasks))
    # finally:
    #     if not loop.is_closed():
    #         loop.close()

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

    url_list = func_html.url_to_dict(SS_list, RA_list) + func_html.url_to_dict(RA_list)
    func_html.html_table(url_list)


if __name__ == '__main__':
    try:
        start = time.time()
        asyncio.run(main())
        
    except RuntimeError as e:
        print(f'Ignoring runtime error, content as {e}')
    finally:
        print(f'Took {time.time() - start}s to finish the job')
