"""Tiny chainable stand-in for the supabase client used in unit tests.

Supports the two query shapes our codebase uses:

  supabase.table(T).select(C).eq(K, V).single().execute().data       -> row
  supabase.table(T).select(C).eq(K, V).execute().data                -> [rows]
  supabase.table(T).update(payload).eq(K, V).execute()               -> records the payload
  supabase.table(T).insert(payload).execute()                        -> records the payload
  supabase.table(T).delete().eq(K, V).execute()                      -> records the delete

The fake stores one row keyed by user_uuid for select; update writes are captured
on the fake so tests can assert what was persisted.
"""


class Fake_Supabase:
  def __init__(self, row=None, rows=None):
    self.row = row              # for .single().execute()
    self.rows = rows or []      # for .execute() (list)
    self.last_update = None     # the payload the code tried to persist
    self.last_insert = None
    self.last_delete = False

  def table(self, _name):
    return _Fake_Table(self)


class _Fake_Table:
  def __init__(self, parent):
    self.parent = parent
    self.mode = "select"        # "select" | "update" | "insert" | "delete"
    self.update_payload = None
    self.insert_payload = None

  def select(self, _cols):
    self.mode = "select"
    return self

  def update(self, payload):
    self.mode = "update"
    self.update_payload = payload
    return self

  def insert(self, payload):
    self.mode = "insert"
    self.insert_payload = payload
    return self

  def delete(self):
    self.mode = "delete"
    return self

  def eq(self, _col, _val):
    return self

  def neq(self, _col, _val):
    return self

  def single(self):
    return self

  def execute(self):
    if self.mode == "update":
      self.parent.last_update = self.update_payload
      return _Fake_Result(data=None)
    if self.mode == "insert":
      self.parent.last_insert = self.insert_payload
      return _Fake_Result(data=[self.insert_payload])
    if self.mode == "delete":
      self.parent.last_delete = True
      return _Fake_Result(data=None)
    # select: prefer .row (single) when present, else fall back to list
    if self.parent.row is not None:
      return _Fake_Result(data=self.parent.row)
    return _Fake_Result(data=self.parent.rows)


class _Fake_Result:
  def __init__(self, data):
    self.data = data
