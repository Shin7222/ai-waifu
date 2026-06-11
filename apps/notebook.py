import sys

def run():
    print("--- Notebook App ---")
    print("Ketik 'exit' untuk keluar.")
    while True:
        note = input("Tulis catatan Anda: ")
        if note.lower() == 'exit':
            break
        with open("notes.txt", "a") as f:
            f.write(note + "\n")
        print("Tersimpan!")
