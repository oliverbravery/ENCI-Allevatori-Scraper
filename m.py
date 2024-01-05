import requests
from bs4 import BeautifulSoup
import json
import sqlite3
from multiprocessing import Value, Pool, Manager, Lock
import os
import time
import numpy as np
from ctypes import c_int, c_buffer

class Counter(object):
    def __init__(self, manager: Manager, initval=0):
        self.val = manager.Value(c_int, initval)
        self.lock = manager.Lock()
    def increment(self):
        with self.lock:
            self.val.value += 1
    def decrement(self):
        with self.lock:
            self.val.value -= 1
    @property
    def value(self):
        return self.val.value

class Breed:
    code: str
    id: str
    last_litter: str
    description: str
    group_code: str
    group_description: str
    def __init__(self, code:str):
        self.code = code
        self.id = None
        self.last_litter = None
        self.description = None
        self.group_code = None
        self.group_description = None
    def __str__(self):
        return f"{self.code}"
    def __repr__(self):
        return Breed.__str__(self)
    
class Member:
    description: str
    id: str
    signatory: bool
    address: str
    town: str
    def __init__(self, description: str, id: str, signatory: bool, address: str, town: str):
        self.description = description
        self.id = id
        self.signatory = signatory
        self.address = address
        self.town = town
    def __str__(self):
        return f"{self.description}-{self.id}-{self.signatory}-{self.address}-{self.town}"
    def __repr__(self):
        return Member.__str__(self)
    def __hash__(self) -> int:
        return hash(self.id)
    def __eq__(self, __value: object) -> bool:
        return self.id == __value.id
    

class Breeder:
    title: str
    owner: str
    id: str
    breeds: dict[str,Breed] = {}
    members: list[Member]
    def __init__(self, title: str, owner: str, id: str, breeds: dict[str,Breed] = {}, members: list[Member] = []):
        self.title = title
        self.owner = owner
        self.id = id
        self.breeds = breeds
        self.members = members
    def __hash__(self) -> int:
        return hash(self.id)
    def __eq__(self, __value: object) -> bool:
        return self.id == __value.id
    def __str__(self):
        return f"({self.title}){self.owner}-{self.breeds}-{self.id}"
    def __repr__(self):
        return Breeder.__str__(self)
    @staticmethod
    def get_key(obj)->int:
        return int(obj.id)

class Area:
    title: str
    region: str
    breeders: list[Breeder]
    def __init__(self, title, region):
        self.title = title
        self.region = region
    def __str__(self):
        return f"({self.region}){self.title}"
    def __repr__(self):
        return Area.__str__(self)
    def __hash__(self) -> int:
        return hash(self.title, self.region)
    def __eq__(self, o: object) -> bool:
        return self.title == o.title and self.region == o.region
    
class Database:
    connection: sqlite3.Connection
    cursor = sqlite3.Cursor
    def __init__(self):
        self.connection = sqlite3.connect("storage.db")
        self.cursor = self.connection.cursor()
        self.init_db()
    def init_db(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS areas (title TEXT, region TEXT PRIMARY KEY)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS breeders (title TEXT, owner TEXT, id TEXT PRIMARY KEY)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS members (description TEXT, id TEXT PRIMARY KEY, signatory TEXT, address TEXT, town TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS breeds (code TEXT PRIMARY KEY, id TEXT, last_litter TEXT, description TEXT, group_code TEXT, group_description TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS breeders_breeds (breeder_id TEXT, breed_code TEXT, FOREIGN KEY(breeder_id) REFERENCES breeders(id), FOREIGN KEY(breed_code) REFERENCES breeds(code), PRIMARY KEY(breeder_id, breed_code))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS breeders_members (breeder_id TEXT, member_id TEXT, FOREIGN KEY(breeder_id) REFERENCES breeders(id), FOREIGN KEY(member_id) REFERENCES members(id), PRIMARY KEY(breeder_id, member_id))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS areas_breeders (area_region TEXT, breeder_id TEXT, FOREIGN KEY(area_region) REFERENCES areas(region), FOREIGN KEY(breeder_id) REFERENCES breeders(id), PRIMARY KEY(area_region, breeder_id))")
        self.connection.commit()
        
def get_areas() -> list[Area]:
    URL = f"https://www.enci.it/allevatori/allevatori-con-affisso?codRegione=PIE"
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    map = soup.find("map", {"name": "ENCI_italia_Map"})
    area_tags = map.find_all("area")
    areas: list[Area] = []
    for a in area_tags:
        current_area = Area(a["title"], a["data-regione"])
        if current_area not in areas:
            areas.append(current_area)
    return areas

def get_breeder_details(breeder: Breeder) -> Breeder:
    url = f"https://www.enci.it/umbraco/enci/AllevatoriApi/TakeAllevatore?idAffisso={breeder.id}"
    payload = {}
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload, timeout=10)
    breeder_data = json.loads(response.text)
    for current_member in breeder_data["Soci"]:
        member: Member = Member(description=current_member["DesAssociato"],
                                id=current_member["IdAnagrafica"],
                                signatory=True if current_member["FlagFirmatario"]=="S" else False,
                                address=current_member["DesIndirizzoSocio"],
                                town=current_member["DesLocalitaSocio"])
        if member not in breeder.members:
            breeder.members.append(member)
    for current_breed in breeder_data["Razze"]:
        breeder.breeds[current_breed["CodRazza"]].id = current_breed["IdUmb"]
        breeder.breeds[current_breed["CodRazza"]].last_litter = current_breed["UltimaCucciolata"]
        breeder.breeds[current_breed["CodRazza"]].description = current_breed["DesRazza"]
        breeder.breeds[current_breed["CodRazza"]].group_code = current_breed["CodGruppo"]
        breeder.breeds[current_breed["CodRazza"]].group_description = current_breed["DesGruppo"]
    return breeder

def get_breeders(area:Area) -> list[Breeder]:
    url = "https://www.enci.it/umbraco/enci/AllevatoriApi/GetAllevatori"
    payload = "{\"regioniAttive\":[\""+area.region+"\"],\"filtroRazze\":[]}"
    headers = {
    'Content-Type': 'application/json;charset=utf-8'
    }
    response: requests.Response = requests.request("POST", url, headers=headers, data=payload)
    breeder_data = json.loads(response.text)
    breeders: list[Breeder] = []
    for current_breeder in breeder_data:
        breeder: Breeder = Breeder(title=current_breeder["DesAffisso"], 
                                   owner=current_breeder["Proprietario"], 
                                   id=current_breeder["IdAffisso"], 
                                   breeds={breed_code:Breed(code=breed_code) for breed_code in current_breeder["Razze"]})
        if breeder not in breeders:
            breeders.append(breeder)
            print(f"\t-Breeder ({breeder.id}){breeder.title} added.")
    return breeders

def add_to_database(db: Database, area: Area) -> bool:
    db.cursor.execute("INSERT OR IGNORE INTO areas (title, region) VALUES (?, ?)", (area.title, area.region))
    for breeder in area.breeders:
        db.cursor.execute("INSERT OR IGNORE INTO breeders (title, owner, id) VALUES (?, ?, ?)", (breeder.title, breeder.owner, breeder.id))
        for breed_code in breeder.breeds:
            breed: Breed = breeder.breeds[breed_code]
            db.cursor.execute("INSERT OR IGNORE INTO breeds (code, id, last_litter, description, group_code, group_description) VALUES (?, ?, ?, ?, ?, ?)", (breed.code, breed.id, breed.last_litter, breed.description, breed.group_code, breed.group_description))
            db.cursor.execute("INSERT OR IGNORE INTO breeders_breeds (breeder_id, breed_code) VALUES (?, ?)", (breeder.id, breed.code))
        for member in breeder.members:
            db.cursor.execute("INSERT OR IGNORE INTO members (description, id, signatory, address, town) VALUES (?, ?, ?, ?, ?)", (member.description, member.id, member.signatory, member.address, member.town))
            db.cursor.execute("INSERT OR IGNORE INTO breeders_members (breeder_id, member_id) VALUES (?, ?)", (breeder.id, member.id))
        db.cursor.execute("INSERT OR IGNORE INTO areas_breeders (area_region, breeder_id) VALUES (?, ?)", (area.region, breeder.id))
    db.connection.commit()
    return True

def scrape_area(area: Area) -> Area:
    area.breeders: list[Breeder] = get_breeders(area)
    print(f"Area ({area.region}){area.title} scraped.")
    return area

def request_breeder_details(breeder: Breeder, total_breeders: int, completed_breeders: Counter, paused_process_count: Counter,wait_time: float) -> Breeder:
    time.sleep(wait_time)
    completed: bool = False
    while not completed:
        try:
            if paused_process_count.value > 10:
                time.sleep(5.0)
            breeder = get_breeder_details(breeder)
            completed = True
        except Exception as e:
            print(f"({breeder.id})Error: {e} - Retrying in 7.3-11.48 seconds.")
            paused_process_count.increment()
            time.sleep(np.random.uniform(7.3,11.48))
            paused_process_count.decrement()
    completed_breeders.increment()
    percentage = round((float(completed_breeders.value)/float(total_breeders))*100.0, 4)
    print(f"({completed_breeders.value}/{total_breeders}) - {percentage}%")
    return breeder

if __name__ == "__main__":
    db: Database = Database()
    areas: list[Area] = get_areas()
    pool: Pool = Pool(os.cpu_count())
    pooled_areas = pool.starmap(scrape_area, [(area,) for area in areas])
    x: dict = {}
    for area in pooled_areas:
        for breeder in area.breeders:
            x[breeder.id] = breeder
    all_breeders: list[Breeder] = list(x.values())
    all_breeders.sort(key=Breeder.get_key)
    print("All breeders scraped.")
    print(f"Starting to retrieve breeder details for {len(all_breeders)} breeders.")
    total_breeder_count = len(all_breeders)
    manager: Manager = Manager()
    completed_processes = Counter(manager,0)
    paused_process_count = Counter(manager,0)
    pool: Pool = Pool(os.cpu_count())
    pooled_breeders = pool.starmap(request_breeder_details, [(breeder, total_breeder_count, completed_processes, paused_process_count,np.random.uniform(0.03,0.43)) for breeder in all_breeders])
    print("All breeders details retrieved.")
    finalised_breeders: dict = {}
    for breeder in pooled_breeders:
        finalised_breeders[breeder.id] = breeder
    print("Starting to add all breeders details to breeders.")
    for area in pooled_areas:
        for breeder in area.breeders:
            if breeder.id in finalised_breeders:
                breeder = finalised_breeders[breeder.id]
    print("All breeders details added to breeders.")
    print(f"{completed_processes.value} breeders completed / {total_breeder_count} breeders total.")
    print("Starting to add all breeders to database.")
    for area in pooled_areas:
        add_to_database(db, area)
        print(f"Area ({area.region}){area.title} added to database.")
    print("All breeders added to database.")

    