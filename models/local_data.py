import os
import json
import uuid
import time
import shutil

class LocalDictModel:
    DATA_DIR = "data"
    def __init__(self, org, dataset=None):
        if dataset is not None:
            self.filename = f"orgs/{org}/{self.DATA_DIR}/{dataset}.json"
            self._read()        
        else:
            shutil.copytree(f"orgs/skeleton", f"orgs/{org}")

    def commit(self):
        with open(self.filename, 'w') as f:
            json.dump(self.db, f)

    def _read(self):
        with open(self.filename, 'r') as f:
            self.db = json.load(f)
            self.time = time.time()

    def refresh(self):
        if os.path.getmtime(self.filename) > self.time:
            self._read()

    def _new_key(self):
        return uuid.uuid1().hex.upper()

    def _exists(self, key):
        return (key in self.db)

    def get(self, key):
        try:
            return self.db[key]
        except:
            raise KeyError(f"Key {key} does not exist")

    def items(self):
        return self.db.values()

    def get_field(self, key, field):
        try:
            item = self.db[key]
            try:
                return item[field]
            except:
                raise ValueError(f"Field {field} does not exist for key {key}")
        except:
            raise KeyError(f"Key {key} does not exist")

    def create(self, item):
        key = self._new_key()
        item['key'] = key
        self.db[key] = item
        self.commit()
        return self.db[key]

    def insert(self, key, item):
        self.db[key] = item
        self.commit()
        return self.db[key]

    def update(self, key, data):
        for field in data:
            self.db[key][field] = data[field]
        self.commit()
        return self.db[key]

    def delete(self, key):
        self.db.pop(key, None)
        self.commit()

    def query(self, filters, sort_keys=None, descending=False, start=None, limit=None):
        filtered = [
            item_value 
                for (item_key, item_value) in self.db.items() 
                if filters is None or \
                   all([item_value[query_key] == query_value 
                        for (query_key, query_value) in filters.items()])
        ]

        result = filtered if sort_keys is None \
                 else sorted(filtered, 
                             key = lambda item: [item[skey] for skey in sort_keys], 
                             reverse=descending )

        total = len(result)

        if start is None:
            final, begin, end = (result, 0, total - 1) \
                if limit is None \
                else (result[:limit], 0, limit - 1 if limit <= total else total - 1)
        else:
            final, begin, end = (result[start:], start, total - 1) \
                if limit is None \
                else (result[start: start+limit], start, start + limit - 1 \
                      if start + limit <= total else total-1)
                
        if len(final) == 0:
            begin = None
            end = None

        return (final, begin, end, total)
