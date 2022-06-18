# -*- coding: utf-8 -*-

import time

import requests
from tqdm import tqdm
import vk


# Service token
DEFAULT_TOKEN = '9c6632069c6632069c663206a19c1ed61499c669c663206fd7701b108a6f85c9864837b'

DEFAULT_VK_VER = '5.131'


TOO_MANY_REQESTS_ERROR = 6


class VkAPI:
    
    def __init__(self, token=DEFAULT_TOKEN, ver=DEFAULT_VK_VER):
        self._token = token
        self._session = vk.Session(access_token=self._token)
        self.api = vk.API(self._session)
        self.ver = ver
        
    def execute(self, code):
        url = 'https://api.vk.com/method/execute?'
        data = dict(code=code, access_token=self._token, v=self.ver)
        resp = requests.post(url=url, data=data)
        try:
            res = [item['response'] for item
                   in vk.utils.json_iter_parse(resp.text)]
        except:
            raise ValueError('No "response" field in the result')
        return res

    def _load_wall_record_comments_chunk(self, group_id, rec_id,
                                         comment_id=None):    
        comments = []
        offset = 0
        count = 0
        while True:
            try:
                if comment_id is None:
                    # Primary thread
                    res = self.api.wall.getComments(
                            owner_id=-group_id, post_id=rec_id, 
                            count=100, offset=offset, v=self.ver)
                else:
                    # Secondary thread
                    res = self.api.wall.getComments(
                            owner_id=-group_id, post_id=rec_id,
                            count=100, offset=offset, v=self.ver,
                            comment_id=comment_id)
                nret = len(res['items'])
                count += nret
                if nret:
                    comments += res['items']
                    offset += nret
                if count >= res['current_level_count']:
                    #print(f'COUNT: {count} of {res["current_level_count"]}')
                    break
            #except vk.exceptions.VkAPIError as e:
            except Exception as e:
                #if e.code != TOO_MANY_REQESTS_ERROR:
                #    print(e)
                time.sleep(0.4)
                #if e.code == TOO_MANY_REQESTS_ERROR:
                #    time.sleep(0.4)
                #else:
                #    raise e
                    
        return comments
    
    def load_wall_record_comments(self, group_id, rec_id):
        comments = []
        try:
            # First level
            comments = self._load_wall_record_comments_chunk(group_id, rec_id)
            # Second level
            comments2 = []
            for n, comment in enumerate(comments):
                #print(f'Comment: {n} / {len(comments)}')
                comments2 += self._load_wall_record_comments_chunk(
                        group_id, rec_id, comment_id=comment['id'])
            comments += comments2
        except vk.exceptions.VkAPIError as e:
            print('VkAPI.load_wall_record_comments() -> VkAPIError')
            print(f'{e.code}  {e.message}')
            pass
        return comments    
    
    def load_group_members(self, group_id, ntoload='all', offset=0,
                           sort_type='id_desc', fields=None):    
        members = []
        count = 0
        if fields is None:
            fields = []
        group_info = self.load_group_info(group_id, fields=['members_count'])
        ntoload_max = group_info['members_count'] - offset - 1
        if ntoload == 'all':
            ntoload = ntoload_max
        else:
            ntoload = min(ntoload, ntoload_max)
        while True:
            try:
                res = self.api.groups.getMembers(
                        group_id=group_id, sort=sort_type,
                        count=1000, offset=offset, v=self.ver,
                        fields=fields)
                nret = len(res['items'])
                count += nret
                print(f'Count: {count} / {ntoload}')
                if nret:
                    members += res['items']
                    offset += nret
                if count >= ntoload:
                    members = members[:ntoload]
                    break
            except Exception as e:
                if isinstance(e, vk.exceptions.VkAPIError):
                    if e.code != TOO_MANY_REQESTS_ERROR:
                        print(f'VkAPI Exception: {e.code}')
                else:
                    print(f'Exception: {e}')
                time.sleep(0.4)                   
        return members    
    
    def load_wall_records(self, group_id, ntoread):
        records = []
        offset = 0
        while ntoread > 0:
            res = self.api.wall.get(owner_id=-group_id, offset=offset,
                                  count=min(ntoread,100), v=self.ver)
            nret = len(res['items'])
            if nret==0:
                break
            ntoread -= nret
            offset += nret
            records += res['items']
        return records
    
    def load_group_info(self, group_id, fields=None):
        if fields is None:
            fields = []
        while True:
            try:
                groups_info = self.api.groups.getById(
                        group_ids=[group_id], fields=fields, v=self.ver)
                break
            except vk.exceptions.VkAPIError:
                time.sleep(0.5)
        return groups_info[0]
    
    def load_groups_info(self, group_idx):
        pos = 0
        groups_info = []
        while pos < len(group_idx):
            groups_info_cur = self.api.groups.getById(
                    group_ids=group_idx[pos:], v=self.ver)
            pos += len(groups_info_cur)
            groups_info += groups_info_cur
        return groups_info
            
    def load_users_info(self, users_idx, fields=None, output=None):
        if output is None:
            users_info = {}
        else:
            users_info = output
        pos = 0
        if fields is None:
            fields = []
        # Request info in portions of 1000 users or less
        while pos < len(users_idx):
            try:
                ntoread = min(len(users_idx) - pos, 1000)
                users_idx_slice = users_idx[pos : ntoread + pos]
                #print('Load user info')
                #time.sleep(1)
                users_info_new_ = self.api.users.get(
                        user_ids=users_idx_slice, fields=fields, v=self.ver)
                #pos += len(users_info_new_)
                pos += ntoread  # get() could return less users due to 
                                # non-existing accounts
                users_info_new = {user_info['id']: user_info
                                  for user_info in users_info_new_}
                users_info.update(users_info_new)
                print(f'Count: {len(users_info)} / {len(users_idx)}')
            except Exception as e:
                if isinstance(e, vk.exceptions.VkAPIError):
                    if e.code != TOO_MANY_REQESTS_ERROR:
                        print(f'VkAPI Exception: {e.code}')
                else:
                    print(f'Exception: {e}')
                time.sleep(0.4)        
        return users_info

    def count_user_comments(self, group_id, recs):
        
        usr_comm_count = {}
        
        # Walk through the records
        for n, rec in tqdm(enumerate(recs), total=len(recs), unit='recs'):
        
            # Get comments
            comms = self.load_wall_record_comments(group_id, rec['id'])
            
            # Select and store comments from the users of interest
            for comm in comms:
                if 'from_id' not in comm.keys():
                    continue
                user_id = comm['from_id']
                if user_id in usr_comm_count:
                    usr_comm_count[user_id] += 1
                else:
                    usr_comm_count[user_id] = 0
                    
        # Sort by the number of comments
        usr_comm_count = sorted(usr_comm_count.items(), key=lambda x: x[1])
        usr_comm_count = dict(usr_comm_count)
        
        return usr_comm_count


