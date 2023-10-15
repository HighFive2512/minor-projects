import os
import zipfile
import io
import shutil
import tempfile

#replaces cyrilic characters only with upper case letters
def convertcyrillictouppercase(text):
    char_mapping = {'а': 'А','б': 'Б','в': 'В','г': 'Г','д': 'Д','е': 'Е','ж': 'Ж','з': 'З','и': 'И','й': 'Й','к': 'К','л': 'Л','м': 'М','н': 'Н','о': 'О','п': 'П','р': 'Р','с': 'С','т': 'Т','у': 'У','ф': 'Ф','х': 'Х','ц': 'Ц','ч': 'Ч','ш': 'Ш','щ': 'Щ','ъ': 'Ъ','ь': 'Ь','ю': 'Ю','я': 'Я'}

    aflag = False
    adict = []
    #to select only the parts outside the xml tags
    for char in text:
        if char == '<':
            aflag = True
        elif char == '>':
            aflag = False
    
        #would skip if flag is true but set the letters to upper if false - thats put in place to exclude the characters in the xml tags
        if aflag:
            adict.append(char)
        else:
            adict.append(char_mapping.get(char, char.upper()))

    return ''.join(adict)

#creates tempdir for the xlsx content - parse the content of the xl/sharedStrings.xml and start to convert the cyrilic letters to upper via the convertcyrillictouppercase function
def tempdirxlsx(fpath):
    try:
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(fpath, 'r') as zip_file:
            zip_file.extractall(temp_dir)

        shared_strings_path = os.path.join(temp_dir, 'xl/sharedStrings.xml')
        with open(shared_strings_path, 'r', encoding='utf-8') as sharedString_filename:
            sharedString_content = sharedString_filename.read()
        astringg = convertcyrillictouppercase(sharedString_content)
        with open(shared_strings_path, 'w', encoding='utf-8') as sharedString_filename:
            sharedString_filename.write(astringg)

        with zipfile.ZipFile(fpath, 'w') as zip_file:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    fpath = os.path.join(root, file)
                    arcname = os.path.relpath(fpath, temp_dir)
                    zip_file.write(fpath, arcname)

        shutil.rmtree(temp_dir)

        print(f"file {fpath}")

    except Exception as e:
        print(f"{fpath}: {e}")

def checkxlsxfiles():
    directory = input("write the path to the xlsx files ")

    if not os.path.exists(directory):
        print("incorrect path")
        return

    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.xlsx'):
                fpath = os.path.join(root, file)
                tempdirxlsx(fpath)

if __name__ == "__main__":
    checkxlsxfiles()
