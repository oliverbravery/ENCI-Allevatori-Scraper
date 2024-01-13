from multiprocessing import Pool, Manager
import os
import numpy as np
from models import *
from database import Database
from scraper import *

def add_to_database(db: Database, areas: list[Area], breeders: list[Breeder], members: list[Member], breeds: list[Breed]) -> bool:
    for area in areas:
        db.cursor.execute("INSERT OR IGNORE INTO areas VALUES (?,?)", (area.title, area.region))
    for breeder in breeders:
        db.cursor.execute("INSERT OR IGNORE INTO breeders VALUES (?,?,?)", (breeder.title, breeder.owner, breeder.id))
    for breed in breeds:
        db.cursor.execute("INSERT OR IGNORE INTO breeds VALUES (?,?,?,?,?,?)", (breed.code, breed.id, breed.last_litter, breed.description, breed.group_code, breed.group_description))
    for member in members:
        db.cursor.execute("INSERT OR IGNORE INTO members VALUES (?,?,?,?,?)", (member.description, member.id, member.signatory, member.address, member.town))
    for breeder in breeders:
        db.cursor.execute("INSERT OR IGNORE INTO areas_breeders VALUES (?,?)", (breeder.area_region, breeder.id))
        for breed_code in breeder.breeds:
            db.cursor.execute("INSERT OR IGNORE INTO breeders_breeds VALUES (?,?)", (breeder.id, breed_code))
    for member in members:
        for breeder_id in member.breeder_ids:
            db.cursor.execute("INSERT OR IGNORE INTO breeders_members VALUES (?,?)", (breeder_id, member.id))
    db.connection.commit()
    return True

def pooled_breeder_retrieval(areas: list[Area]) -> list[Breeder]:
    pool: Pool = Pool(os.cpu_count())
    breeders: list[Breeder] = pool.starmap(scrape_area, [(area,) for area in areas])
    breeders: list[Breeder] = [breeder for breeder_list in breeders for breeder in breeder_list]
    return breeders
    
def pooled_breed_members_retrieval(breeders: list[Breeder]) -> list[BreedMembers]:
    total_breeder_count = len(breeders)
    # create a manager to instantiate semaphore objects for progress tracking across processes
    manager: Manager = Manager()
    completed_processes = Counter(manager,0)
    paused_process_count = Counter(manager,0)
    pool: Pool = Pool(os.cpu_count())
    progress: Progress = Progress(start_time=time.time(), total_amount=total_breeder_count, manager=manager)
    # use starmap to pass multiple arguments to the function
    pooled_breed_members: list[BreedMembers] = pool.starmap(request_breeder_details, 
                                                            [(breeder, 
                                                              paused_process_count,np.random.uniform(0.03,0.43), progress) 
                                                             for breeder in breeders])
    return pooled_breed_members
    
def sort_breed_members(breed_members: list[BreedMembers]) -> (list[Member], list[Breed]):
    members: dict[str, Member] = {}
    breeds: list[str, Breed] = {}
    for breed_members in breed_members:
        for member in breed_members.members:
            if member.id not in members:
                members[member.id] = member
            else:
                for breeder_id in member.breeder_ids:
                    if breeder_id not in members[member.id].breeder_ids:
                        members[member.id].breeder_ids.append(breeder_id)
        for breed in breed_members.breeds:
            if breed.code not in breeds:
                breeds[breed.code] = breed
    members: list[Member] = list(members.values())
    breeds: list[Breed] = list(breeds.values())
    return (members, breeds)

if __name__ == "__main__":
    # create a database object
    db: Database = Database()
    # get all areas
    areas: list[Area] = get_areas()
    # get all breeders using multiprocessing
    breeders: list[Breeder] = pooled_breeder_retrieval(areas)
    print("All breeders scraped.")
    print(f"Starting to retrieve breeder details for {len(breeders)} breeders.")
    # get all breeders' members and breeds using multiprocessing
    breed_members: list[BreedMembers] = pooled_breed_members_retrieval(breeders)
    members: list[Member] = None
    breeds: list[Breed] = None
    # sort breed_members of type BreedMembers into lists of members and breeds
    members, breeds = sort_breed_members(breed_members)
    print("All breeders details retrieved.")
    print("Starting to add all breeders to database.")
    # add all data to a relational database
    add_to_database(db, areas, breeders, members, breeds)
    print("All breeders added to database.")

    