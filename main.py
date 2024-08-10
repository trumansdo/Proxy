#!python3.9
# -*- encoding: utf-8 -*-
#coding:utf-8

import requests, re, yaml, time, base64
from re import Pattern
from typing import Any, Dict, List
from lxml import etree
from itertools  import chain
import urllib3
import os 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

rss_url:str = 'https://www.cfmem.com/feeds/posts/default?alt=rss'
clash_reg:Pattern = re.compile(r'clash.*(https?://\S+)')
v2ray_reg:Pattern = re.compile(r'V2Ray.*(https?://\S+)')

clash_output_file:str = './dist/clash.config.yaml'
clash_output_tpl:str = './clash.config.template.yaml'
v2ray_output_file:str = './dist/v2ray.config.txt'
    
clash_extra:List[str] = []

blacklist:List[str] = list(map(lambda l:l.replace('\r', '').replace('\n', '').split(':'), open('blacklists.txt',encoding='utf-8').readlines()))

def clash_urls(html:str) -> List[str]:
    '''
    Fetch URLs For Clash
    '''
    
    return list(chain(*filter(lambda y: len(y)>0,map(lambda x: clash_reg.findall(x.text),html)))) + clash_extra

def v2ray_urls(html:str) -> List[str]:
    '''
    Fetch URLs For V2Ray
    '''
    return list(chain(*filter(lambda y: len(y)>0,map(lambda x: v2ray_reg.findall(x.text),html)))) + clash_extra

def fetch_html(url:str) -> str:
    '''
    Fetch The Content Of url
    '''
    try:
        resp:requests.Response = requests.get(url, verify=False, timeout=10)
        if resp.status_code != 200:
            print(f'[!] Got HTTP Status Code {resp.status_code} When Requesting {url}')
            return '' 
        return resp.text
    except Exception as e:
        print(f'[-] Error Occurs When Fetching Content Of {url}: {e}')
        return ''

def merge_clash(configs:List[str]) -> str:
    '''
    Merge Multiple Clash Configurations
    '''
    config_template:Dict[str, Any] = yaml.safe_load(open(clash_output_tpl,encoding='utf-8').read())
    proxies:List[Dict[str, Any]] = []
    for i in range(len(configs)):
        tmp_config:Dict[str, Any] = yaml.safe_load(configs[i])
        if 'proxies' not in tmp_config: continue
        for j in range(len(tmp_config['proxies'])):
            proxy:Dict[str, Any] = tmp_config['proxies'][j]
            if any(filter(lambda p:p[0] == proxy['server'] and str(p[1]) == str(proxy['port']), blacklist)): continue
            if any(filter(lambda p:p['server'] == proxy['server'] and p['port'] == proxy['port'], proxies)): continue
            proxy['name'] = proxy['name'] + f'_{i}@{j}'
            proxies.append(proxy)
    node_names:List[str] = list(map(lambda n: n['name'], proxies))
    config_template['proxies'] = proxies
    for grp in config_template['proxy-groups']:
        if 'xxx' in grp['proxies']:
            grp['proxies'].remove('xxx')
            grp['proxies'].extend(node_names)

    return yaml.safe_dump(config_template, indent=1, allow_unicode=True)

def merge_v2ray(configs:List[str]) -> str:
    '''
    Merge Multiple V2Ray Configurations
    '''
    return os.linesep.join(configs)

def main():
    rss_html:str = fetch_html(rss_url)
    # rss_html:str = open(file='./rss.html',mode='r',encoding='utf-8').read()
    if rss_html is None or len(rss_html) <= 0: 
        print('[-] Failed To Fetch Content Of RSS')
        return
    rss_html = rss_html.replace("&amp;","&")
    rss_html = rss_html.replace("&lt;","<")
    rss_html = rss_html.replace("&gt;",">")
    rss_html = rss_html.replace("&nbsp;"," ")
    rss_html = rss_html.replace("&quot;",'"')
    span_list = etree.HTML(rss_html.encode('utf-8')).cssselect("h2 + div > div > span")
    clash_url_list:List[str] = clash_urls(span_list)
    v2ray_url_list:List[str] = v2ray_urls(span_list)
    print(f'[+] Got {len(clash_url_list)} Clash URLs, {len(v2ray_url_list)} V2Ray URLs')

    clash_configs:List[str] = [] 
    for u in clash_url_list:
        html:str = fetch_html(u)
        if html is not None and len(html) > 0: 
            clash_configs.append(html)
            print(f'[+] Configuration {u} Downloaded')
        else: 
            print(f'[-] Failed To Download Clash Configuration {u}')
        #time.sleep(0.1)
    v2ray_configs:List[str] = []
    for u in v2ray_url_list:
        html:str = fetch_html(u)
        if html is not None and len(html) > 0: 
            v2ray_configs.append(html)
            print(f'[+] Configuration {u} Downloaded')
        else: 
            print(f'[-] Failed To Download V2Ray Configuration {u}')
        #time.sleep(0.1)

    clash_merged:str = merge_clash(clash_configs)
    with open(clash_output_file, mode='w',encoding='utf-8') as f: f.write(clash_merged)

    v2ray_merged:str = merge_v2ray(v2ray_configs)
    with open(v2ray_output_file, mode='w',encoding='utf-8') as f: f.write(v2ray_merged)

if __name__ == '__main__':
    main()
