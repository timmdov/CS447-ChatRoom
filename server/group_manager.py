# server/group_manager.py
class GroupManager:
    def __init__(self):
        self.groups = {}  

    def create_group(self, group_name, owner_client, owner_nickname):
        if group_name not in self.groups:
            self.groups[group_name] = {
                'members': {owner_client},
                'nicknames': {owner_nickname},
                'owner': owner_client
            }
            return True
        return False

    def join_group(self, group_name, client, nickname):
        if group_name in self.groups:
            self.groups[group_name]['members'].add(client)
            self.groups[group_name]['nicknames'].add(nickname)
            return True
        return False

    def leave_group(self, group_name, client, nickname):
        if group_name in self.groups and client in self.groups[group_name]['members']:
            self.groups[group_name]['members'].remove(client)
            self.groups[group_name]['nicknames'].remove(nickname)
            if len(self.groups[group_name]['members']) == 0:
                del self.groups[group_name]
            return True
        return False

    def get_group_members(self, group_name):
        return self.groups.get(group_name, {}).get('members', set())

    def get_group_nicknames(self, group_name):
        return self.groups.get(group_name, {}).get('nicknames', set())

    def get_user_groups(self, client):
        return [group for group, data in self.groups.items() if client in data['members']]