#!/usr/bin/env python3
# coding=utf-8

#-----------------------------------------------------------------------------
# Check following website for available Lab boxes which RA can be rcured
# https://vmahopprd01.isus.emc.com/artifactory/devops-tools-release/PhoneBook/phonebook_with_inline_window.htm
# 
# May 15 2024
#-----------------------------------------------------------------------------

# TODO: Get the title of the link --> generate a HTML like the orignal one
# TODO: Use AIOHTTP to speed up!

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import time

url1 = 'https://vmahopprd01.isus.emc.com/artifactory/devops-tools-release/PhoneBook/phonebook_with_inline_window.htm'

url = 'https://vmahopprd01.isus.emc.com/artifactory/devops-tools-release/PhoneBook/phonebook_V4_Simplified.htm'

links = []
avail_links = []

# From html to get all the links of lab boxes
response = requests.get(url, verify=False)
soup = BeautifulSoup(response.text, 'html.parser')
#print(soup.prettify())

for link in soup.find_all('a'):
    l = link.get('href')
    links.append(l)

#print(links)

# Deal with the links to find which one is available to access
# For RA acess
index = 0
while index < len(links):
    cur = links[index]

    try:
        r = requests.get(cur, verify=False, timeout=10)
        if r.status_code == requests.codes.OK:
            avail_links.append(cur)
        
        #print(avail_links)
            
    except:
        print(f'The box {cur[8:19]} failed to connect id{index}')

    if '9519' in cur:
        index += 9
    
    if '8888' in cur:
        index += 5

with open('links_ss', 'w') as f:
    for each in tqdm(avail_links):
        time.sleep(0.25)
        f.write(each+'\n')