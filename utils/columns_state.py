class ColumnsState:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.df_columns = None
            cls._instance.pagamenti_columns = None
        return cls._instance
    
    def set_df_columns(self, columns):
        self.df_columns = columns
        
    def set_pagamenti_columns(self, columns):
        self.pagamenti_columns = columns
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
