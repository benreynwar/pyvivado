import sqlite3

class SQLLiteCollection(object):

    COMPULSORY_FIELDS = set(['parent_directory'])
    OPTIONAL_FIELDS = set(['directory', 'description', 'state'])

    def __init__(self, fn):
        self.conn = sqlite3.connect(fn)
        self.cur = self.conn.cursor()
        sql = '''
CREATE TABLE IF NOT EXISTS tasks
(
id INTEGER PRIMARY KEY,
parent_directory TEXT,
directory TEXT,
description TEXT,
state TEXT
);'''
        self.cur.execute(sql)

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

    def insert(self, record):
        for key in record.keys():
            if key not in (self.COMPULSORY_FIELDS | self.OPTIONAL_FIELDS):
                raise ValueError('Unknown attribute: {}'.format(key))
        for opfield in self.OPTIONAL_FIELDS:
            if opfield not in record:
                record[opfield] = ''
        self.cur.execute(
            'INSERT INTO tasks VALUES (?, ?, ?, ?, ?)',
            [None, record['parent_directory'], record['directory'],
             record['description'], record['state']],
        )
        self.conn.commit()
        new_id = self.cur.lastrowid
        record['id'] = new_id
        return new_id

    def update(self, record):
        labels = []
        values = []
        for key in record.keys():
            if key not in (self.COMPULSORY_FIELDS | self.OPTIONAL_FIELDS):
                if key != '_id':
                    raise ValueError('Unknown attribute: {}'.format(key))
            else:
                labels.append(key)
                values.append(record[key])
        sql = 'INSERT INTO tasks({}) VALUES ({}) where id=?'.format(
            [', '.join(labels), ', '.join(['?']*len(labels))])
        self.cur.execute(sql, values + [record['id']])
        self.conn.commit()
    
    def find_by_id(self, _id):
        self.cur.execute(
            'SELECT * FROM tasks WHERE id = ?', (_id,))
        values = self.cur.fetchone()
        record = {
            'id': values[0],
            'parent_directory': values[1],
            'directory': values[2],
            'description': values[3],
            'state': values[4],
        }
        return record

    def count(self):
        self.cur.execute('SELECT count(*) FROM tasks')
        values = self.cur.fetchone()
        count = values[0]
        return count
        
    def drop(self):
        self.cur.execute('DELETE FROM tasks')
        self.conn.commit()
        
    
