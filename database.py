import sqlite3
from Progress import *

class Database:
    """
    A class that represents a connection to a sqlite3 database.
    """
    connection: sqlite3.Connection
    cursor = sqlite3.Cursor
    
    def __init__(self):
        """
        Initializes the database connection and cursor.
        """
        self.connection = sqlite3.connect("storage.db")
        self.cursor = self.connection.cursor()
        self.init_db()
        
    def init_db(self):
        """ 
        Initializes the database tables.
        """
        self.cursor.execute("CREATE TABLE IF NOT EXISTS areas (title TEXT, region TEXT PRIMARY KEY)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS breeders (title TEXT, owner TEXT, id TEXT PRIMARY KEY)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS members (description TEXT, id TEXT PRIMARY KEY, signatory TEXT, address TEXT, town TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS breeds (code TEXT PRIMARY KEY, id TEXT, last_litter TEXT, description TEXT, group_code TEXT, group_description TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS breeders_breeds (breeder_id TEXT, breed_code TEXT, FOREIGN KEY(breeder_id) REFERENCES breeders(id), FOREIGN KEY(breed_code) REFERENCES breeds(code), PRIMARY KEY(breeder_id, breed_code))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS breeders_members (breeder_id TEXT, member_id TEXT, FOREIGN KEY(breeder_id) REFERENCES breeders(id), FOREIGN KEY(member_id) REFERENCES members(id), PRIMARY KEY(breeder_id, member_id))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS areas_breeders (area_region TEXT, breeder_id TEXT, FOREIGN KEY(area_region) REFERENCES areas(region), FOREIGN KEY(breeder_id) REFERENCES breeders(id), PRIMARY KEY(area_region, breeder_id))")
        self.connection.commit()
        
    def query_no_response(self, query: str, params:tuple, progress: Progress = None) -> None:
        """
        Executes a query without returning a response.
        Args:
            query (str): The query to execute.
            params (tuple): The parameters to pass to the query.
            progress (Progress, optional): Progress object for tracking progress. Defaults to None.
        """
        self.cursor.execute(query, params)
        if progress:
            progress.increment_amount_completed()
            progress.display_progress()
    
    def commit_to_database(self):
        """
        Commits the changes to the database.
        """
        self.connection.commit()