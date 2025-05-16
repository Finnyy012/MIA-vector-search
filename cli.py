print("Launching...")

from vdb import VDB
import os
import utils

database = VDB()

def clear(): os.system('cls' if os.name=='nt' else 'clear')

while True:
    clear()
    print("0: exit\n1: upload from url\n2: query\n3: display stored titles\n")
    command = input(" option: ")
    clear()

    if command=="0":
        break

    elif command=="1":
        url = input("url: ")
        database.upsert_from_url(url)
        print("finished!")

    elif command=="2":
        query = input("Search query: ")
        res = database.search_as_query(query)

        for i, node in enumerate(res['metadatas'][0]):
            print(f"result {i}: from {node["title"]}, {node["url"]}")
            print(utils.unchunk_from_node(node))
            input("\nPress Enter to continue")

    elif command=="3":
        print("Stored titles: ")
        print(database.get_titles())

    else:
        print("invalid input")
    input("\nPress Enter to continue")