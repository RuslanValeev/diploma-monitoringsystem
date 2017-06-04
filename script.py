#!/usr/bin/env python
# -*- coding: utf-8 -*- 
"""
Code to analyze squid log file
"""                          
from __future__ import division
import gzip
import time
import sys
import operator
import requests
import urllib
import re
from bs4 import BeautifulSoup

reload(sys)  
sys.setdefaultencoding('utf8')

_time_format = "%d %b %Y %H:%M:%S"    

keywords = ['Фурье', 'Коши', 'математика', 'коши']
patterns = {'search-engines': ['yandex', 'rambler', 'google', 'mail', 'aport', 'yahoo'],
            'entertainment': ['pikabu', 'youtube', 'igromania'],
            'encyclopedia': ['wikipedia']}

learning_resourses = {}

class SquidLogLine(object):
    """
    Parse Squid log line enty
    """ 
    fields = ['ts', 'elapsed', 'remhost', 'status', 'bytes', 'method', 'url', 'rfc931', 'peerstatus', 'type']  

    def __init__(self, line, print_human_times=False, print_minimal=False):
        """setup fields""" 
        self._print_human_times = print_human_times 
        self._print_minimal = print_minimal 
        try:                                        
            map( lambda k,v: setattr(self, k, v), SquidLogLine.fields, line.split() )
        except TypeError:
            l = line.split()
            l = l[:6] + [''.join(l[6:-3])] + l[-3:]
            map( lambda k,v: setattr(self, k, v), SquidLogLine.fields, l )
        self.client = self.remhost
        try:
            self.ts = float(self.ts)  
        except TypeError, e:
            if self.ts == None:
                pass
            else:
                raise e
        
    def __str__(self):   
        if self._print_human_times:
            s = "%s " % time.strftime(_time_format, time.localtime(self.ts))
        else:
            s = "%s " % self.ts 
        if self._print_minimal: 
            s += "%s %s %s %s %s" % (self.remhost, self.status[-3:], self.method, self.url, self.type)
        else:
            for k in SquidLogLine.fields[1:]:
                s += "%s " % getattr(self, k)
            s = s[:-1]
        return s
                
class SquidLog(object):
    """
    Reading Squid log file
    """
    def __init__(self, f, print_human_times = False, print_minimal=False): 
        if type(f) == type(str()):
            try:      
                self.f = gzip.open(f) 
                self.f.next()
                self.f.rewind()
            except IOError, e:         
                self.f = open(f)
            except StopIteration, e:
                pass
        else:
            self.f = f
        self._print_human_times = print_human_times 
        self._print_minimal = print_minimal
            
    def __iter__(self):
        """iterator creator"""
        return self
        
    def next(self):
        """returns next line from the logs"""
        line = self.f.next()
        return SquidLogLine( line, print_human_times=self._print_human_times, print_minimal=self._print_minimal )
        
    def close(self):
        """close fh"""
        self.f.close()

def get_links(log):
    counts_log = {}
    users_log = {}
    for l in log:
        if l.type == "-":
            if l.url[0:15] == 'www.youtube.com' or l.url[0:14] == 'www.google.com' or l.url[0:16] == 'ru.wikipedia.org':
                if l.method == "CONNECT":
                    vhost = (l.url).split(':')[0]
                else:
                    try:
                        vhost = (l.url).split("/")[2]
                    except IndexError:
                        continue
                if l.remhost in users_log:
                    users_log[l.remhost].append("http://" + vhost)
                else:
                    users_log[l.remhost] = ["http://" + vhost]

                if l.remhost in counts_log:
                    if vhost in counts_log[l.remhost]:
                        counts_log[l.remhost][vhost] = counts_log[l.remhost][vhost] + 1
                    else:
                        counts_log[l.remhost][vhost] = 1
                else:
                    counts_log[l.remhost] = {}
                    counts_log[l.remhost][vhost] = 1

        if l.type == "text/html":
            if l.url[-1] == '/' or l.url[-5:] == '.html' or l.url[-4:] == '.htm' or l.url[-4:] == '.php' or l.url[-3] == '%' or l.url[-1].isdigit():
                if l.method == "CONNECT":
                    vhost = (l.url).split(':')[0]
                else:
                    try:
                        vhost = (l.url).split("/")[2]
                    except IndexError:
                        continue
                if vhost.count('.') < 2 or vhost[0:3] == 'www':
                    if l.remhost in users_log:
                        users_log[l.remhost].append(l.url)
                    else:
                        users_log[l.remhost] = [l.url]
                    if l.remhost in counts_log:
                        if vhost in counts_log[l.remhost]:
                            counts_log[l.remhost][vhost] = counts_log[l.remhost][vhost] + 1
                        else:
                            counts_log[l.remhost][vhost] = 1
                    else:
                        counts_log[l.remhost] = {}
                        counts_log[l.remhost][vhost] = 1
    return counts_log, users_log


def check_url_keywords(user, url, keywords):
    """check keyword's in the page body"""
    html = urllib.urlopen(url).read()
    soup = BeautifulSoup(html, 'html.parser')
    [s.extract() for s in soup(['style', 'script', '[document]'])]
    text = soup.getText()    
    for word in keywords:
        if word in text:
            print "Я нашел ключевое слово " + str(word) + " на сайте " + url
            if user in learning_resourses:
                if 'learning' in learning_resourses[user]:
                    if url not in learning_resourses[user]['learning']:
                        learning_resourses[user]['learning'].append(url)
                else:
                    learning_resourses[user]['learning'] = [url]
            else:
                learning_resourses[user] = {}
                learning_resourses[user]['learning'] = [url]


def check_url_patterns(user, url, patterns):
    """check pattern's in the url"""
    for category in patterns:
        for word in patterns[category]:
            if word in url:
                print "Я нашел url паттерна " + str(word) + " на сайте " + url
                if user in learning_resourses:
                    if category in learning_resourses[user]:
                        if url not in learning_resourses[user][category]:
                            learning_resourses[user][category].append(url)
                    else:
                        learning_resourses[user][category] = [url]
                else:
                    learning_resourses[user] = {}
                    learning_resourses[user][category] = [url]

def frequency_analysis(frequency_dict):
    """count total frequency"""
    total_visit = 0
    total_frequency = {}
    for user in frequency_dict:
        for link in frequency_dict[user]:
            total_visit += frequency_dict[user][link]
    for user in frequency_dict:
        for link in frequency_dict[user]:
            total_frequency[link] = round(frequency_dict[user][link] / total_visit, 2)
    return total_frequency


def analyze_links(data_log):
    """analyze all links"""
    for user in data_log:
        already_visited = []
        for url in data_log[user]:
            if url not in already_visited:
                check_url_keywords(user, url, keywords)
                check_url_patterns(user, url, patterns)
                already_visited.append(url)
    return learning_resourses


if __name__ == '__main__':
    log = SquidLog(sys.argv[1], print_human_times = True, print_minimal=True)
    frequency_dict, data_log = get_links(log)
    total_log = analyze_links(data_log)
    total_frequency_log = frequency_analysis(frequency_dict)
    print 'Итоговый лог' + str(total_log)
    print 'Частотный анализ:' + str(total_frequency_log)