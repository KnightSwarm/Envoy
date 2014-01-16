import oursql

from .util import Singleton, LocalSingleton, LocalSingletonBase

@LocalSingleton
class Database(LocalSingletonBase):
	def initialize(self, host, user, passwd, db):
		self.conn = oursql.connect(host=host, user=user, passwd=passwd, db=db, autoreconnect=True)
		self.row_factory = Row
		self.tables = {}
	
	def _get_cursor(self):
		return CursorWrapper(self.conn.cursor(), self.row_factory, self)
		
	def _get_table(self, name, in_memory=False, forced=False):
		if in_memory == True:
			try:
				# Only create a new MemoryTable if one doesn't already exist
				create_new = forced or not isinstance(self.tables[name], MemoryTable)
			except KeyError, e:
				create_new = True
		else:
			try:
				self.tables[name]
				create_new = forced or False
			except KeyError, e:
				create_new = True
		
		if create_new == False:
			return self.tables[name]
		else:
			if in_memory == True:
				new_table = MemoryTable(self, name)
			else:
				new_table = DatabaseTable(self, name)
				
			self.tables[name] = new_table
			return new_table
	
	def __getitem__(self, key):
		return self.get_database_table(key)
		
	def commit(self):
		self.conn.commit()
		
	def get_database_table(self, name):
		return self._get_table(name, in_memory=False)
	
	def get_memory_table(self, name):
		return self._get_table(name, in_memory=True)
	
	def log_query(self, query, params):
		pass
	
	def query(self, query, params = [], commit=False, table=None):
		self.log_query(query, params)
		
		cur = self._get_cursor()
		cur.table = table
		cur.execute(query, params)
		
		if commit == True:
			self.conn.commit()
			
		return cur

class CursorWrapper(object):
	def __init__(self, cursor, row_factory, db):
		self.cursor = cursor
		self.row_factory = row_factory
		self.db = db
		self.table = None
		
	def __getattr__(self, name):
		return getattr(self.cursor, name)
		
	def __iter__(self):
		return self
		
	def _wrap_row(self, row):
		if row is None:
			return None
		else:
			return self.row_factory(self.cursor, row, self.db, self.table)
		
	def next(self):  # Iterable implementation
		row = self.fetchone()
		
		if row is None:
			raise StopIteration
		else:
			return row
		
	def fetchone(self):
		return self._wrap_row(self.cursor.fetchone())
		
	def fetchmany(self, size=None):
		if size is None:
			size = self.cursor.arraysize
			
		return [self._wrap_row(row) for row in self.cursor.fetchmany(size)]
		
	def fetchall(self):
		return [self._wrap_row(row) for row in self.cursor.fetchall()]
	
class Row(object):
	def __init__(self, cursor=None, row=None, db=None, table=None):
		self._commit_buffer = {}
		self._data = {}
		
		if cursor is None and row is None:
			self._new = True
		else:
			self._new = False
			
			for index, column in enumerate(cursor.description):
				self._data[column[0]] = row[index]
				
		self._db = db
		self._table = table
	
	def __getitem__(self, key):
		return self._data[key]
	
	def __setitem__(self, key, value):
		self._commit_buffer[key] = value
	
	def _clear_buffer(self):
		self._commit_buffer = {}
	
	def commit(self):
		# Commit to database
		if len(self._commit_buffer) > 0:
			statement_list = ", ".join("`%s` = ?" % key for key in self._commit_buffer.keys())
			query = "UPDATE %s SET %s WHERE `Id` = '%s'" % (self._table, statement_list, self['Id'])  # Not SQLi-safe!
			self._db.query(query, params=self._commit_buffer.values(), commit=True)
			
			# Update locally
			for key, value in self._commit_buffer.iteritems():
				self._data[key] = value
				
		# Clear out commit buffer
		self._clear_buffer()
		
	def rollback(self):
		self._clear_buffer()
		
	def delete(self):
		self._db.query("DELETE FROM %s WHERE `Id` = ?" % self._table, (self["Id"],))

class Table(object):
	def __init__(self, database, table_name):
		# You should never construct this directly!
		self.db = database
		self.table = table_name
	
	def _process_insert(self, value, key=None):
		if key is not None:
			value['Id'] = key
		
		for column in self.columns:
			if column != "Id" and column not in value._commit_buffer.keys():
				value._commit_buffer[column] = None
		
		column_list = ", ".join("`%s`" % name for name in value._commit_buffer.keys())
		sub_list = ", ".join("?" for name in value._commit_buffer.keys())
		query = "INSERT INTO %s (%s) VALUES (%s)" % (self.table, column_list, sub_list)  # Not SQLi-safe!
		
		result = self.db.query(query, params=value._commit_buffer.values(), commit=True)
		
		value._new = False
		
		return result.lastrowid
	
	def _try_set(self, key, value, cache):
		if key in cache:
			raise TypeError("A row with the given ID already exists. Either edit the existing one, or append a new row using append().")
		else:
			try:
				self._process_insert(value, key)
			except sqlite3.IntegrityError, e:
				raise TypeError("A row with the given ID already exists. Either edit the existing one, or append a new row using append().")
	
	def _set_column_names(self, names):
		self._column_names = names
		
	def _retrieve_column_names(self):
		cur = self.db.query("SELECT * FROM %s WHERE 0" % self.table)  # Not SQLi-safe!
		self._set_column_names([x[0] for x in cur.description])
		
	def __getattr__(self, name):
		if name == "columns":
			try:
				return self._column_names
			except AttributeError, e:
				self._retrieve_column_names()
				return self._column_names
		else:
			raise AttributeError("No such attribute exists")
	
	def append(self, value):
		value._table = self.table
		return self._process_insert(value)
		
class DatabaseTable(Table):
	def __init__(self, database, table_name):
		Table.__init__(self, database, table_name)
		self._cache = {}
	
	def _process_insert(self, value, key=None):
		rowid = Table._process_insert(self, value, key)
		self._cache[rowid] = value
		return rowid
	
	def __getitem__(self, key):
		try:
			return self._cache[key]
		except KeyError, e:
			result = self.db.query("SELECT * FROM %s WHERE `Id` = ?" % self.table, params=(key,))
			self._set_column_names([x[0] for x in result.description])
			
			if result is None:
				raise KeyError("No row with that ID was found in the table.")
			else:
				row = result.fetchone()
				row._db = self.db
				row._table = self.table
				row._type = "database"
				self._cache[key] = row
				return row
				
	def __setitem__(self, key, value):
		self._try_set(key, value, self._cache)
		
	def purge(self):
		self._cache = {}

class MemoryTable(Table):
	def __init__(self, database, table_name):
		Table.__init__(self, database, table_name)
		self.data = {}
		self._retrieve_data()
		
	def _retrieve_data(self):
		result = self.db.query("SELECT * FROM %s" % self.table)  # Not SQLi-safe!
		self._set_column_names([x[0] for x in result.description])
		
		for row in result:
			row._db = self.db
			row._table = self.table
			row._type = "memory"
			self.data[row['Id']] = row
			
	def _process_insert(self, value, key=None):
		rowid = Table._process_insert(self, value, key)
		self.data[rowid] = value
		self.data[rowid]._db = self.db
		self.data[rowid]._table = self.table
		self.data[rowid]._type = "memory"
		return rowid
			
	def __getitem__(self, key):
		return self.data[key]
		
	def __setitem__(self, key, value):
		self._try_set(key, value, self.data)
	
	def refresh(self):
		self.data = {}
		self._retrieve_data()
