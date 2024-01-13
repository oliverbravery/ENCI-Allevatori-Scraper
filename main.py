from multiprocessing import Pool, Manager
import os
import numpy as np
from models import *
from database import Database
from scraper import *

def database_integration(areas: list[Area], breeders: list[Breeder], 
                         members: list[Member], breeds: list[Breed], 
                         manager: Manager) -> None:
    # instantiates a database object
    db: Database = Database()
    total_database_entries: int = len(areas)+len(breeders)+len(members)+len(breeds)+len(breeders)+len(
        [breed for breeder in breeders for breed in breeder.breeds]
        )+len([member for member in members for breeder_id in member.breeder_ids])
    progress: Progress = Progress(start_time=time.time(), 
                                  total_amount=total_database_entries, 
                                  manager=manager)
    add_to_database(db, areas, breeders, members, breeds, progress)
    
def add_to_database(db: Database, areas: list[Area], breeders: list[Breeder], members: list[Member], breeds: list[Breed], progress: Progress) -> bool:
    for area in areas:
        db.query_no_response(query="INSERT OR IGNORE INTO areas VALUES (?,?)", 
                             params=(area.title, area.region), progress=progress)
    for breeder in breeders:
        db.query_no_response(query="INSERT OR IGNORE INTO breeders VALUES (?,?,?)", 
                             params=(breeder.title, breeder.owner, breeder.id), progress=progress)
    for breed in breeds:
        db.query_no_response(query="INSERT OR IGNORE INTO breeds VALUES (?,?,?,?,?,?)", 
                             params=(breed.code, breed.id, breed.last_litter, breed.description, 
                                     breed.group_code, breed.group_description), 
                             progress=progress)
    for member in members:
        db.query_no_response(query="INSERT OR IGNORE INTO members VALUES (?,?,?,?,?)", 
                             params=(member.description, member.id, member.signatory, member.address, member.town), 
                             progress=progress)
    for breeder in breeders:
        db.query_no_response(query="INSERT OR IGNORE INTO areas_breeders VALUES (?,?)", 
                             params=(breeder.area_region, breeder.id), progress=progress)
        for breed_code in breeder.breeds:
            db.query_no_response(query="INSERT OR IGNORE INTO breeders_breeds VALUES (?,?)", 
                                 params=(breeder.id, breed_code), progress=progress)
    for member in members:
        for breeder_id in member.breeder_ids:
            db.query_no_response(query="INSERT OR IGNORE INTO breeders_members VALUES (?,?)", 
                                 params=(breeder_id, member.id), progress=progress)
    db.commit_to_database()

def pooled_breeder_retrieval(areas: list[Area], manager: Manager) -> list[Breeder]:
    pool: Pool = Pool(os.cpu_count())
    progress: Progress = Progress(start_time=time.time(), 
                                  total_amount=len(areas), 
                                  manager=manager)
    breeders: list[Breeder] = pool.starmap(scrape_area, [(area,progress,) for area in areas])
    breeders: list[Breeder] = [breeder for breeder_list in breeders for breeder in breeder_list]
    return breeders
    
def pooled_breed_members_retrieval(breeders: list[Breeder], manager: Manager) -> list[BreedMembers]:
    total_breeder_count = len(breeders)
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
    # instantiate a Manager object to create a semaphores for progress tracking across processes
    manager: Manager = Manager()
    # Centered title with 50-character width
    print("_" * 50)
    print("\n" + f"{'Allevatori Scraper v1.0.0':^50}")
    print("_" * 50)
    # get all areas
    areas: list[Area] = get_areas()
    # get all breeders using multiprocessing
    print("\nStarting to retrieve all breeders.")
    breeders: list[Breeder] = pooled_breeder_retrieval(areas, manager)
    print("\nAll breeders scraped.")
    print(f"\nStarting to retrieve breeder details for {len(breeders)} breeders.")
    # get all breeders' members and breeds using multiprocessing
    breed_members: list[BreedMembers] = pooled_breed_members_retrieval(breeders, manager)
    members: list[Member] = None
    breeds: list[Breed] = None
    # sort breed_members of type BreedMembers into lists of members and breeds
    members, breeds = sort_breed_members(breed_members)
    print("\nAll breeders details retrieved.")
    print("\nStarting to add all breeders to database.")
    # add all data to a relational database
    database_integration(areas, breeders, members, breeds, manager)
    print("\nAll information added to the database.")
    print("\nProgram complete. Exiting.")

    