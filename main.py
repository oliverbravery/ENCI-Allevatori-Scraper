from multiprocessing import Pool, Manager
import os
import numpy as np
from models import *
from database import Database
from scraper import *

def database_integration(areas: list[Area], breeders: list[Breeder], 
                         members: list[Member], breeds: list[Breed], 
                         manager: Manager) -> None:
    """
    Migrates the data collected from scraping into a database. Wraps the add_to_database function to track progress.

    Args:
        areas (list[Area]): The areas of Italy scraped from the ENCI website.
        breeders (list[Breeder]): The breeders scraped from the ENCI website.
        members (list[Member]): The members scraped from the ENCI website.
        breeds (list[Breed]): The breeds scraped from the ENCI website.
        manager (Manager): The multiprocessing manager used to share the counter accross processes.
    """
    # instantiates a database object
    db: Database = Database()
    # calculates the total amount of database entries to be added to the database
    total_database_entries: int = len(areas)+len(breeders)+len(members)+len(breeds)+len(breeders)+len(
        [breed for breeder in breeders for breed in breeder.breeds]
        )+len([member for member in members for breeder_id in member.breeder_ids])
    # instantiates a Progress object to track progress
    progress: Progress = Progress(start_time=time.time(), 
                                  total_amount=total_database_entries, 
                                  manager=manager)
    # adds all data to the database
    add_to_database(db, areas, breeders, members, breeds, progress)
    
def add_to_database(db: Database, areas: list[Area], breeders: list[Breeder], members: list[Member], breeds: list[Breed], progress: Progress):
    """
    Adds all data to the database.

    Args:
        db (Database): The database object.
        areas (list[Area]): List of areas to add to the database.
        breeders (list[Breeder]): List of breeders to add to the database.
        members (list[Member]): List of members to add to the database.
        breeds (list[Breed]): List of breeds to add to the database.
        progress (Progress): The progress tracker object.
    """
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
    """
    Retrieves all breeders from the ENCI website using multiprocessing. 
    Wraps the scrape_area function to allow for tracking progress accross processes.

    Args:
        areas (list[Area]): The areas of Italy scraped from the ENCI website.
        manager (Manager): The multiprocessing manager used to share the counter accross processes.

    Returns:
        list[Breeder]: A list of Breeder objects scraped from the ENCI website.
    """
    # instantiates a Pool object to allow for multiprocessing using all available cores
    pool: Pool = Pool(os.cpu_count())
    # instantiates a Progress object to track progress
    progress: Progress = Progress(start_time=time.time(), 
                                  total_amount=len(areas), 
                                  manager=manager)
    # use starmap to scrape each area in the list of areas using multiprocessing
    breeders: list[Breeder] = pool.starmap(scrape_area, [(area,progress,) for area in areas])
    # flatten the list of lists of breeders into a single list of breeders
    breeders: list[Breeder] = [breeder for breeder_list in breeders for breeder in breeder_list]
    return breeders
    
def pooled_breed_members_retrieval(breeders: list[Breeder], manager: Manager) -> list[BreedMembers]:
    """
    Retrieves all breeders' members and breeds from the ENCI website using multiprocessing. 
    Wraps the request_breeder_details function to allow for tracking progress accross processes.

    Args:
        breeders (list[Breeder]): The breeders scraped from the ENCI website.
        manager (Manager): The multiprocessing manager used to share the counter accross processes.

    Returns:
        list[BreedMembers]: A list of BreedMembers objects scraped from the ENCI website.
    """
    # calculate the total amount of breeders to be scraped
    total_breeder_count = len(breeders)
    paused_process_count = Counter(manager,0)
    pool: Pool = Pool(os.cpu_count())
    # instantiates a Progress object to track progress
    progress: Progress = Progress(start_time=time.time(), total_amount=total_breeder_count, manager=manager)
    # use starmap to scrape each breeder in the list of breeders using multiprocessing
    pooled_breed_members: list[BreedMembers] = pool.starmap(request_breeder_details, 
                                                            [(breeder, 
                                                              paused_process_count,np.random.uniform(0.03,0.43), progress) 
                                                             for breeder in breeders])
    return pooled_breed_members
    
def sort_breed_members(breed_members: list[BreedMembers]) -> (list[Member], list[Breed]):
    """
    Sorts the breed_members of type BreedMembers into seperate lists of members and breeds.

    Args:
        breed_members (list[BreedMembers]): The breed_members to sort.

    Returns:
        tuple: A tuple containing the lists of members and breeds.
    """
    # create a dictionary of members and breeds to remove duplicates
    members: dict[str, Member] = {}
    breeds: list[str, Breed] = {}
    # iterate through each BreedMembers object and add the members and breeds to the dictionary if they are not already in it
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
    # convert the dictionaries to lists
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